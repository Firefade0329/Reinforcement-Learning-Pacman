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

FREEZE = {**PR.load_freeze(), "hard_enabled": False, "code_commit": "c" * 40}  # the draft file leaves it open; the tests declare it
TINY = dict(total_env_steps=96, learn_start=32, eval_every=48, buffer=600, batch=8, device="cpu", val_set="smoke_eval")
ROWS = [r for r in PR.load_matrix() if r["arch"] == "cnn2" and r["seed"] == 100]  # the n=1 and n=3 runs of one seed


@pytest.fixture(scope="module", autouse=True)
def declared_hard_flag():
    mp = pytest.MonkeyPatch()
    mp.setattr(PR, "load_freeze", lambda path=None: FREEZE)
    yield
    mp.undo()


@pytest.fixture(scope="module")
def study(tmp_path_factory, declared_hard_flag):
    results = tmp_path_factory.mktemp("study")
    assert set(runner.run_matrix(ROWS, FREEZE, results, 1, TINY).values()) == {"done"}
    script = results / "analysis.py"
    script.write_text("# placeholder analysis script\n", newline="\n")
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
    _damage_and_expect(fresh, lambda r: (r / "runs" / "prereg_cnn2_n1_s100" / "test_standard.json").write_text("{}", newline="\n"), "forbidden files", after_manifest=False)
    _damage_and_expect(fresh, lambda r: (r / "runs" / "prereg_cnn2_n1_s100" / "failure.json").write_text("{}", newline="\n"), "failure.json", after_manifest=False)


def test_edited_run_record_and_configuration_drift_block(fresh):
    def edit(results):
        f = results / "runs" / "prereg_cnn2_n1_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["config"]["lr"] = 0.001
        f.write_text(json.dumps(d), newline="\n")

    _damage_and_expect(fresh, edit, "recorded configuration differs", after_manifest=False)


def test_different_initial_weights_for_n1_and_n3_block(fresh):
    def edit(results):
        f = results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["init_online_hash"] = "0" * 64
        f.write_text(json.dumps(d), newline="\n")

    _damage_and_expect(fresh, edit, "same initial weights", after_manifest=False)


def test_mixed_code_or_environment_block(fresh):
    def edit_code(results):
        f = results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["code_version"]["python_tree_sha256"] = "x"
        f.write_text(json.dumps(d), newline="\n")

    def edit_env(results):
        f = results / "runs" / "prereg_cnn2_n3_s100" / "run_complete.json"
        d = json.loads(f.read_text())
        d["environment"]["torch"] = "0.0.0"
        f.write_text(json.dumps(d), newline="\n")

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
    script.write_text("# changed after sealing\n", newline="\n")
    with pytest.raises(seal.ManifestError, match="analysis script differs"):
        verify(results, script, m)


def test_missing_manifest_blocks(fresh):
    results, script = fresh
    with pytest.raises(seal.ManifestError, match="not found"):
        verify(results, script, results / "nope.json")
    (results / "bad.json").write_text(json.dumps({"version": 1, "complete": False}), newline="\n")
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
    run = results / "runs" / "prereg_cnn2_n1_s100"
    assert not (run / "last").exists() and not (run / "best").exists() and not (results / "unseal_log.jsonl").exists()


