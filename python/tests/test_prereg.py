"""Preregistered study tooling: matrix <-> code correspondence, the formal runner's guarantees (fixed order, no test
evaluation, no resume, failed attempts archived, nothing taken from environment variables) and the smoke driver."""
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from pacman_rl import cli
from pacman_rl import prereg as PR
from pacman_rl import provenance as P
from pacman_rl.dqn import TrainConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402

ROWS = PR.load_matrix()
FREEZE = PR.load_freeze()
TINY = dict(total_env_steps=96, learn_start=32, eval_every=48, buffer=600, batch=8, device="cpu", val_set="smoke_eval")


# ------------------------------------------------------------------ matrix <-> code
def test_matrix_file_is_the_one_that_was_registered():
    assert P.file_sha256(PR.MATRIX_FILE) == PR.MATRIX_SHA256 == FREEZE["matrix_sha256"]
    assert PR.check_matrix_file() == []
    assert len(ROWS) == 30 and [r["order"] for r in ROWS] == list(range(1, 31))


def test_every_row_maps_to_a_complete_explicit_training_configuration():
    seen = set()
    for r in ROWS:
        cfg = PR.train_config(r, FREEZE)
        d = asdict(cfg)
        for k in ("arch", "n_step", "seed", "total_env_steps", "obs", "width", "double", "dueling", "lr", "gamma", "n_envs",
                  "steps_per_update", "batch", "buffer", "learn_start", "eval_every", "threads", "device"):
            assert d[k] == r[k], (r["run_name"], k)
        assert d["val_set"] == "prereg_val" and d["device"] == "cuda"
        # the settings the CSV does not carry are frozen explicitly AND equal the code's defaults (no silent drift)
        for k in PR.FROZEN_HPARAMS:
            assert d[k] == FREEZE[k] == getattr(TrainConfig(), k), k
        assert d["eps_frac"] * d["total_env_steps"] == 120000  # exploration anneals over the first 120000 transitions
        # round trip through the real command line: every field passed explicitly, nothing left to defaults
        ns = cli.build_parser().parse_args(["train", *PR.train_args(cfg, r["run_name"]), "--no-resume"])
        assert cli.train_config_from_args(ns) == cfg and ns.name == r["run_name"] and ns.no_resume
        seen.add(r["run_name"])
    assert len(seen) == 30


def test_fixed_order_comes_from_the_file_and_is_not_claimed_to_come_from_a_seed():
    assert "271828" not in json.dumps(FREEZE) and "not generated" in FREEZE["run_order"]
    blocks = [ROWS[6 * b: 6 * b + 6] for b in range(5)]
    assert [{r["seed"] for r in blk} for blk in blocks] == [{s} for s in PR.SEEDS]
    assert all(len({(r["arch"], r["n_step"]) for r in blk}) == 6 for blk in blocks)


@pytest.mark.parametrize("mutate,expect", [
    (lambda r: r[0].update(lr=0.001), "lr=0.001"),
    (lambda r: r[3].update(run_name="prereg_cnn2_n3_s100"), "run_name"),
    (lambda r: r[5].update(n_step=1, run_name="prereg_res8_n1_s100"), "six distinct"),
    (lambda r: r[7].update(seed=100, run_name="prereg_res4_n1_s100"), "must be the six distinct"),
    (lambda r: r.pop(), "order column"),
    (lambda r: r[1].update(device="cpu"), "device="),
    (lambda r: r[2].update(total_env_steps=120000), "total_env_steps"),
])
def test_matrix_validation_rejects_damage(mutate, expect):
    rows = [dict(r) for r in ROWS]
    mutate(rows)
    assert any(expect in p for p in PR.validate_matrix(rows)), PR.validate_matrix(rows)


def test_matrix_hash_mismatch_is_reported(tmp_path):
    f = tmp_path / "m.csv"
    shutil.copy(PR.MATRIX_FILE, f)
    assert PR.check_matrix_file(f) == []
    f.write_bytes(f.read_bytes() + b"\n")
    assert any("SHA-256" in p for p in PR.check_matrix_file(f))


