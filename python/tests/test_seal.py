"""Guard of the sealed final test seeds: the integrity manifest, tamper detection, the explicit --unseal, one-shot
evaluation.  NOTE: no test here evaluates the real sealed seeds 30000-30299 -- the partition is replaced by throw-away
seeds (50000-50004) wherever an evaluation has to run, so the sealed seeds are never read by the test-suite."""
import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

from pacman_rl import evaluate as ev
from pacman_rl import prereg as PR
from pacman_rl import seal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402

FREEZE = PR.load_freeze()
TINY = dict(total_env_steps=96, learn_start=32, eval_every=48, buffer=600, batch=8, device="cpu", val_set="smoke_eval")
ROWS = [r for r in PR.load_matrix() if r["arch"] == "cnn2" and r["seed"] == 100]  # the n=1 and n=3 runs of one seed


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    results = tmp_path_factory.mktemp("study")
    assert set(runner.run_matrix(ROWS, FREEZE, results, 1, TINY).values()) == {"done"}
    script = results / "analysis.py"
    script.write_text("# placeholder analysis script\n")
    return results, script


@pytest.fixture()
def fresh(study, tmp_path):
    """A private copy of the finished mini-study, so a test can damage it."""
    results, script = study
    dst = tmp_path / "study"
    shutil.copytree(results, dst)
    return dst, dst / "analysis.py"


@pytest.fixture(autouse=True)
def throwaway_sealed_seeds(monkeypatch):
    monkeypatch.setitem(ev.SEED_SETS, "prereg_test", list(range(50000, 50005)))


def build(results, script, **kw):
    return seal.build_manifest(results, ROWS, FREEZE, script, allow_unfrozen=True, tiny_overrides=TINY, **kw)


def verify(results, script, manifest_path):
    return seal.verify_manifest(manifest_path, results, ROWS, FREEZE, script, allow_unfrozen=True, tiny_overrides=TINY)


# ------------------------------------------------------------------ token
def test_token_cannot_be_forged_and_unseals_only_through_the_manifest(fresh):
    with pytest.raises(TypeError):
        seal.UnsealToken(object(), "x")
    with pytest.raises(ev.SealedSetError):
        ev.seed_set("prereg_test", unseal="yes")
    results, script = fresh
    m = results / "m.json"
    seal.write_manifest(m, build(results, script))
    token = verify(results, script, m)
    assert ev.seed_set("prereg_test", token) == list(range(50000, 50005))  # the throw-away partition of this test module


# ------------------------------------------------------------------ manifest content
def test_manifest_records_every_run_hash_and_the_analysis_script(fresh):
    results, script = fresh
    man = build(results, script)
    assert man["complete"] is True and man["n_runs"] == 2 and man["failed_attempts_archived"] == 0
    assert set(man["runs"]) == {r["run_name"] for r in ROWS}
    one = man["runs"]["prereg_cnn2_n1_s100"]
    assert set(one) >= {"last_file_sha256", "best_file_sha256", "last_state_sha256", "best_state_sha256", "init_online_hash", "run_complete_sha256"}
    from pacman_rl.provenance import file_sha256
    assert man["analysis_script_sha256"] == file_sha256(script)