def test_final_eval_is_one_shot_writes_the_contract_layout_and_format(fresh):
    results, script = fresh
    index = final(results, script, unseal=True)
    assert set(index) == {r["run_name"] for r in ROWS}
    for r in ROWS:
        run = results / "runs" / r["run_name"]
        last = json.loads((run / "last" / "standard.json").read_text())
        best = json.loads((run / "best" / "standard.json").read_text())
        for ckpt, doc in (("last", last), ("best", best)):
            assert set(doc) == {"schema_version", "meta", "records"} and doc["schema_version"] == "prereg-eval-1"
            m = doc["meta"]
            assert m["synthetic"] is False and m["run_name"] == r["run_name"] and m["arch"] == r["arch"] and m["n_step"] == r["n_step"]
            assert m["train_seed"] == 100 and m["checkpoint"] == ckpt and m["scenario"] == "standard" and m["device"] == "cpu" and m["torch_threads"] == 1
            assert len(m["weights_sha256"]) == 64 and len(m["code_commit"]) == 40 and isinstance(m["checkpoint_step"], int)
            assert [x["seed"] for x in doc["records"]] == list(range(50000, 50005))  # throw-away partition of this module
            assert all(set(x) == {"seed", "score", "steps", "died", "won", "truncated"} for x in doc["records"])
        assert not (run / "last" / "hard.json").exists()  # hard_enabled is false
    assert len((results / "unseal_log.jsonl").read_text().splitlines()) == 1
    assert "score" not in json.dumps(index)  # only file hashes are indexed
    # a second attempt cannot even be unsealed (the runs now contain last/ and best/) and never overwrites
    snap = (results / "runs" / ROWS[0]["run_name"] / "last" / "standard.json").read_bytes()
    with pytest.raises((runner.Refused, FileExistsError)):
        final(results, script, unseal=True)
    assert (results / "runs" / ROWS[0]["run_name"] / "last" / "standard.json").read_bytes() == snap


def test_formal_final_eval_runs_the_training_gate_before_anything_is_read(fresh, monkeypatch):
    results, script = fresh
    m = results / "m.json"
    seal.write_manifest(m, build(results, script))
    calls = []

    def refuse(freeze, res, rows, *, root=None):
        calls.append(1)
        raise runner.Refused("refusing the final evaluation: gate")

    monkeypatch.setattr(runner, "final_eval_preflight", refuse)
    with pytest.raises(runner.Refused, match="gate"):  # allow_unfrozen=False: the same preflight as before training
        runner.final_eval(m, results, script, rows=ROWS, freeze=FREEZE, allow_unfrozen=False, tiny=TINY, unseal=True)
    assert calls == [1] and not (results / "unseal_log.jsonl").exists() and not (results / "final_eval_environment.json").exists()


def test_final_eval_saves_the_evaluation_environment_before_the_seeds_are_read(fresh):
    results, script = fresh
    final(results, script, unseal=True)
    env = json.loads((results / "final_eval_environment.json").read_text())
    assert env["evaluation_device"] == FREEZE["final_eval_device"] and env["environment"]["torch"]
    assert env["utc"] <= json.loads((results / "unseal_log.jsonl").read_text().splitlines()[0])["utc"]
    assert (results / "final_eval_environment.json").stat().st_mtime_ns <= (results / "unseal_log.jsonl").stat().st_mtime_ns


def test_identical_best_and_last_are_evaluated_once_and_say_so(fresh):
    results, script = fresh
    name = ROWS[0]["run_name"]
    run = results / "runs" / name
    shutil.copy(run / "last.pt", run / "best.pt")  # make best identical to last, then re-record the run (a unit-level setup)
    d = json.loads((run / "run_complete.json").read_text())
    d["best_file_sha256"], d["best_state_sha256"] = d["last_file_sha256"], d["last_state_sha256"]
    (run / "run_complete.json").write_text(json.dumps(d), newline="\n")
    written = runner.final_eval_run(results, name, seal.UnsealToken(seal._ISSUE_KEY, "t"), FREEZE)
    best = json.loads((run / "best" / "standard.json").read_text())
    last = json.loads((run / "last" / "standard.json").read_text())
    assert best["records"] == last["records"] and best["meta"]["reused_from"] == "last" and best["meta"]["checkpoint"] == "best"
    assert best["meta"]["weights_sha256"] == last["meta"]["weights_sha256"]
    assert set(written) == {"last/standard", "best/standard"}