# ------------------------------------------------------------------ preflight refusals
def test_formal_run_refuses_a_draft_configuration():
    with pytest.raises(runner.Refused, match="not 'frozen'"):
        runner.preflight(FREEZE, None, allow_unfrozen=False)


def test_environment_overrides_are_refused(monkeypatch):
    for var in runner.FORBIDDEN_ENV:
        monkeypatch.setenv(var, "1")
        with pytest.raises(runner.Refused, match=var):
            runner.preflight(FREEZE, None, allow_unfrozen=True)
        monkeypatch.delenv(var)


def test_third_worker_needs_an_explicit_frozen_setting():
    with pytest.raises(runner.Refused, match="3 workers"):
        runner.preflight(FREEZE, 3, allow_unfrozen=True)
    assert runner.preflight(FREEZE, 2, allow_unfrozen=True) == 2


def test_freeze_problems_lists_every_open_field():
    probs = runner.freeze_problems(FREEZE)
    for k in runner.TO_FILL:
        assert any(k in p for p in probs)
    for k in runner.TOP_LEVEL_TO_FILL:
        assert any(p.startswith(f"{k} is not filled") for p in probs)
    frozen = json.loads(json.dumps(FREEZE))
    frozen["status"] = "frozen"
    frozen.update(machine_id="m", worker_count=2, code_commit="c" * 40, hard_enabled=False)
    frozen["to_fill_at_freeze"].update({k: "x" for k in runner.TO_FILL}, power_and_sleep_settings_confirmed=True)
    assert runner.freeze_problems(frozen) == []
    frozen["val_seeds"] = list(range(20000, 20050))  # the v0.2 range: no longer what the code uses
    assert any("val_seeds differs" in p for p in runner.freeze_problems(frozen))


# ------------------------------------------------------------------ the runner
@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    results = tmp_path_factory.mktemp("prereg")
    rows = [r for r in ROWS if r["arch"] == "cnn2" and r["seed"] == 100]  # cnn2 n=1 and n=3, seed 100 (matrix order 4 and 5)
    out = runner.run_matrix(rows, FREEZE, results, 1, TINY)
    return results, rows, out


def test_runs_complete_from_scratch_without_any_test_evaluation(two_runs):
    results, rows, out = two_runs
    assert out == {"prereg_cnn2_n1_s100": "done", "prereg_cnn2_n3_s100": "done"}
    for r in rows:
        d = results / "runs" / r["run_name"]
        done = json.loads((d / "run_complete.json").read_text())
        assert done["attempt"] == 1 and done["matrix_order"] == r["order"] and done["config"]["val_set"] == "smoke_eval"
        assert not any(p.name.startswith(("test", "final")) or p.name.startswith("resume") for p in d.iterdir())
        assert (d / "last.pt").exists() and (d / "best.pt").exists() and (d / "environment.json").exists()
        text = (d / "run_complete.json").read_text()
        assert str(results) not in text and str(Path.home()) not in text
    a, b = (json.loads((results / "runs" / r["run_name"] / "run_complete.json").read_text()) for r in rows)
    assert a["init_online_hash"] == b["init_online_hash"] and a["last_state_sha256"] != b["last_state_sha256"]


def test_jobs_are_dispatched_in_matrix_order(tmp_path, monkeypatch):
    started = []
    monkeypatch.setattr(runner, "execute", lambda name, cfg, results, order=None, **kw: (started.append((order, name)), "done")[1])
    rows = ROWS[:8]
    runner.run_matrix(rows, FREEZE, tmp_path, 1, TINY)
    assert [o for o, _ in started] == [r["order"] for r in rows] and [n for _, n in started] == [r["run_name"] for r in rows]


