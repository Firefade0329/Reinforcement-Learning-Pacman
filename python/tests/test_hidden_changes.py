"""F2 (external review of 3337db7): `git update-index --skip-worktree` (and `--assume-unchanged`) hide an edited tracked file from
`git status --porcelain`, `git diff` and `git diff-index`, so every "clean tree" check built on them accepted modified code.

Defences: (a) every tracked file must carry the plain `H` flag of `git ls-files -v`; (b) the working-tree bytes of python/ and the frozen documents
must equal the committed git blobs.  Checked at all use points: provenance.freeze_state, provenance.code_version, the formal analysis
(prereg_analysis.check_protocol_evidence) and the window-diagnostics summary (freeze_context).  Throwaway repositories, synthetic data."""
import subprocess
import sys
from pathlib import Path

import pytest

from pacman_rl import gitcheck
from pacman_rl import prereg as PR
from pacman_rl import provenance as P

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
import window_diagnostics_summary as S  # noqa: E402
from prereg_fixture import Study  # noqa: E402
from test_formal_identity import D  # noqa: E402
from test_freeze_identity import Repo  # noqa: E402
from test_window_diag_summary import FrozenRepo  # noqa: E402

FLAGS = ["--skip-worktree", "--assume-unchanged"]
TARGET = "python/pacman_rl/other.py"  # an ordinary code file: not in any manifest, so only the git-level defences can notice an edit


def status(root):
    return subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def hide_and_edit(root, flag, rel=TARGET, text="VALUE = 999  # edited after the freeze\n"):
    """The attack of the review.  Returns after asserting that the three commands the old checks used really report a clean tree."""
    before = status(root)
    subprocess.run(["git", "update-index", flag, rel], cwd=root, check=True)
    (root / rel).write_text(text, newline="\n")
    assert status(root) == before, "the attack must be invisible to `git status` (otherwise this is not the reviewed situation)"
    assert rel not in subprocess.run(["git", "diff-index", "--name-only", "HEAD"], cwd=root, capture_output=True, text=True).stdout.split()


def add_other(repo_root):
    (repo_root / TARGET).write_text("VALUE = 1\n", newline="\n")


@pytest.fixture()
def frozen_repo(tmp_path, monkeypatch):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    add_other(r.root)
    r.git("add", "-A")
    r.git("commit", "-qm", "code incl. ordinary file")
    r.C = r.git("rev-parse", "HEAD")
    r.freeze()
    return r


def problems_of(repo, **kw):
    return P.freeze_state(repo.root, repo.C, **kw)["problems"]


# ------------------------------------------------------------------ the helper itself
def test_helper_reports_flags_and_content_separately_and_is_silent_on_a_clean_tree(frozen_repo):
    root = frozen_repo.root
    assert gitcheck.hidden_change_problems(root) == [] and gitcheck.index_flag_problems(root) == []
    subprocess.run(["git", "update-index", "--skip-worktree", TARGET], cwd=root, check=True)
    only_flag = gitcheck.hidden_change_problems(root)  # flagged but not modified: the flag alone is refused
    assert len(only_flag) == 1 and "skip-worktree" in only_flag[0] and TARGET in only_flag[0]
    (root / TARGET).write_text("VALUE = 2\n", newline="\n")
    both = gitcheck.hidden_change_problems(root)
    assert len(both) == 2 and "skip-worktree" in both[0] and "differ between the working tree and the committed git blob" in both[1] and TARGET in both[1]
    assert gitcheck.worktree_mismatches(root, ("python",)) == [TARGET]
    assert gitcheck.worktree_mismatches(root, ("python",), skip=(TARGET,)) == []  # skip: allowed to differ


def test_tree_hash_from_blobs_equals_the_worktree_hash_of_a_clean_tree_and_differs_after_an_edit(frozen_repo):
    root = frozen_repo.root
    cv = P.code_version(root)
    assert cv["python_tree_sha256_git"] == cv["python_tree_sha256"] and gitcheck.tree_sha256(gitcheck.committed_blobs(root, ("python",))) == cv["python_tree_sha256_git"]
    hide_and_edit(root, "--skip-worktree")
    cv2 = P.code_version(root)
    assert cv2["python_tree_sha256"] != cv2["python_tree_sha256_git"] == cv["python_tree_sha256_git"]


# ------------------------------------------------------------------ use point 1: provenance.freeze_state
def test_freeze_state_of_the_clean_repository_has_no_problem(frozen_repo):
    assert problems_of(frozen_repo) == []


@pytest.mark.parametrize("flag", FLAGS)
def test_freeze_state_refuses_a_hidden_edit_of_a_code_file(frozen_repo, flag):
    hide_and_edit(frozen_repo.root, flag)
    ps = problems_of(frozen_repo)
    assert any("index flag" in p for p in ps) and any("differ between the working tree and the committed git blob" in p and TARGET in p for p in ps), ps


@pytest.mark.parametrize("flag", FLAGS)
def test_freeze_state_refuses_a_hidden_edit_of_a_frozen_document(frozen_repo, flag):
    """docs/prereg is covered as well: the dependency snapshot is part of C (it is not one of the six freeze materials)."""
    hide_and_edit(frozen_repo.root, flag, rel="docs/prereg/dependency_lock.txt", text="numpy==9.9.9\n")
    ps = problems_of(frozen_repo)
    assert any("docs/prereg/dependency_lock.txt" in p and "differ" in p for p in ps), ps