# ------------------------------------------------------------------ the guard refuses
def test_missing_or_unfinished_runs_block_the_manifest(fresh):
    results, script = fresh
    (results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json").unlink()
    with pytest.raises(seal.ManifestError, match="no run_complete.json"):
        build(results, script)


def _damage_and_expect(fresh, damage, expect, *, after_manifest):
    results, script = fresh
    m = results / "m.json"
    if after_manifest:
        seal.write_manifest(m, build(results, script))
        damage(results)
        with pytest.raises(seal.ManifestError, match=expect):
            verify(results, script, m)
    else:
        damage(results)
        with pytest.raises(seal.ManifestError, match=expect):
            build(results, script)


def test_tampered_checkpoint_is_detected_before_and_after_the_manifest(fresh, study):
    def flip(results):
        f = results / "runs" / "prereg_cnn2_n1_s100" / "last.pt"
        f.write_bytes(f.read_bytes() + b"\0")

    _damage_and_expect(fresh, flip, "does not match the hash recorded", after_manifest=False)
    results, script = study
    import tempfile

    tmp = Path(tempfile.mkdtemp()) / "s"
    shutil.copytree(results, tmp)
    _damage_and_expect((tmp, tmp / "analysis.py"), flip, "does not match the hash recorded|differ from the manifest", after_manifest=True)


def test_stray_test_output_or_failure_marker_blocks(fresh):
    _damage_and_expect(fresh, lambda r: (r / "runs" / "prereg_cnn2_n1_s100" / "test_standard.json").write_text("{}"), "forbidden files", after_manifest=False)
    _damage_and_expect(fresh, lambda r: (r / "runs" / "prereg_cnn2_n1_s100" / "failure.json").write_text("{}"), "failure.json", after_manifest=False)


def test_edited_run_record_and_configuration_drift_block(fresh):
    def edit(results):
        f = results / "runs" / "prereg_cnn2_n1_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["config"]["lr"] = 0.001
        f.write_text(json.dumps(d))

    _damage_and_expect(fresh, edit, "recorded configuration differs", after_manifest=False)


def test_different_initial_weights_for_n1_and_n3_block(fresh):
    def edit(results):
        f = results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["init_online_hash"] = "0" * 64
        f.write_text(json.dumps(d))

    _damage_and_expect(fresh, edit, "same initial weights", after_manifest=False)


def test_mixed_code_or_environment_block(fresh):
    def edit_code(results):
        f = results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["code_version"]["python_tree_sha256"] = "x"
        f.write_text(json.dumps(d))

    def edit_env(results):
        f = results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["environment"]["torch"] = "0.0.0"
        f.write_text(json.dumps(d))

    _damage_and_expect(fresh, edit_code, "different code versions", after_manifest=False)
    _damage_and_expect(fresh, edit_env, "different software/GPU environments", after_manifest=False)


def test_frozen_mode_demands_the_frozen_commit_and_the_frozen_analysis_hash(fresh):
    results, script = fresh
    with pytest.raises(seal.ManifestError, match="frozen commit|frozen hash"):
        seal.build_manifest(results, ROWS, FREEZE, script, allow_unfrozen=False, tiny_overrides=TINY)


def test_analysis_script_change_after_the_manifest_blocks(fresh):
    results, script = fresh
    m = results / "m.json"
    seal.write_manifest(m, build(results, script))
    script.write_text("# changed after sealing\n")
    with pytest.raises(seal.ManifestError, match="analysis script differs"):
        verify(results, script, m)


def test_missing_manifest_blocks(fresh):
    results, script = fresh
    with pytest.raises(seal.ManifestError, match="not found"):
        verify(results, script, results / "nope.json")
    (results / "bad.json").write_text(json.dumps({"version": 1, "complete": False}))
    with pytest.raises(seal.ManifestError, match="not a complete"):
        verify(results, script, results / "bad.json")


# ------------------------------------------------------------------ the final evaluation
def final(results, script, **kw):
    m = results / "m.json"
    if not m.exists():
        seal.write_manifest(m, build(results, script))
    return runner.final_eval(m, results, script, rows=ROWS, freeze=FREEZE, allow_unfrozen=True, tiny=TINY, **kw)


def test_final_eval_needs_the_explicit_unseal_flag(fresh):
    results, script = fresh
    with pytest.raises(runner.Refused, match="--unseal"):
        final(results, script, unseal=False)
    assert not (results / "runs" / "prereg_cnn2_n1_s100" / "eval_final").exists() and not (results / "unseal_log.jsonl").exists()


def test_final_eval_is_one_shot_and_writes_last_and_best_separately(fresh):
    results, script = fresh
    index = final(results, script, unseal=True)
    assert set(index) == {r["run_name"] for r in ROWS}
    for r in ROWS:
        out = results / "runs" / r["run_name"] / "eval_final"
        last = json.loads((out / "last" / "standard.json").read_text())
        best = json.loads((out / "best" / "standard.json").read_text())
        assert last["split"] == "prereg_test" and [x["seed"] for x in last["records"]] == list(range(50000, 50005))
        assert last["extra"]["torch_threads"] == 1 and last["extra"]["eval_device"] == "cpu" and best["agent"].endswith("/best")
        assert all("truncated" in x for x in last["records"])
    assert len((results / "unseal_log.jsonl").read_text().splitlines()) == 1
    assert "score" not in json.dumps(index)  # only file hashes are indexed
    # a second attempt cannot even be unsealed (the runs now contain eval_final) and never overwrites
    snapshot = (results / "runs" / ROWS[0]["run_name"] / "eval_final" / "last" / "standard.json").read_bytes()
    with pytest.raises((runner.Refused, FileExistsError)):
        final(results, script, unseal=True)
    assert (results / "runs" / ROWS[0]["run_name"] / "eval_final" / "last" / "standard.json").read_bytes() == snapshot


def test_identical_best_and_last_are_evaluated_once_and_say_so(fresh):
    results, script = fresh
    name = ROWS[0]["run_name"]
    run = results / "runs" / name
    shutil.copy(run / "last.pt", run / "best.pt")  # make best identical to last, then re-record the run (a unit-level setup)
    from pacman_rl.provenance import file_sha256

    d = json.loads((run / "run_complete.json").read_text())
    d["best_file_sha256"], d["best_state_sha256"] = d["last_file_sha256"], d["last_state_sha256"]
    (run / "run_complete.json").write_text(json.dumps(d))
    written = runner.final_eval_run(results, name, seal.UnsealToken(seal._ISSUE_KEY, "t"))
    best = json.loads((run / "eval_final" / "best" / "standard.json").read_text())
    last = json.loads((run / "eval_final" / "last" / "standard.json").read_text())
    assert best["records"] == last["records"] and best["extra"]["checkpoint"]["reused_from"] == "last"
    assert set(written) == {"last/standard", "best/standard"} and file_sha256(run / "best.pt") == d["best_file_sha256"]


def test_optional_hard_scenario_is_last_only(fresh):
    results, script = fresh
    final(results, script, unseal=True, hard=True)
    out = results / "runs" / ROWS[0]["run_name"] / "eval_final"
    assert (out / "last" / "hard.json").exists() and not (out / "best" / "hard.json").exists()


def test_the_real_sealed_seeds_are_not_what_these_tests_ran_on():
    assert ev.SEED_SETS["prereg_test"] == list(range(50000, 50005))  # the autouse fixture replaced the partition