def test_complete_runs_are_skipped_not_rerun(two_runs):
    results, rows, _ = two_runs
    before = (results / "runs" / rows[0]["run_name"] / "run_complete.json").read_bytes()
    assert set(runner.run_matrix(rows, FREEZE, results, 1, TINY).values()) == {"skipped"}
    assert (results / "runs" / rows[0]["run_name"] / "run_complete.json").read_bytes() == before


def test_unfinished_run_is_archived_and_restarted_from_scratch_never_resumed(tmp_path):
    row = next(r for r in ROWS if r["arch"] == "cnn2" and r["n_step"] == 3 and r["seed"] == 100)
    cfg = PR.train_config(row, FREEZE, **TINY)
    run_dir = tmp_path / "runs" / row["run_name"]
    # a genuine interrupted run: stopped after its first checkpoint, so resume.pt + resume_replay.npz exist
    from pacman_rl.dqn import train

    train(cfg, run_dir, log=lambda *_: None, _stop_after=48)
    assert (run_dir / "resume.pt").exists()
    assert runner.execute(row["run_name"], cfg, tmp_path, row["order"]) == "done"
    done = json.loads((run_dir / "run_complete.json").read_text())
    assert done["attempt"] == 2
    arch = tmp_path / "attempts" / row["run_name"] / "attempt_1"
    assert (arch / "resume.pt").exists() and (arch / "train_log.jsonl").exists()
    log = [json.loads(x) for x in (tmp_path / "attempts.jsonl").read_text().splitlines()]
    assert len(log) == 1 and log[0]["run"] == row["run_name"] and log[0]["attempt"] == 1 and "resume.pt" in log[0]["files"]
    new = [json.loads(x) for x in (run_dir / "train_log.jsonl").read_text().splitlines()]
    assert not any(r["type"] == "resume" for r in new) and new[0]["type"] == "init"  # a fresh run, not a continuation
    assert not (run_dir / "resume.pt").exists()


def test_finalize_rejects_test_outputs_and_config_drift(two_runs, tmp_path):
    results, rows, _ = two_runs
    r = rows[0]
    d = tmp_path / "copy"
    shutil.copytree(results / "runs" / r["run_name"], d)
    (d / "run_complete.json").unlink()
    shutil.copy(d / "train_config.json", d / "config.json")  # back to what train() wrote, as before finalize
    cfg = PR.train_config(r, FREEZE, **TINY)
    (d / "test_standard.json").write_text("{}", newline="\n")
    assert any("forbidden" in p for p in runner.finalize(d, r["run_name"], cfg, 1, r["order"]))
    (d / "test_standard.json").unlink()
    assert runner.finalize(d, r["run_name"], cfg, 1, r["order"]) == []
    (d / "run_complete.json").unlink()
    shutil.copy(d / "train_config.json", d / "config.json")
    drift = PR.train_config(r, FREEZE, **{**TINY, "lr": 0.001})
    assert any("config.json differs" in p for p in runner.finalize(d, r["run_name"], drift, 1, r["order"]))
    (d / "last.pt").unlink()
    assert any("missing last.pt" in p for p in runner.finalize(d, r["run_name"], cfg, 1, r["order"]))


# ------------------------------------------------------------------ smoke driver
def test_smoke_driver_reports_throughput_memory_hash_pairs_and_resume(tmp_path):
    rep = runner.smoke("quick", "cpu", tmp_path, steps=1200, pairs=[("cnn2", 1, 900), ("cnn2", 3, 900)])
    assert {v["outcome"] for v in rep["runs"].values()} == {"done"}
    assert rep["initial_hash_pairs_equal"] == {"cnn2_s900": True}
    for v in rep["runs"].values():
        assert v["env_steps"] == 1200 and v["updates"] > 0 and v["env_steps_per_second"] > 0 and v["peak_working_set_mb"] > 0 and v["peak_memory_error"] is None and (sys.platform != "win32" or v["peak_commit_mb"] > 0)
        assert v["cpu_eval_10_episodes"]["last"]["n_records"] == 10 and v["cpu_eval_10_episodes"]["best"]["n_records"] == 10
    assert rep["interrupt_resume_check"]["ok"] is True
    text = (tmp_path / "smoke_report_quick.json").read_text()
    assert str(tmp_path) not in text and set(rep["environment"]) == set(P.ENV_KEYS)
    cfg = json.loads((tmp_path / "runs" / "smoke_quick_cnn2_n1_s900" / "config.json").read_text())
    assert cfg["seed"] == 900 and cfg["val_set"] == "smoke_eval"


