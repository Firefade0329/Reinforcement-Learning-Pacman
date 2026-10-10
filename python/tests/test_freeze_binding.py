"""The freeze binding check (configuration <-> manifest <-> actual files) at BOTH formal entries, with real temporary git repositories.

The counter-examples are those of the freeze rehearsal: the preregistration text changed after F, a configuration hash set to all zeros, the
manifest deleted, ... Every case changes exactly one thing in an otherwise valid frozen state; the manifest of the valid state is written by
hand in the fixture (not by the code under test).  Spies prove that when the check fails nothing was started: no training task, no
subprocess, no environment step, no unseal permission, no read of the sealed partition.  Implementer and test author are the same AI model."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pacman_rl import freeze_binding as FB
from pacman_rl import prereg as PR
from pacman_rl import seal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402
from test_freeze_identity import ANALYSIS_REL, CFG_REL, LOCK_REL, MAN_REL, Repo, prepare, sha_of  # noqa: E402

PREREG = "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md"
SPEC = "docs/prereg/ANALYSIS_SPEC_v0.3.2.md"
ROWS = PR.load_matrix()[:3]
ZERO = "0" * 64


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    r.freeze()
    return r


def results_for(repo, F):
    res = repo.root / "results_prereg"
    for row in ROWS:
        d = res / "runs" / row["run_name"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "run_complete.json").write_text(json.dumps({"freeze_commit": F, "code_commit": repo.C}))
    return res


def train_entry(repo):
    return runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root)


def final_entry(repo):
    return runner.final_eval_preflight(repo.cfg, results_for(repo, repo.git("rev-parse", "HEAD")), ROWS, root=repo.root)


ENTRIES = [pytest.param(train_entry, id="training"), pytest.param(final_entry, id="final-eval")]


@pytest.mark.parametrize("entry", ENTRIES)
def test_a_valid_frozen_state_passes_both_entries(repo, entry):
    entry(repo)


@pytest.mark.parametrize("entry", ENTRIES)
def test_preregistration_text_changed_and_committed_after_f_is_refused(repo, entry):
    repo.commit_file(PREREG, "SYNTHETIC FAKE preregistration text, edited after the freeze\n")  # a freeze-material file, so git alone allows it
    with pytest.raises(runner.Refused, match=rf"{PREREG}: the file's SHA-256 .* differs from the frozen"):
        entry(repo)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("field", ["analysis_script_sha256", "preregistration_document_sha256", "dependency_lock_sha256"])
def test_each_of_the_three_main_hashes_set_to_zero_is_refused_by_name(repo, entry, field):
    repo.amend_cfg(lambda c: c["to_fill_at_freeze"].__setitem__(field, ZERO))  # manifest's hash of the configuration is refreshed: nothing masks the fault
    with pytest.raises(runner.Refused, match=rf"to_fill_at_freeze\.{field} is not a real SHA-256"):
        entry(repo)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("field,target", [("analysis_script_sha256", ANALYSIS_REL), ("preregistration_document_sha256", PREREG), ("dependency_lock_sha256", LOCK_REL)])
def test_a_main_hash_that_differs_from_the_manifest_entry_is_refused(repo, entry, field, target):
    repo.amend_cfg(lambda c: c["to_fill_at_freeze"].__setitem__(field, "ab" * 32))
    with pytest.raises(runner.Refused, match=rf"to_fill_at_freeze\.{field} {'ab' * 32} differs from the manifest entry for {target}"):
        entry(repo)


@pytest.mark.parametrize("entry", ENTRIES)
def test_missing_manifest_is_refused(repo, entry):
    repo.git("rm", "-q", MAN_REL)
    repo.git("commit", "-qm", "drop the manifest")
    with pytest.raises(runner.Refused, match="freeze_manifest.json: missing"):
        entry(repo)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("edit,message", [
    (lambda m: m.update(complete=False), "complete must be true"),
    (lambda m: m.update(synthetic=True), "synthetic must be false"),
    (lambda m: m.update(code_commit="d" * 40), "code_commit 'dddd.*' differs from the frozen configuration"),
    (lambda m: m.update(spec_version="0.3.1"), "schema_version / spec_version"),
    (lambda m: m["frozen_files"].pop(PREREG), f"required frozen file '{PREREG}' is not listed"),
    (lambda m: m["frozen_files"].pop(SPEC), f"required frozen file '{SPEC}' is not listed"),
    (lambda m: m["frozen_files"].pop(LOCK_REL), f"required frozen file '{LOCK_REL}' is not listed"),
    (lambda m: m["frozen_files"].pop(ANALYSIS_REL), f"required frozen file '{ANALYSIS_REL}' is not listed"),
    (lambda m: m["frozen_files"].__setitem__("../outside.txt", "ab" * 32), "not a relative path inside the project"),
    (lambda m: m["frozen_files"].__setitem__("docs/prereg/ghost.txt", "ab" * 32), "ghost.txt: listed in frozen_files but the file is missing"),
    (lambda m: m["frozen_files"].__setitem__(PREREG, "short"), "is not 64 lower-case hex"),
])
def test_manifest_defects_are_refused(repo, entry, edit, message):
    repo.amend_manifest(edit)
    with pytest.raises(runner.Refused, match=message):
        entry(repo)


def test_extra_frozen_file_drift_and_removal_are_refused(repo):
    # extra-frozen files are checked too, not only the main three.  The extra file is part of C (a code-side file), listed in the manifest at F
    repo2_root = repo.root
    (repo2_root / "python/pacman_rl/extra_frozen.txt").write_text("extra\n")
    repo.git("add", "-A")
    repo.git("commit", "-qm", "extra code-side file")
    repo.C = repo.git("rev-parse", "HEAD")
    repo.freeze()
    repo.amend_manifest(lambda m: m["frozen_files"].__setitem__("python/pacman_rl/extra_frozen.txt", sha_of(repo2_root / "python/pacman_rl/extra_frozen.txt")))
    train_entry(repo)  # intact: passes
    (repo2_root / "python/pacman_rl/extra_frozen.txt").write_text("drifted\n")
    with pytest.raises(runner.Refused, match="extra_frozen.txt: the file's SHA-256 .* differs from the frozen"):
        train_entry(repo)
    (repo2_root / "python/pacman_rl/extra_frozen.txt").unlink()
    with pytest.raises(runner.Refused, match="extra_frozen.txt: listed in frozen_files but the file is missing"):
        train_entry(repo)


def test_the_matrix_must_carry_the_registered_hash_in_the_manifest(repo):
    repo.amend_manifest(lambda m: m["frozen_files"].__setitem__("docs/prereg/matrix.csv", "ab" * 32))
    with pytest.raises(runner.Refused, match="matrix.csv"):
        train_entry(repo)


def test_success_leaves_identity_evidence(repo):
    ev: dict = {}
    runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root, evidence=ev)
    assert ev["binding_passed"] is True and ev["head"] == repo.git("rev-parse", "HEAD") and ev["code_commit"] == repo.C
    assert ev["freeze_manifest_sha256"] == sha_of(repo.root / MAN_REL) and ev["checked_utc"].endswith("Z") and ev["files_checked"] >= 6


# ------------------------------------------------------------------ nothing is started when the check fails
class Spies:
    """Counts the calls that would start something.  The dangerous ones never run for real, even if the code under test were wrong."""

    def __init__(self, monkeypatch):
        self.calls = {"execute": 0, "subprocess": 0, "env_step": 0, "verify_manifest": 0, "final_eval_run": 0, "seed_set": 0, "save_env": 0}
        import pacman_rl.env as env
        import pacman_rl.evaluate as ev

        def stub(name, result=None):
            def f(*a, **k):
                self.calls[name] += 1
                return result
            return f

        real_run = subprocess.run

        def run(cmd, *a, **k):  # git (the identity checks themselves) is fine; a training / evaluation subprocess is not
            if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
                return real_run(cmd, *a, **k)
            self.calls["subprocess"] += 1
            return subprocess.CompletedProcess(cmd, 1)

        monkeypatch.setattr(runner, "execute", stub("execute", "failed"))
        monkeypatch.setattr(subprocess, "run", run)
        monkeypatch.setattr(env.PacmanEnv, "step", stub("env_step"))
        monkeypatch.setattr(seal, "verify_manifest", stub("verify_manifest"))
        monkeypatch.setattr(runner, "final_eval_run", stub("final_eval_run", {}))
        monkeypatch.setattr(ev, "seed_set", stub("seed_set", []))
        monkeypatch.setattr(runner, "save_final_eval_environment", stub("save_env"))

    def started(self):
        return {k: v for k, v in self.calls.items() if v}


def point_cli_at(repo, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", repo.root)
    monkeypatch.setattr(PR, "FREEZE_FILE", repo.root / CFG_REL)
    monkeypatch.setattr(PR, "ROOT", repo.root)


def test_training_cli_fails_non_zero_and_starts_nothing_when_the_binding_is_broken(repo, monkeypatch):
    repo.commit_file(PREREG, "edited after the freeze\n")
    point_cli_at(repo, monkeypatch)
    spies = Spies(monkeypatch)
    with pytest.raises(SystemExit) as e:
        runner.main(["run", "--workers", "2", "--results-dir", str(repo.root / "results_prereg")])
    assert e.value.code not in (0, None) and "differs from the frozen" in str(e.value.code)
    assert spies.started() == {}  # no task, no subprocess, no environment step
    assert not (repo.root / "results_prereg").exists()  # not even the results directory (and no success evidence) was created


def test_training_cli_with_a_valid_state_passes_the_gate_and_records_the_evidence(repo, monkeypatch):
    point_cli_at(repo, monkeypatch)
    monkeypatch.setattr(runner, "execute", lambda *a, **k: "done")  # the gate is the subject; no training here
    assert runner.main(["run", "--workers", "2", "--results-dir", str(repo.root / "results_prereg")]) == 0
    line = json.loads((repo.root / "results_prereg" / "preflight_log.jsonl").read_text().splitlines()[0])
    assert line["binding_passed"] is True and line["head"] == repo.git("rev-parse", "HEAD") and line["workers"] == 2


def test_final_evaluation_refuses_before_any_permission_or_test_seed_read(repo, monkeypatch):
    F = repo.git("rev-parse", "HEAD")
    results = results_for(repo, F)
    repo.commit_file(PREREG, "edited after the freeze\n")
    monkeypatch.setattr(PR, "load_freeze", lambda path=None: repo.cfg)
    spies = Spies(monkeypatch)
    manifest = results / "m.json"
    manifest.write_text("{}")
    with pytest.raises(runner.Refused, match="differs from the frozen"):
        runner.final_eval(manifest, results, repo.root / ANALYSIS_REL, unseal=True, rows=ROWS, freeze=repo.cfg, root=repo.root)
    assert spies.started() == {}  # no unseal permission issued, no sealed partition read, no evaluation, no environment evidence
    assert not (results / "unseal_log.jsonl").exists() and not (results / "final_eval_environment.json").exists()


def test_real_cli_on_the_draft_repository_exits_non_zero():
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, str(root / "python/scripts/prereg.py"), "run", "--workers", "2", "--results-dir", str(root / "results_prereg_cli_probe")],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(root / "python"), "HOME": "/tmp"})
    assert r.returncode != 0 and not (root / "results_prereg_cli_probe").exists()


# ------------------------------------------------------------------ the generator needs no older manifest and applies the same rules
GEN = (CFG_REL, ANALYSIS_REL, LOCK_REL)


def generate(repo, **kw):
    return seal.build_freeze_manifest(repo.root, "docs/prereg/matrix.csv", CFG_REL, ANALYSIS_REL, LOCK_REL, **kw)


def test_generator_works_without_an_existing_manifest_and_its_output_passes_the_check(tmp_path, monkeypatch):
    r = Repo(tmp_path / "g")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    prepare(r)  # no freeze_manifest.json anywhere
    assert not (r.root / MAN_REL).exists()
    man = generate(r)
    (r.root / MAN_REL).write_text(json.dumps(man, indent=1, sort_keys=True))
    problems, ev = FB.binding_check(r.root)
    assert problems == [] and ev["binding_passed"] is True and man["frozen_files"][CFG_REL] == sha_of(r.root / CFG_REL)


@pytest.mark.parametrize("field", ["analysis_script_sha256", "preregistration_document_sha256", "dependency_lock_sha256"])
def test_generator_refuses_a_configuration_whose_hash_fields_do_not_match_the_files(tmp_path, monkeypatch, field):
    r = Repo(tmp_path / "g")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    prepare(r)
    r.cfg["to_fill_at_freeze"][field] = ZERO
    r.write_cfg()
    with pytest.raises(seal.ManifestError, match=field):
        generate(r)


def test_gitattributes_is_a_required_frozen_file(repo):
    repo.amend_manifest(lambda m: m["frozen_files"].pop(".gitattributes"))
    with pytest.raises(runner.Refused, match=r"required frozen file '\.gitattributes' is not listed"):
        train_entry(repo)


def test_generator_refuses_a_frozen_path_that_has_no_text_rule(tmp_path, monkeypatch):
    r = Repo(tmp_path / "g")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    (r.root / "tools").mkdir()
    (r.root / "tools" / "extra.txt").write_text("outside every -text rule\n")
    r.git("add", "-A")
    r.git("commit", "-qm", "extra")
    r.C = r.git("rev-parse", "HEAD")
    prepare(r)
    with pytest.raises(seal.ManifestError, match=r"without a -text rule.*tools/extra.txt"):
        generate(r, extra_frozen=["tools/extra.txt"])


# ------------------------------------------------------------------ the dependency snapshot (C7)
from pacman_rl import freeze_binding as FBm  # noqa: E402

GOOD = b"matplotlib==3.9.0\nnumpy==2.0.0\npytest==8.0.0\ntorch==2.5.1+cu121\n"


def test_a_snapshot_committed_with_c_passes_both_entries(repo):
    train_entry(repo)
    final_entry(repo)


@pytest.mark.parametrize("data,message", [
    (b"\xef\xbb\xbf" + GOOD, "BOM"),
    (GOOD.replace(b"\n", b"\r\n"), "CR characters"),
    (GOOD[:-1], "exactly one newline"),
    (GOOD + b"\n", "exactly one newline"),
    (b"numpy==2.0.0\nmatplotlib==3.9.0\npytest==8.0.0\ntorch==2.5.1\n", "not sorted"),
    (b"matplotlib>=3.9\nnumpy==2.0.0\npytest==8.0.0\ntorch==2.5.1\n", "not an exact"),
    (b"# freeze\n" + GOOD, "not an exact"),
    (b"-e git+https://example.invalid/x#egg=x\n" + GOOD, "not an exact"),
    (GOOD + b"wheel @ file:///tmp/wheel.whl\n", "not an exact"),
    (b"matplotlib==3.9.0\nnumpy==2.0.0\npytest==8.0.0\n", "torch is missing"),
    (b"numpy==2.0.0\ntorch==2.5.1\n", "matplotlib is missing"),
    (b"matplotlib==3.9.0\nnumpy==2.0.0\nnumpy==2.0.1\npytest==8.0.0\ntorch==2.5.1\n", "more than once"),
    (b"\xff\xfe", "UTF-8"),
    (b"", "empty"),
])
def test_snapshot_format_defects_are_refused(data, message):
    assert any(message in x for x in FBm.lock_problems(data)), FBm.lock_problems(data)


def test_exact_snapshot_with_local_version_suffix_and_mixed_case_sorted_like_pip_is_accepted():
    data = b"Jinja2==3.1.4\nMarkupSafe==2.1.5\nmatplotlib==3.9.0\nnumpy==2.0.0\npytest==8.0.0\ntorch==2.5.1+cu121\ntyping_extensions==4.12.2\n"
    assert FBm.lock_problems(data) == []


def test_binding_check_applies_the_format_to_the_committed_snapshot(repo):
    repo.commit_file(LOCK_REL, "numpy>=1\n")  # a requirements-style file posing as the snapshot (hash fields refreshed so only the format is at fault)
    repo.amend_cfg(lambda c: c["to_fill_at_freeze"].__setitem__("dependency_lock_sha256", sha_of(repo.root / LOCK_REL)))
    repo.amend_manifest(lambda m: m["frozen_files"].__setitem__(LOCK_REL, sha_of(repo.root / LOCK_REL)))
    with pytest.raises(runner.Refused, match="dependency_lock.txt: .*not an exact"):
        train_entry(repo)


def test_wrong_snapshot_path_is_refused(repo):
    repo.amend_manifest(lambda m: m.update(dependency_lock_path="python/requirements.txt"))
    with pytest.raises(runner.Refused, match="dependency_lock_path must be docs/prereg/dependency_lock.txt"):
        train_entry(repo)


def test_the_analysis_numpy_file_cannot_pose_as_the_snapshot(repo):
    req = "python/scripts/prereg_analysis.requirements.txt"
    repo.amend_manifest(lambda m: m.update(dependency_lock_path=req))
    with pytest.raises(runner.Refused, match="dependency_lock_path must be"):
        train_entry(repo)
    # and it is frozen separately: leaving it out is refused too
    repo2 = repo
    repo2.amend_manifest(lambda m: (m.update(dependency_lock_path=LOCK_REL), m["frozen_files"].pop(req)))
    with pytest.raises(runner.Refused, match=rf"required frozen file '{req}' is not listed"):
        train_entry(repo2)


def test_snapshot_first_added_or_changed_in_f_is_refused(tmp_path, monkeypatch):
    r = Repo(tmp_path / "late")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    r.git("rm", "-q", LOCK_REL)  # the snapshot is NOT part of C ...
    r.git("commit", "-qm", "C without the snapshot")
    r.C = r.git("rev-parse", "HEAD")
    (r.root / LOCK_REL).write_bytes(GOOD)  # ... and appears first in F
    r.freeze()
    with pytest.raises(runner.Refused, match="dependency_lock.txt does not exist in the code commit C"):
        train_entry(r)
    # changed in F (present in C): the C->F rule refuses it, the lock is not freeze material
    r2 = Repo(tmp_path / "changed")
    r2.commit_file(LOCK_REL, GOOD.decode())
    r2.C = r2.git("rev-parse", "HEAD")
    r2.freeze()
    train_entry(r2)
    r2.commit_file(LOCK_REL, GOOD.decode().replace("2.0.0", "2.0.1"))
    with pytest.raises(runner.Refused, match="not freeze material.*dependency_lock.txt"):
        train_entry(r2)


def test_generator_refuses_a_missing_snapshot_in_c_and_a_bad_format(tmp_path, monkeypatch):
    r = Repo(tmp_path / "gen")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    r.commit_file(LOCK_REL, "torch>=2\n")
    r.C = r.git("rev-parse", "HEAD")
    prepare(r)
    with pytest.raises(seal.ManifestError, match="dependency_lock.txt: .*not an exact"):
        generate(r)


# ------------------------------------------------------------------ every mandatory frozen item (C3)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("rel", sorted(FBm.REQUIRED_FROZEN))
def test_each_mandatory_frozen_item_must_be_listed(repo, entry, rel):
    if rel == "docs/prereg/frozen_config_v0.3.2.json":
        pytest.skip("the configuration's own entry is covered by the configuration-hash tests")
    repo.amend_manifest(lambda m: m["frozen_files"].pop(rel))
    with pytest.raises(runner.Refused, match=rf"required frozen file '{rel}' is not listed"):
        entry(repo)


@pytest.mark.parametrize("rel", ["docs/prereg/CLAUDE_HANDOFF_v0.3.2.md", "docs/prereg/FREEZE_CHECKLIST.md", "python/pacman_rl/window_diag.py",
                                 "python/scripts/window_diagnostics_summary.py", ".gitattributes", "python/scripts/prereg_analysis.requirements.txt"])
def test_actual_drift_of_each_mandatory_item_is_refused(repo, rel):
    (repo.root / rel).write_bytes((repo.root / rel).read_bytes() + b"\n# drift\n")
    repo.git("add", "-A")
    repo.git("commit", "-qm", f"drift {rel}")
    with pytest.raises(runner.Refused, match=rf"{rel.replace('.', r'[.]')}: the file's SHA-256 .* differs from the frozen"):
        train_entry(repo)


def test_the_manifest_never_lists_itself(repo):
    man = json.loads((repo.root / MAN_REL).read_text())
    assert MAN_REL not in man["frozen_files"]