@pytest.mark.parametrize("flag", FLAGS)
def test_freeze_state_refuses_the_flag_alone_even_without_an_edit(frozen_repo, flag):
    subprocess.run(["git", "update-index", flag, TARGET], cwd=frozen_repo.root, check=True)
    ps = problems_of(frozen_repo)
    assert any("index flag" in p for p in ps) and not any("differ between" in p for p in ps), ps


def test_allow_dirty_freeze_files_still_refuses_hidden_edits_but_not_ordinary_freeze_file_edits(frozen_repo):
    root = frozen_repo.root
    (root / "docs/prereg/FREEZE_CHECKLIST.md").write_text("being prepared\n", newline="\n")  # the permitted preparation state
    assert problems_of(frozen_repo, allow_dirty_freeze_files=True) == []
    hide_and_edit(root, "--skip-worktree")
    assert any(TARGET in p for p in problems_of(frozen_repo, allow_dirty_freeze_files=True))


# ------------------------------------------------------------------ use point 2: provenance.code_version
@pytest.mark.parametrize("flag", FLAGS)
def test_code_version_reports_dirty_for_a_hidden_edit(frozen_repo, flag):
    root = frozen_repo.root
    clean = P.code_version(root)
    assert clean["git_dirty"] is False and clean["hidden_changes"] == []
    hide_and_edit(root, flag)
    cv = P.code_version(root)
    assert cv["git_dirty"] is True and cv["hidden_changes"] and cv["git_sha"] == clean["git_sha"]
    assert cv["python_tree_sha256"] != clean["python_tree_sha256"] and cv["python_tree_sha256_git"] == clean["python_tree_sha256_git"]


def test_code_version_checks_named_extra_files_too(frozen_repo):
    root = frozen_repo.root
    extra = {"docs/prereg/dependency_lock.txt": ""}
    assert P.code_version(root, extra)["git_dirty"] is False
    hide_and_edit(root, "--assume-unchanged", rel="docs/prereg/dependency_lock.txt", text="numpy==9.9.9\n")
    assert P.code_version(root, extra)["git_dirty"] is True


# ------------------------------------------------------------------ use point 3: the formal analysis
def formal(tmp_path):
    return Study(tmp_path / "p", d=D, formal=True)


def refuse(tmp_path, st):
    out = tmp_path / "out_fail"
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, out, "formal")
    assert e.value.obj["code"] == "E_MANIFEST", e.value.obj
    assert not out.exists()
    return e.value.obj


@pytest.mark.parametrize("flag", FLAGS)
def test_formal_analysis_refuses_a_hidden_edit_of_a_code_file(tmp_path, flag):
    st = formal(tmp_path)
    hide_and_edit(st.root, flag)
    obj = refuse(tmp_path, st)
    assert "not what git says" in obj["message"] and any(TARGET in x for x in obj["actual"]), obj


def test_formal_analysis_refuses_the_flag_alone_and_accepts_the_clean_study(tmp_path):
    st = formal(tmp_path)
    subprocess.run(["git", "update-index", "--assume-unchanged", TARGET], cwd=st.root, check=True)
    obj = refuse(tmp_path, st)
    assert "index flag" in obj["message"]
    subprocess.run(["git", "update-index", "--no-assume-unchanged", TARGET], cwd=st.root, check=True)
    A.analyze(st.manifest, st.runs, tmp_path / "out_ok", "formal")


def test_the_analysis_script_helper_agrees_with_the_package_helper(frozen_repo):
    root = frozen_repo.root
    assert A._hidden_git_problems(root) == [] == S._hidden_git_problems(root)
    hide_and_edit(root, "--skip-worktree")
    a, b, c = A._hidden_git_problems(root), S._hidden_git_problems(root), gitcheck.hidden_change_problems(root)
    for found in (a, b, c):
        assert len(found) == 2 and "skip-worktree" in found[0]
        assert "differ between the working tree and the committed git blob" in found[1] and TARGET in found[1]


# ------------------------------------------------------------------ use point 4: the window-diagnostics summary
@pytest.mark.parametrize("flag", FLAGS)
def test_window_summary_refuses_a_hidden_edit_of_a_code_file(tmp_path, flag):
    repo = FrozenRepo(tmp_path / "fr")
    assert repo.context()["freeze_commit"] == repo.F
    hide_and_edit(repo.root, flag)
    with pytest.raises(S.DiagError, match="not what git says"):
        repo.context()


# ------------------------------------------------------------------ the command-line entry points built on freeze_state
@pytest.mark.parametrize("flag", FLAGS)
def test_formal_run_and_final_eval_preflights_refuse_a_hidden_edit(frozen_repo, flag, tmp_path):
    import prereg as runner

    runner.preflight(frozen_repo.cfg, None, allow_unfrozen=False, root=frozen_repo.root)  # the clean repository is accepted
    hide_and_edit(frozen_repo.root, flag)
    with pytest.raises(runner.Refused, match="index flag|differ between the working tree"):
        runner.preflight(frozen_repo.cfg, None, allow_unfrozen=False, root=frozen_repo.root)
    rows = PR.load_matrix()[:1]
    res = tmp_path / "res"
    (res / "runs" / rows[0]["run_name"]).mkdir(parents=True)
    with pytest.raises(runner.Refused, match="index flag|differ between the working tree"):
        runner.final_eval_preflight(frozen_repo.cfg, res, rows, root=frozen_repo.root)