def test_optional_hard_scenario_is_last_only_and_only_if_declared(fresh):
    results, script = fresh
    name = ROWS[0]["run_name"]
    token = seal.UnsealToken(seal._ISSUE_KEY, "t")
    with pytest.raises(runner.Refused, match="hard_enabled must be declared"):
        runner.final_eval_run(results, name, token, {**FREEZE, "hard_enabled": None})
    runner.final_eval_run(results, name, token, {**FREEZE, "hard_enabled": True})
    run = results / "runs" / name
    h = json.loads((run / "last" / "hard.json").read_text())
    assert h["meta"]["scenario"] == "hard" and h["meta"]["checkpoint"] == "last" and not (run / "best" / "hard.json").exists()


def test_the_real_sealed_seeds_are_not_what_these_tests_ran_on():
    assert ev.SEED_SETS["prereg_test"] == list(range(50000, 50005))  # the autouse fixture replaced the partition


# ------------------------------------------------------------------ evaluation seal and freeze manifest (analysis inputs)
def test_evaluation_seal_hashes_every_file_the_analysis_reads(fresh):
    results, script = fresh
    final(results, script, unseal=True)
    fm = results / "freeze_manifest.json"
    fm.write_text("{}", newline="\n")
    out = runner.make_evaluation_seal(results, results / "m.json", fm, rows=ROWS, freeze=FREEZE, allow_unfrozen=True)
    obj = json.loads((results / "evaluation_seal.json").read_text())
    assert obj["schema_version"] == "prereg-seal-1" and obj["synthetic"] is False and obj["all_training_complete"] is True
    assert obj["all_checkpoint_checks_passed"] is True and obj["runs"] == [r["run_name"] for r in ROWS] and obj["attempts"] == []
    from pacman_rl.provenance import file_sha256

    assert obj["freeze_manifest_sha256"] == file_sha256(fm)
    want = {f"{r['run_name']}/{rel}" for r in ROWS for rel in ("config.json", "summary.json", "last/standard.json", "best/standard.json")}
    assert set(obj["files"]) == want  # no hard files: hard_enabled is false
    for key, h in obj["files"].items():
        assert h == file_sha256(results / "runs" / key.split("/", 1)[0] / key.split("/", 1)[1])
    with pytest.raises(runner.Refused, match="already exists"):
        runner.make_evaluation_seal(results, results / "m.json", fm, rows=ROWS, freeze=FREEZE, allow_unfrozen=True)


def test_evaluation_seal_refuses_missing_files_changed_checkpoints_and_undeclared_hard(fresh):
    results, script = fresh
    final(results, script, unseal=True)
    fm = results / "fm.json"
    fm.write_text("{}", newline="\n")
    run = results / "runs" / ROWS[0]["run_name"]
    (run / "best" / "standard.json").rename(run / "best" / "standard.json.moved")
    with pytest.raises(seal.ManifestError, match="required file best/standard.json missing"):
        seal.build_evaluation_seal(results, ROWS, FREEZE, results / "m.json", fm)
    (run / "best" / "standard.json.moved").rename(run / "best" / "standard.json")
    (run / "last" / "hard.json").write_text("{}", newline="\n")
    with pytest.raises(seal.ManifestError, match="hard_enabled is false"):
        seal.build_evaluation_seal(results, ROWS, FREEZE, results / "m.json", fm)
    (run / "last" / "hard.json").unlink()
    (run / "last.pt").write_bytes((run / "last.pt").read_bytes() + b"\0")
    with pytest.raises(seal.ManifestError, match="changed since the pre-test manifest"):
        seal.build_evaluation_seal(results, ROWS, FREEZE, results / "m.json", fm)


def test_runs_record_the_code_commit_c_and_the_freeze_commit_f_separately(fresh):
    """config.json and the evaluation meta carry C (frozen code_commit); run_complete.json keeps C and the run-time HEAD (F)."""
    results, script = fresh
    final(results, script, unseal=True)
    for r in ROWS:
        run = results / "runs" / r["run_name"]
        done = json.loads((run / "run_complete.json").read_text())
        assert done["code_commit"] == "c" * 40 and done["freeze_commit"] == done["code_version"]["git_sha"] != done["code_commit"]
        assert json.loads((run / "config.json").read_text())["code_commit"] == "c" * 40
        assert json.loads((run / "last" / "standard.json").read_text())["meta"]["code_commit"] == "c" * 40


