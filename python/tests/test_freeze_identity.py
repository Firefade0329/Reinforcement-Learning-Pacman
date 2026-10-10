"""Freeze identity with REAL git flows in temporary repositories (simulated data only).

C = the code commit named by the frozen configuration; F = HEAD when the runs are made, a descendant of C that adds only freeze
material.  The old rule 'HEAD == code_commit and clean tree' could never be satisfied by an ordinary commit sequence."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pacman_rl import prereg as PR
from pacman_rl import provenance as P
from pacman_rl import seal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402

CFG_REL = "docs/prereg/frozen_config_v0.3.2.json"


class Repo:
    def __init__(self, root: Path):
        self.root = root
        (root / "python" / "pacman_rl").mkdir(parents=True)
        (root / "python" / "pacman_rl" / "m.py").write_text("x = 1\n")
        (root / "docs" / "prereg").mkdir(parents=True)
        shutil.copy(PR.MATRIX_FILE, root / "docs" / "prereg" / "matrix.csv")
        (root / "docs" / "PLAN.md").write_text("plan\n")
        self.cfg = json.loads(PR.FREEZE_FILE.read_text())
        self.cfg.update(status="frozen", machine_id="m", worker_count=2, hard_enabled=False)
        self.cfg["to_fill_at_freeze"].update({k: "x" for k in runner.TO_FILL}, power_and_sleep_settings_confirmed=True)
        self.write_cfg()
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "code")
        self.C = self.git("rev-parse", "HEAD")

    def git(self, *a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def write_cfg(self):
        (self.root / CFG_REL).write_text(json.dumps(self.cfg, indent=1))

    def freeze(self):
        """Fill code_commit = C, add the fake preregistration texts, commit F."""
        self.cfg["code_commit"] = self.C
        self.write_cfg()
        (self.root / "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md").write_text("SYNTHETIC FAKE preregistration text\n")
        (self.root / "docs/prereg/ANALYSIS_SPEC_v0.3.2.md").write_text("SYNTHETIC FAKE analysis specification text\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "freeze")
        return self.git("rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")  # the temporary repo's (byte-identical) matrix
    return r


def preflight(repo):
    return runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root)


def test_the_old_rule_could_not_be_satisfied_by_any_ordinary_commit_sequence(repo):
    """Documents the defect: filling the field with HEAD dirties the tree; committing moves HEAD past the field."""
    repo.cfg["code_commit"] = repo.C
    repo.write_cfg()
    assert repo.git("status", "--porcelain", "--untracked-files=no") != ""  # dirty
    repo.git("add", "-A")
    repo.git("commit", "-qm", "freeze")
    assert repo.git("rev-parse", "HEAD") != repo.cfg["code_commit"]  # HEAD is no longer the commit the field names


def test_formal_preflight_passes_on_the_real_code_then_freeze_commit_flow(repo):
    F = repo.freeze()
    assert F != repo.C
    assert preflight(repo) == 2
    state = P.freeze_state(repo.root, repo.C)
    assert state["problems"] == [] and state["head"] == F and state["code_commit"] == repo.C


def test_head_equal_to_the_code_commit_is_also_a_valid_state(repo):
    assert P.freeze_state(repo.root, repo.C)["problems"] == []  # F == C: a clean tree at the code commit itself
    repo.cfg["code_commit"] = repo.C
    repo.write_cfg()  # freeze material being prepared
    assert any("uncommitted" in p for p in P.freeze_state(repo.root, repo.C)["problems"])
    assert P.freeze_state(repo.root, repo.C, allow_dirty_freeze_files=True)["problems"] == []


def test_rejects_a_freeze_commit_that_modifies_python(repo):
    (repo.root / "python/pacman_rl/m.py").write_text("x = 2\n")  # sneaked into the freeze commit
    repo.freeze()
    with pytest.raises(runner.Refused, match="python/ tree at HEAD differs"):
        preflight(repo)


def test_rejects_a_dirty_working_tree(repo):
    repo.freeze()
    (repo.root / "python/pacman_rl/m.py").write_text("x = 3\n")
    with pytest.raises(runner.Refused, match="uncommitted changes"):
        preflight(repo)
    (repo.root / "python/pacman_rl/m.py").write_text("x = 1\n")
    (repo.root / CFG_REL).write_text((repo.root / CFG_REL).read_text() + " ")  # even freeze material must be committed for a formal run
    with pytest.raises(runner.Refused, match="uncommitted changes"):
        preflight(repo)


def test_rejects_a_code_commit_that_is_not_an_ancestor_or_does_not_exist(repo):
    repo.git("checkout", "-q", "-b", "other")
    (repo.root / "python/pacman_rl/m.py").write_text("x = 9\n")
    repo.git("commit", "-qam", "diverging code")
    other = repo.git("rev-parse", "HEAD")
    repo.git("checkout", "-q", "-")
    repo.C = repo.C  # main stays at C
    repo.freeze()
    repo.cfg["code_commit"] = other  # a real commit, but not an ancestor of HEAD
    with pytest.raises(runner.Refused, match="not an ancestor of HEAD"):
        runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root)
    repo.cfg["code_commit"] = "0" * 40
    with pytest.raises(runner.Refused, match="does not name a commit"):
        runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root)
    repo.cfg["code_commit"] = None
    with pytest.raises(runner.Refused, match="40-hex"):
        runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root)


def test_rejects_other_files_changed_between_code_and_freeze_commit(repo):
    (repo.root / "docs/PLAN.md").write_text("changed in the freeze commit\n")
    repo.freeze()
    with pytest.raises(runner.Refused, match="not freeze material"):
        preflight(repo)


def test_matrix_change_after_the_code_commit_is_rejected(repo):
    m = repo.root / "docs/prereg/matrix.csv"
    m.write_text(m.read_text().replace("prereg_res4_n1_s100", "prereg_res4_n1_s100 ", 1))
    repo.freeze()
    with pytest.raises(runner.Refused):
        preflight(repo)  # matrix hash differs (and matrix.csv is not freeze material)


def test_draft_configuration_is_refused_even_in_a_valid_git_state(repo):
    repo.cfg["status"] = "draft"
    repo.freeze()
    with pytest.raises(runner.Refused, match="not 'frozen'"):
        preflight(repo)


# ------------------------------------------------------------------ freeze manifest preparation
def build(repo):
    return seal.build_freeze_manifest(repo.root, "docs/prereg/matrix.csv", CFG_REL, "python/pacman_rl/m.py", "python/pacman_rl/m.py",
                                      ["docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md", "docs/prereg/ANALYSIS_SPEC_v0.3.2.md"])


def test_manifest_can_be_prepared_with_uncommitted_freeze_files_and_records_c(repo):
    repo.cfg["code_commit"] = repo.C
    repo.write_cfg()
    (repo.root / "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md").write_text("SYNTHETIC FAKE preregistration text\n")
    (repo.root / "docs/prereg/ANALYSIS_SPEC_v0.3.2.md").write_text("SYNTHETIC FAKE analysis specification text\n")
    obj = build(repo)  # HEAD == C, only freeze material is uncommitted
    assert obj["code_commit"] == repo.C and obj["project_root"] == "." and set(obj["frozen_files"]) >= {CFG_REL, "docs/prereg/matrix.csv"}


def test_manifest_refuses_changed_code_or_a_missing_code_commit(repo):
    repo.cfg["code_commit"] = repo.C
    repo.write_cfg()
    (repo.root / "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md").write_text("SYNTHETIC FAKE\n")
    (repo.root / "docs/prereg/ANALYSIS_SPEC_v0.3.2.md").write_text("SYNTHETIC FAKE\n")
    (repo.root / "python/pacman_rl/m.py").write_text("x = 5\n")
    with pytest.raises(seal.ManifestError, match="uncommitted changes"):
        build(repo)
    (repo.root / "python/pacman_rl/m.py").write_text("x = 1\n")
    repo.cfg["code_commit"] = None
    repo.write_cfg()
    with pytest.raises(seal.ManifestError, match="40-hex"):
        build(repo)
