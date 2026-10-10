"""C2: the formal analysis verifies the sealed C / F, the current repository and the environment evidence BEFORE any score is looked at (ANALYSIS_SPEC 1.2, 8.6).

Throwaway git repositories (C = code commit, F = freeze commit, results ignored by git), a fake anonymous machine record and fully synthetic scores.  One defect at a
time on an otherwise valid formal study.  Only the standard library git is used by the analysis (no torch).  Implementer and test author are the same AI model."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
from prereg_fixture import Study, sha, write_json  # noqa: E402

D = {"cnn2": [10] * 5, "res4": [20] * 5, "res8": [30] * 5}


def formal(tmp_path, **kw):
    return Study(tmp_path / "p", d=D, formal=True, **kw)


def analyze(tmp_path, st, name="out"):
    out = tmp_path / name
    A.analyze(st.manifest, st.runs, out, "formal")
    return json.loads((out / "analysis.json").read_text()), out


def refuse(tmp_path, st, code):
    out = tmp_path / "out_fail"
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, out, "formal")
    assert e.value.obj["code"] == code, e.value.obj
    assert not out.exists()  # nothing that looks like a result is left behind
    return e.value.obj


def edit_env(st, fn):
    f = st.root / "results_prereg" / "final_eval_environment.json"
    d = json.loads(f.read_text())
    fn(d)
    write_json(f, d)
    st.reseal()  # the sealed hash follows the edit, so the fault under test is not masked by a stale hash


# ------------------------------------------------------------------ pass
def test_valid_formal_study_passes_and_the_provenance_lists_c_f_head_and_the_environment(tmp_path):
    st = formal(tmp_path)
    an, out = analyze(tmp_path, st)
    prov = an["provenance"]["protocol_evidence"]
    env = st.root / "results_prereg" / "final_eval_environment.json"
    assert prov["code_commit"] == st.commit and prov["freeze_commit"] == st.freeze_commit == prov["head"] == st.git("rev-parse", "HEAD")
    assert prov["final_eval_environment"] == {"path": "results_prereg/final_eval_environment.json", "sha256": sha(env), "machine_id": "synthetic"}
    assert st.commit != st.freeze_commit and len(prov["git_checks"]) == 5
    rep = (out / "REPORT.md").read_text()
    assert st.commit in rep and st.freeze_commit in rep and sha(env) in rep
    assert json.loads((out / "input_manifest.json").read_text())["protocol_evidence"] == prov
    # the core numbers are the F1 oracle (constant differences 10 / 20 / 30), unchanged by the provenance
    L = an["endpoints"]["last_standard"]["effects"]
    assert L["d"]["res4"]["raw_values"] == [20] * 5 and L["c"]["raw_values"] == [20] * 5 and an["primary_decisions"]["H1"]["label"] == "supported"
    assert an["primary_decisions"]["H2"]["label"] == "supported" and an["primary_decisions"]["res4_sign_test"]["p"] == 1 / 32


# ------------------------------------------------------------------ git relations
def test_c_that_is_not_an_ancestor_of_f_is_refused(tmp_path):
    refuse(tmp_path, formal(tmp_path, side_branch_c=True), "E_MANIFEST")


def test_protocol_evidence_c_that_differs_from_the_manifest_c_is_refused(tmp_path):
    st = formal(tmp_path)
    manifest = json.loads(st.manifest.read_text())
    seal = json.loads((st.root / "results_prereg" / "evaluation_seal.json").read_text())
    frozen = json.loads((st.prereg / "frozen_config_v0.3.2.json").read_text())
    with pytest.raises(A.AnalysisError) as e:
        A.check_protocol_evidence(st.root, {**manifest, "code_commit": "f" * 40}, frozen, seal, "results_prereg/evaluation_seal.json")
    assert e.value.obj["code"] == "E_MANIFEST" and "differs from the manifest" in e.value.obj["message"]
    A.check_protocol_evidence(st.root, manifest, frozen, seal, "results_prereg/evaluation_seal.json")  # unchanged inputs pass


def test_f_that_changes_python_is_refused(tmp_path):
    def pre(st):
        (st.root / "python/pacman_rl/window_diag.py").write_text("# changed in the freeze commit\n")  # frozen hash follows, so only the relation fails

    obj = refuse(tmp_path, formal(tmp_path, pre_f=pre), "E_MANIFEST")
    assert "python/ tree" in obj["message"]


def test_f_that_changes_the_matrix_is_refused(tmp_path):
    def pre(st):
        m = st.prereg / "matrix.csv"
        m.write_bytes(m.read_bytes().replace(b"prereg_res4_n1_s100", b"prereg_res4_n1_s100 ", 1))

    refuse(tmp_path, formal(tmp_path, pre_f=pre), "E_HASH_MISMATCH")  # the registered matrix hash is checked before the git relation (spec: earlier real hash error wins)


def test_f_with_a_non_permitted_file_is_refused(tmp_path):
    def pre(st):
        (st.root / "docs" / "README.md").write_text("a note added in the freeze commit\n")

    obj = refuse(tmp_path, formal(tmp_path, pre_f=pre), "E_MANIFEST")
    assert "six freeze-material files" in obj["message"]


def test_head_that_is_not_the_sealed_f_is_refused(tmp_path):
    st = formal(tmp_path)
    st.git("commit", "-q", "--allow-empty", "-m", "a later commit")
    obj = refuse(tmp_path, st, "E_MANIFEST")
    assert "HEAD is not the sealed freeze commit F" in obj["message"]


def test_a_dirty_tracked_file_is_refused(tmp_path):
    st = formal(tmp_path)
    (st.root / ".gitignore").write_text("results_prereg/\n# edited\n")
    obj = refuse(tmp_path, st, "E_MANIFEST")
    assert "uncommitted" in obj["message"]


def test_a_directory_that_is_not_a_git_repository_is_refused(tmp_path):
    st = formal(tmp_path)
    shutil.rmtree(st.root / ".git")
    refuse(tmp_path, st, "E_MANIFEST")


def test_git_missing_or_timing_out_is_refused_not_ignored(tmp_path, monkeypatch):
    st = formal(tmp_path)

    def boom(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(A.subprocess, "run", boom)
    obj = refuse(tmp_path, st, "E_MANIFEST")
    assert "git is unavailable" in obj["message"]


# ------------------------------------------------------------------ environment evidence
def test_missing_environment_file_is_refused(tmp_path):
    st = formal(tmp_path)
    (st.root / "results_prereg" / "final_eval_environment.json").unlink()
    refuse(tmp_path, st, "E_MISSING_FILE")


def test_environment_file_changed_after_sealing_is_a_hash_error(tmp_path):
    st = formal(tmp_path)
    f = st.root / "results_prereg" / "final_eval_environment.json"
    d = json.loads(f.read_text())
    d["utc"] = "2001-01-01T00:00:00Z"
    write_json(f, d)  # the seal is NOT refreshed
    refuse(tmp_path, st, "E_HASH_MISMATCH")


def test_missing_protocol_evidence_is_refused(tmp_path):
    st = formal(tmp_path)
    seal_path = st.root / "results_prereg" / "evaluation_seal.json"
    d = json.loads(seal_path.read_text())
    d.pop("protocol_evidence")
    write_json(seal_path, d)
    refuse(tmp_path, st, "E_MANIFEST")


@pytest.mark.parametrize("edit,what", [
    (lambda d: d.update(machine_id="other"), "machine_id"),
    (lambda d: d.pop("machine_id"), "machine_id"),
    (lambda d: d.update(evaluation_device="cuda"), "evaluation_device"),
    (lambda d: d["environment"].update(device_type="cuda"), "evaluation_device"),
    (lambda d: d["environment"].update(torch_threads=2), "torch_threads"),
    (lambda d: d["environment"].update(torch_threads=1.0), "torch_threads"),
    (lambda d: d["code_version"].update(git_sha="e" * 40), "git_sha"),
    (lambda d: d["code_version"].update(git_dirty=True), "git_sha"),
    (lambda d: d["preflight"].update(code_commit="e" * 40), "preflight"),
    (lambda d: d["preflight"].update(head="e" * 40), "preflight"),
    (lambda d: d["preflight"].update(freeze_commit_of_runs="e" * 40), "preflight"),
])
def test_wrong_machine_cpu_thread_or_commit_in_the_environment_file_is_refused(tmp_path, edit, what):
    st = formal(tmp_path)
    edit_env(st, edit)
    obj = refuse(tmp_path, st, "E_MANIFEST")
    assert what in obj["message"]


@pytest.mark.parametrize("edit", [
    lambda e: e.update(code_commit="e" * 40),
    lambda e: e.update(freeze_commit="e" * 40),
    lambda e: e.update(code_commit="short"),
    lambda e: e["final_eval_environment"].update(sha256="nothex"),
    lambda e: e.pop("final_eval_environment"),
    lambda e: e["final_eval_environment"].update(path="../outside.json"),
])
def test_malformed_or_inconsistent_protocol_evidence_is_refused(tmp_path, edit):
    st = formal(tmp_path)
    seal_path = st.root / "results_prereg" / "evaluation_seal.json"
    d = json.loads(seal_path.read_text())
    edit(d["protocol_evidence"])
    write_json(seal_path, d)
    refuse(tmp_path, st, "E_MANIFEST")


# ------------------------------------------------------------------ the configuration hashes and the mirrored constants
def test_configuration_main_hash_that_differs_from_the_manifest_is_refused_by_the_analysis_too(tmp_path):
    st = formal(tmp_path)
    # change the preregistration text hash in the CONFIGURATION only; keep the configuration's own manifest hash consistent
    cfg = st.prereg / "frozen_config_v0.3.2.json"
    d = json.loads(cfg.read_text())
    d["to_fill_at_freeze"]["preregistration_document_sha256"] = "ab" * 32
    write_json(cfg, d)
    st.write_manifest()
    st.reseal()
    obj = refuse(tmp_path, st, "E_CONFIG_MISMATCH")
    assert "preregistration_document_sha256" in obj["message"]


def test_the_dependency_snapshot_path_is_fixed_in_formal_mode(tmp_path):
    st = formal(tmp_path)
    m = json.loads(st.manifest.read_text())
    m["dependency_lock_path"] = "python/scripts/prereg_analysis.requirements.txt"
    write_json(st.manifest, m)
    refuse(tmp_path, st, "E_MANIFEST")


def test_the_analysis_mirrors_equal_the_training_packages_constants():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pacman_rl import freeze_binding as FB
    from pacman_rl import provenance as P

    assert set(A.REQUIRED_DOCS) == set(FB.REQUIRED_FROZEN) and A.LOCK_REL == FB.LOCK_REL
    assert set(A.FREEZE_MATERIALS) == set(P.FREEZE_MATERIALS)


def test_the_analysis_script_does_not_import_the_training_package():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "prereg_analysis.py").read_text()
    import re

    assert not re.search(r"^\s*(import torch|from torch|import pacman_rl|from pacman_rl)", src, re.M)
    out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import prereg_analysis; print('torch' in sys.modules)" % str(Path(A.__file__).parent)],
                         capture_output=True, text=True).stdout.strip()
    assert out == "False"