def test_frozen_mode_requires_the_frozen_code_commit_and_one_freeze_commit(fresh):
    results, script = fresh
    problems, _ = seal.run_problems(results, ROWS, {**FREEZE, "code_commit": "d" * 40}, allow_unfrozen=False, tiny_overrides=TINY)
    assert any("not produced from the frozen code commit" in p for p in problems)
    run = results / "runs" / ROWS[0]["run_name"]
    d = json.loads((run / "run_complete.json").read_text())
    d["freeze_commit"] = "e" * 40
    (run / "run_complete.json").write_text(json.dumps(d), newline="\n")
    problems, _ = seal.run_problems(results, ROWS, FREEZE, allow_unfrozen=True, tiny_overrides=TINY)
    assert any("different code versions" in p for p in problems)


# ------------------------------------------------------------------ the CURRENT summary / log are re-checked before unsealing (P1-2)
def _drop_summary(run):
    (run / "summary.json").unlink()


def _budget_drift(run):
    d = json.loads((run / "summary.json").read_text())
    d["total_env_steps"] = 120000
    (run / "summary.json").write_text(json.dumps(d), newline="\n")


def _duplicate_validation(run):
    d = json.loads((run / "summary.json").read_text())
    d["validation_steps"].append(d["validation_steps"][-1])
    (run / "summary.json").write_text(json.dumps(d), newline="\n")


def _best_step_changed(run):
    d = json.loads((run / "summary.json").read_text())
    other = [s for s in d["validation_steps"] if s != d["checkpoints"]["best"]["step"]][0]
    d["checkpoints"]["best"]["step"] = other
    (run / "summary.json").write_text(json.dumps(d), newline="\n")


def _log_duplicated(run):
    lines = (run / "train_log.jsonl").read_text().splitlines()
    ev = [x for x in lines if '"eval"' in x][-1]
    (run / "train_log.jsonl").write_text("\n".join(lines + [ev]) + "\n", newline="\n")


CASES = [(_drop_summary, "summary.json is missing"), (_budget_drift, "budget"), (_duplicate_validation, "validation_steps"),
         (_best_step_changed, "differs from the summary recorded"), (_log_duplicated, "validation rows")]


@pytest.mark.parametrize("damage,expect", CASES, ids=[c[0].__name__ for c in CASES])
def test_make_manifest_rejects_a_damaged_current_summary_or_log(fresh, damage, expect):
    results, script = fresh
    damage(results / "runs" / ROWS[0]["run_name"])
    with pytest.raises(seal.ManifestError, match=expect):
        build(results, script)


@pytest.mark.parametrize("damage,expect", CASES, ids=[c[0].__name__ for c in CASES])
def test_verify_manifest_rejects_material_damaged_after_the_manifest_was_written(fresh, damage, expect):
    results, script = fresh
    m = results / "m.json"
    seal.write_manifest(m, build(results, script))
    damage(results / "runs" / ROWS[0]["run_name"])
    with pytest.raises(seal.ManifestError, match=expect):
        verify(results, script, m)
    with pytest.raises(runner.Refused, match=expect):  # and the final evaluation refuses before anything is read
        runner.final_eval(m, results, script, rows=ROWS, freeze=FREEZE, allow_unfrozen=True, tiny=TINY, unseal=True)
    assert not (results / "unseal_log.jsonl").exists()


