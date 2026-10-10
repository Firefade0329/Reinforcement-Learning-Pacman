"""C1: the final-evaluation environment evidence (machine_id) and the evaluation seal's `protocol_evidence` (C, F, environment file path / hash).

Temporary git repository, hand-written run_complete identities, the real save_final_eval_environment on the CPU.  One defect at a time on an otherwise valid state.
Implementer and test author are the same AI model; no real result is read."""
import json
import sys
from pathlib import Path

import pytest

from pacman_rl import prereg as PR
from pacman_rl import seal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402
from test_freeze_identity import Repo, sha_of  # noqa: E402

ROWS = PR.load_matrix()[:3]


@pytest.fixture()
def state(tmp_path, monkeypatch):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    F = r.freeze()
    res = r.root / "results_prereg"
    for row in ROWS:
        d = res / "runs" / row["run_name"]
        d.mkdir(parents=True)
        (d / "run_complete.json").write_text(json.dumps({"freeze_commit": F, "code_commit": r.C}))
    ev = runner.final_eval_preflight(r.cfg, res, ROWS, root=r.root)
    runner.save_final_eval_environment(res, r.cfg, ev, root=r.root)
    return r, res, F


def produce(r, res):
    return runner.evaluation_protocol_evidence(res, r.cfg, ROWS, root=r.root)


def edit_env(res, fn):
    f = res / "final_eval_environment.json"
    d = json.loads(f.read_text())
    fn(d)
    f.write_text(json.dumps(d, indent=1))


def test_environment_file_carries_the_anonymous_machine_id_and_keeps_its_old_fields(state):
    r, res, F = state
    d = json.loads((res / "final_eval_environment.json").read_text())
    assert d["machine_id"] == r.cfg["machine_id"] == "m"
    assert {"utc", "evaluation_device", "environment", "code_version", "preflight"} <= set(d) and d["environment"]["torch_threads"] == 1
    assert d["environment"]["device_type"] == "cpu" and d["code_version"]["git_sha"] == F and d["code_version"]["git_dirty"] is False
    assert d["preflight"]["code_commit"] == r.C and d["preflight"]["head"] == d["preflight"]["freeze_commit_of_runs"] == F


def test_correct_evidence_is_produced_with_the_environment_files_path_and_hash(state):
    r, res, F = state
    ev = produce(r, res)
    assert ev == {"code_commit": r.C, "freeze_commit": F, "final_eval_environment": {"path": "results_prereg/final_eval_environment.json", "sha256": sha_of(res / "final_eval_environment.json")}}


def test_saving_the_environment_needs_a_machine_id_in_the_frozen_configuration(state, tmp_path):
    r, res, F = state
    other = tmp_path / "other"
    other.mkdir()
    ev = runner.final_eval_preflight(r.cfg, res, ROWS, root=r.root)
    with pytest.raises(runner.Refused, match="no machine_id"):
        runner.save_final_eval_environment(other, {**r.cfg, "machine_id": None}, ev, root=r.root)


@pytest.mark.parametrize("edit,message", [
    (lambda d: d.pop("machine_id"), "machine_id None differs"),
    (lambda d: d.update(machine_id="other-machine"), "machine_id 'other-machine' differs"),
    (lambda d: d.update(machine_id=""), "machine_id '' differs"),
    (lambda d: d.update(evaluation_device="cuda"), "must run on the CPU"),
    (lambda d: d["environment"].update(device_type="cuda"), "must run on the CPU"),
    (lambda d: d["environment"].update(torch_threads=2), "torch_threads is 2"),
    (lambda d: d["code_version"].update(git_sha="e" * 40), "clean freeze commit F"),
    (lambda d: d["code_version"].update(git_dirty=True), "clean freeze commit F"),
    (lambda d: d["code_version"].update(git_dirty=None), "clean freeze commit F"),
    (lambda d: d["preflight"].update(code_commit="e" * 40), "head = freeze_commit_of_runs = F and code_commit = C"),
    (lambda d: d["preflight"].update(freeze_commit_of_runs="e" * 40), "head = freeze_commit_of_runs = F and code_commit = C"),
    (lambda d: d["preflight"].update(head="e" * 40), "head = freeze_commit_of_runs = F and code_commit = C"),
    (lambda d: d.update(preflight=None), "head = freeze_commit_of_runs = F and code_commit = C"),
])
def test_wrong_machine_cpu_thread_or_identity_evidence_is_refused(state, edit, message):
    r, res, F = state
    edit_env(res, edit)
    with pytest.raises(runner.Refused, match=message):
        produce(r, res)