# ------------------------------------------------------------------ v0.3.2 interfaces
def test_frozen_config_matches_the_code_and_the_spec_field_names():
    assert PR.check_frozen_config(FREEZE) == []
    for k in ("eps_start", "eps_end", "eps_frac", "tau", "grad_clip", "val_seeds", "test_seeds", "smoke_eval_seeds", "smoke_run_seeds",
              "eval_episodes", "final_eval_device", "final_eval_threads", "hard_enabled", "code_commit", "machine_id", "train_device",
              "validation_device", "worker_count", "max_episode_steps", "train_scenario", "hard_chase_p"):
        assert k in FREEZE, k
    assert FREEZE["val_seeds"] == list(range(21000, 21050)) and FREEZE["test_seeds"] == list(range(30000, 30300))
    assert FREEZE["smoke_eval_seeds"] == list(range(40000, 40010)) and FREEZE["smoke_run_seeds"] == [900, 901]
    assert PR.MATRIX_FILE.name == "matrix.csv" and PR.FREEZE_FILE.name == "frozen_config_v0.3.2.json"
    bad = {**FREEZE, "eps_end": 0.01}
    assert any("eps_end" in p for p in PR.check_frozen_config(bad))


def test_completed_run_has_the_contract_files(two_runs):
    results, rows, _ = two_runs
    for r in rows:
        d = results / "runs" / r["run_name"]
        cfg = json.loads((d / "config.json").read_text())
        for col in PR.COLUMNS:
            assert col in cfg, col  # every CSV column (order, run_name, ..., primary_checkpoint) is in the merged effective config
        for k in ("eps_start", "eps_end", "eps_frac", "tau", "grad_clip", "code_commit", "frozen_config_sha256", "val_seeds", "test_seeds",
                  "eval_episodes", "final_eval_device", "final_eval_threads", "max_episode_steps", "train_scenario"):
            assert k in cfg, k
        assert cfg["frozen_config_sha256"] == P.file_sha256(PR.FREEZE_FILE) and len(cfg["code_commit"]) == 40
        assert (d / "train_config.json").exists()  # what train() itself wrote
        s = json.loads((d / "summary.json").read_text())
        assert s["run_name"] == r["run_name"] and s["total_env_steps"] == 96 and s["validation_steps"] == [48, 96]
        assert isinstance(s["replay"]["size"], int) and isinstance(s["actual_updates"], int) and s["validation_episodes_each"] == 10
        assert len(s["initial_state_dict_sha256"]) == 64
        assert s["checkpoints"]["last"] == {"step": 96, "weights_sha256": json.loads((d / "run_complete.json").read_text())["last_state_sha256"]}
        assert s["checkpoints"]["best"]["step"] in s["validation_steps"]


# ------------------------------------------------------------------ smoke profiles must not share runs or reports
def _small_load_profile(monkeypatch):
    """The real load profile fills a 100000-sample buffer; a miniature with the same pairs keeps the test quick."""
    monkeypatch.setitem(runner.PROFILES, "load", {**runner.PROFILES["load"], "steps": 1200, "learn_start": 500, "buffer": 4000, "eval_every": 1000, "workers": 1})