def test_final_evaluation_takes_the_best_step_from_the_current_summary_file(fresh):
    results, script = fresh
    name = ROWS[0]["run_name"]
    run = results / "runs" / name
    shutil.copy(run / "last.pt", run / "best.pt")
    d = json.loads((run / "run_complete.json").read_text())
    d["best_file_sha256"], d["best_state_sha256"] = d["last_file_sha256"], d["last_state_sha256"]
    (run / "run_complete.json").write_text(json.dumps(d), newline="\n")
    s = json.loads((run / "summary.json").read_text())
    s["checkpoints"]["best"]["step"] = 48
    (run / "summary.json").write_text(json.dumps(s), newline="\n")  # the file, not the cached copy, is authoritative
    runner.final_eval_run(results, name, seal.UnsealToken(seal._ISSUE_KEY, "t"), FREEZE)
    assert json.loads((run / "best" / "standard.json").read_text())["meta"]["checkpoint_step"] == 48


def test_documentation_does_not_claim_an_unbypassable_seal():
    """The seal is protocol-based: the default formal entry keeps the seeds closed, the low-level API / public constants / source edits do not.
    Texts must not say that only final-eval can read the sealed seeds."""
    root = Path(__file__).resolve().parents[2]
    banned = ("The ONLY code path that reads the sealed", "只能经 `scripts/prereg.py final-eval`")
    for rel in ("docs/RESEARCH_LOG.md", "docs/PLAN.md", "docs/prereg/README.md", "python/README.md", "python/scripts/prereg.py", "python/pacman_rl/seal.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert not any(b in text for b in banned), rel
    log = (root / "docs/RESEARCH_LOG.md").read_text(encoding="utf-8")
    assert "基于协议" in log and "不可绕过的保证" in log
    assert "protocol, not a security boundary" in (root / "docs/prereg/README.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ the window record is invisible to the integrity machinery
@pytest.fixture(scope="module")
def study_diag(tmp_path_factory, declared_hard_flag):
    results = tmp_path_factory.mktemp("study_diag")
    assert set(runner.run_matrix(ROWS, FREEZE, results, 1, TINY, diagnostics=True).values()) == {"done"}
    script = results / "analysis.py"
    script.write_text("# placeholder analysis script\n", newline="\n")
    return results, script


def test_runs_with_the_window_record_pass_every_integrity_check_unchanged(study_diag, tmp_path):
    results, script = study_diag
    for r in ROWS:
        assert (results / "runs" / r["run_name"] / "window_diagnostics.json").is_file()
    problems, facts = seal.run_problems(results, ROWS, FREEZE, allow_unfrozen=True, tiny_overrides=TINY)
    assert problems == []  # no stray-file rejection, no configuration mismatch, no current-material problem
    dst = tmp_path / "copy"
    shutil.copytree(results, dst)
    m = dst / "m.json"
    seal.write_manifest(m, build(dst, dst / "analysis.py"))
    token = verify(dst, dst / "analysis.py", m)  # verify_manifest issues the token
    assert token is not None
    index = runner.final_eval(m, dst, dst / "analysis.py", rows=ROWS, freeze=FREEZE, allow_unfrozen=True, tiny=TINY, unseal=True)
    assert set(index) == {r["run_name"] for r in ROWS}
    # the final evaluation neither reads nor rewrites the record
    for r in ROWS:
        assert (dst / "runs" / r["run_name"] / "window_diagnostics.json").read_bytes() == (results / "runs" / r["run_name"] / "window_diagnostics.json").read_bytes()


def test_adding_or_removing_the_record_after_the_fact_does_not_change_the_manifest_facts(fresh):
    results, script = fresh
    before = build(results, script)["runs"]
    for r in ROWS:
        (results / "runs" / r["run_name"] / "window_diagnostics.json").write_text("{}", newline="\n")
        (results / "runs" / r["run_name"] / "window_diagnostics.partial.json").write_text("{}", newline="\n")
    assert build(results, script)["runs"] == before
    assert seal.run_problems(results, ROWS, FREEZE, allow_unfrozen=True, tiny_overrides=TINY)[0] == []