def test_missing_environment_file_is_refused(state):
    r, res, F = state
    (res / "final_eval_environment.json").unlink()
    with pytest.raises(runner.Refused, match="final_eval_environment.json is missing"):
        produce(r, res)


def test_a_run_with_another_c_or_f_is_refused(state):
    r, res, F = state
    (res / "runs" / ROWS[1]["run_name"] / "run_complete.json").write_text(json.dumps({"freeze_commit": "e" * 40, "code_commit": r.C}))
    with pytest.raises(runner.Refused, match="do not all record code commit C"):
        produce(r, res)


def test_head_moved_or_dirty_tracked_file_or_material_drift_is_refused(state):
    r, res, F = state
    (r.root / "python/pacman_rl/m.py").write_text("x = 99\n")
    with pytest.raises(runner.Refused, match="uncommitted changes"):
        produce(r, res)
    (r.root / "python/pacman_rl/m.py").write_text("x = 1\n")
    produce(r, res)
    r.commit_file("docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md", "edited later\n")  # HEAD is no longer F and the frozen text drifted
    with pytest.raises(runner.Refused, match="differs from the frozen|freeze commit F"):
        produce(r, res)


def test_the_seal_carries_protocol_evidence_at_top_level_only_and_the_core_files_set_is_unchanged(state, monkeypatch):
    r, res, F = state
    ev = produce(r, res)
    # a minimal sealable study is built elsewhere (test_seal); here the seal builder is driven with the produced evidence
    captured = {}
    monkeypatch.setattr(seal, "build_evaluation_seal", lambda *a, protocol_evidence=None, **k: captured.update(ev=protocol_evidence) or {"x": 1})
    fm = res / "fm.json"
    fm.write_text("{}")
    runner.make_evaluation_seal(res, res / "m.json", fm, rows=ROWS, freeze=r.cfg, root=r.root)
    assert captured["ev"] == ev and (res / "evaluation_seal.json").is_file()


def test_the_formal_seal_is_refused_when_the_evidence_is_wrong_and_nothing_is_written(state):
    r, res, F = state
    edit_env(res, lambda d: d.update(machine_id="other-machine"))
    fm = res / "fm.json"
    fm.write_text("{}")
    with pytest.raises(runner.Refused, match="machine_id"):
        runner.make_evaluation_seal(res, res / "m.json", fm, rows=ROWS, freeze=r.cfg, root=r.root)
    assert not (res / "evaluation_seal.json").exists()


@pytest.fixture(scope="module")
def study_for_seal(tmp_path_factory):
    import test_seal as TS

    mp = pytest.MonkeyPatch()
    for var in runner.FORBIDDEN_ENV:  # a module-scoped fixture is built before the per-test environment cleanup of conftest.py
        mp.delenv(var, raising=False)
    mp.setattr(PR, "load_freeze", lambda path=None: TS.FREEZE)
    results = tmp_path_factory.mktemp("seal_study")
    assert set(runner.run_matrix(TS.ROWS, TS.FREEZE, results, 1, TS.TINY).values()) == {"done"}
    script = results / "analysis.py"
    script.write_text("# placeholder\n")
    mp.setattr(TS.ev, "SEED_SETS", {**TS.ev.SEED_SETS, "prereg_test": list(range(50000, 50005))})
    pre = results / "m.json"
    seal.write_manifest(pre, TS.build(results, script))
    TS.final(results, script, unseal=True)
    fm = results / "fm.json"
    fm.write_text("{}")
    yield results, TS.ROWS, TS.FREEZE, pre, fm
    mp.undo()


def test_build_evaluation_seal_adds_protocol_evidence_without_touching_files(study_for_seal):
    results, rows, freeze, pre, fm = study_for_seal
    plain = seal.build_evaluation_seal(results, rows, freeze, pre, fm)
    with_ev = seal.build_evaluation_seal(results, rows, freeze, pre, fm, protocol_evidence={"code_commit": "c" * 40})
    assert "protocol_evidence" not in plain and with_ev["protocol_evidence"] == {"code_commit": "c" * 40}
    assert {k: v for k, v in with_ev.items() if k != "protocol_evidence"} == plain