def test_quick_then_load_in_the_same_results_dir_runs_both_and_keeps_both_reports(tmp_path, monkeypatch):
    _small_load_profile(monkeypatch)
    pair = [("cnn2", 1, 900)]  # the same (architecture, n_step, seed) in both profiles: the case that used to collide
    quick = runner.smoke("quick", "cpu", tmp_path, steps=1200, pairs=pair)
    quick_report = tmp_path / "smoke_report_quick.json"
    before = quick_report.read_bytes()
    load = runner.smoke("load", "cpu", tmp_path, pairs=pair)
    # the load run was really trained, not skipped as "already complete" ...
    assert {v["outcome"] for v in load["runs"].values()} == {"done"} and {v["outcome"] for v in quick["runs"].values()} == {"done"}
    # ... in its own run directory ...
    assert (tmp_path / "runs" / "smoke_quick_cnn2_n1_s900" / "run_complete.json").exists()
    assert (tmp_path / "runs" / "smoke_load_cnn2_n1_s900" / "run_complete.json").exists()
    # ... with the profile's own configuration, and the quick report is untouched
    assert json.loads((tmp_path / "runs" / "smoke_load_cnn2_n1_s900" / "config.json").read_text())["learn_start"] == 500
    assert json.loads((tmp_path / "runs" / "smoke_quick_cnn2_n1_s900" / "config.json").read_text())["buffer"] == 4000
    assert quick_report.read_bytes() == before
    assert json.loads(before)["profile"] == "quick" and json.loads((tmp_path / "smoke_report_load.json").read_text())["profile"] == "load"
    assert not (tmp_path / "smoke_report.json").exists()  # the ambiguous shared name is gone
    assert (tmp_path / "interrupt_check_quick").exists() and (tmp_path / "interrupt_check_load").exists()


# ------------------------------------------------------------------ smoke: a complete run is reused only for the same configuration and code
def _reuse_cfg(steps=1200, device="cpu"):
    row = next(r for r in PR.load_matrix() if r["arch"] == "cnn2" and r["n_step"] == 1 and r["seed"] == 100)
    prof = runner.PROFILES["quick"]
    return PR.train_config(row, FREEZE, seed=900, device=device, val_set=FREEZE["smoke_val_set"], total_env_steps=steps,
                           learn_start=prof["learn_start"], buffer=prof["buffer"], eval_every=prof["eval_every"])


@pytest.fixture(scope="module")
def smoke_once(tmp_path_factory):
    d = tmp_path_factory.mktemp("smoke_reuse")
    rep = runner.smoke("quick", "cpu", d, steps=1200, pairs=[("cnn2", 1, 900)], resume_check=False)
    return d, rep


NAME = "smoke_quick_cnn2_n1_s900"


def test_same_profile_different_steps_is_refused_and_leaves_the_complete_run_untouched(smoke_once):
    d, first = smoke_once
    run = d / "runs" / NAME
    snap = {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}
    rep = runner.smoke("quick", "cpu", d, steps=1000, pairs=[("cnn2", 1, 900)], resume_check=False)
    e = rep["runs"][NAME]
    assert e["outcome"] == "refused" and rep["ok"] is False and any("total_env_steps" in x for x in e["refusal"])
    assert "env_steps" not in e and "reused" not in e  # no stale numbers are presented as this invocation's
    assert {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()} == snap
    assert first["runs"][NAME]["outcome"] == "done"


def test_a_different_device_or_arch_or_buffer_is_a_different_configuration(smoke_once):
    d, _ = smoke_once
    run = d / "runs" / NAME
    assert runner.reuse_problems(run, _reuse_cfg()) == []
    assert any("device" in p for p in runner.reuse_problems(run, _reuse_cfg(device="cuda")))
    import dataclasses

    for field, value in (("buffer", 5000), ("learn_start", 600), ("lr", 0.001), ("seed", 901)):
        assert any(field in p for p in runner.reuse_problems(run, dataclasses.replace(_reuse_cfg(), **{field: value}))), field


def test_a_changed_python_tree_refuses_reuse(smoke_once, monkeypatch):
    d, _ = smoke_once
    real = P.code_version
    monkeypatch.setattr(P, "code_version", lambda *a, **k: {**real(*a, **k), "python_tree_sha256": "f" * 64})
    problems = runner.reuse_problems(d / "runs" / NAME, _reuse_cfg())
    assert any("python/ tree differs" in p for p in problems)


def test_identical_rerun_reports_reuse_origin_original_minutes_and_this_invocations_cost(smoke_once):
    d, first = smoke_once
    rep = runner.smoke("quick", "cpu", d, steps=1200, pairs=[("cnn2", 1, 900)], resume_check=False)
    e, e0 = rep["runs"][NAME], first["runs"][NAME]
    assert e["outcome"] == "skipped" and e["reused"] is True and e0["reused"] is False and rep["ok"] is True and rep["workers"] == 1
    assert e["original_training_minutes"] == e0["original_training_minutes"] == e0["minutes"] > 0
    assert e["invocation_seconds"] < e0["invocation_seconds"] and rep["wall_seconds"] < e0["minutes"] * 60 + 60  # this call did not train
    assert e["origin"] == e0["origin"] and e["origin"]["device"] == "cpu" and len(e["origin"]["python_tree_sha256"]) == 64 and e["origin"]["attempt"] == 1
    assert e["throughput_source"] == "original training run (reused)" and e0["throughput_source"] == "this invocation"
    assert str(d) not in json.dumps(rep)


def test_smoke_cli_exits_nonzero_when_the_interrupt_resume_check_fails(monkeypatch, tmp_path):
    base = {"profile": "quick", "runs": {"r": {"outcome": "done"}}, "interrupt_resume_check": {"ok": True}, "ok": True}
    for ok_check, runs_ok, code in ((True, True, 0), (False, True, 1), (True, False, 1)):
        rep = {**base, "runs": {"r": {"outcome": "done" if runs_ok else "failed"}}, "interrupt_resume_check": {"ok": ok_check}}
        rep["ok"] = ok_check and runs_ok
        monkeypatch.setattr(runner, "smoke", lambda *a, _r=rep, **k: _r)
        assert runner.main(["smoke", "--profile", "quick", "--device", "cpu", "--results-dir", str(tmp_path)]) == code


def test_smoke_report_ok_is_false_when_the_resume_check_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "interrupt_resume_check", lambda path: {"ok": False, "note": "x"})
    rep = runner.smoke("quick", "cpu", tmp_path, steps=1200, pairs=[("cnn2", 1, 900)])
    assert rep["ok"] is False and rep["runs"][NAME]["outcome"] == "done"


# ------------------------------------------------------------------ window diagnostics through the runner (switch on the command line, not in the configuration)
def test_smoke_with_window_diagnostics_writes_the_file_and_keeps_the_switch_part_of_reuse(tmp_path):
    rep = runner.smoke("quick", "cpu", tmp_path, steps=1200, pairs=[("cnn2", 3, 900)], resume_check=False, diagnostics=True)
    run = tmp_path / "runs" / "smoke_quick_cnn2_n3_s900"
    d = json.loads((run / "window_diagnostics.json").read_text())
    assert rep["window_diagnostics"] is True and rep["ok"] is True and d["integrity"]["complete"] is True and d["totals"]["collected_transitions"] == 1200
    cfg_json = json.loads((run / "config.json").read_text())
    assert "window_diagnostics" not in cfg_json and "window_diagnostics" not in json.loads((run / "train_config.json").read_text())
    # the same run requested with the switch off is another experiment (files and overhead differ): refused, not silently reused
    off = runner.smoke("quick", "cpu", tmp_path, steps=1200, pairs=[("cnn2", 3, 900)], resume_check=False, diagnostics=False)
    assert off["runs"]["smoke_quick_cnn2_n3_s900"]["outcome"] == "refused" and any("window diagnostics" in x for x in off["runs"]["smoke_quick_cnn2_n3_s900"]["refusal"])
    again = runner.smoke("quick", "cpu", tmp_path, steps=1200, pairs=[("cnn2", 3, 900)], resume_check=False, diagnostics=True)
    assert again["runs"]["smoke_quick_cnn2_n3_s900"]["outcome"] == "skipped"
