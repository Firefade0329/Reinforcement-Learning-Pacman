from pathlib import Path

import numpy as np
import pytest
import torch

from pacman_rl import maps
from pacman_rl.env import FIELD_SHAPE, OBS_SHAPE, STANDARD, PacmanEnv
from pacman_rl.features import FEATURE_DIM, NUM_TABULAR_STATES, feature_vector, tabular_state
from pacman_rl.models import ARCHS, build_model, receptive_field
from pacman_rl.replay import NStepReplay

REPO = Path(__file__).resolve().parents[2]


def test_nstep_return_and_terminal_handling():
    g = 0.5
    r = NStepReplay(100, (1,), np.float32, n_envs=1, n_step=3, gamma=g)
    o = lambda i: np.array([i], dtype=np.float32)  # noqa: E731
    # rewards 1,2,4 then episode terminates on 4th step with reward 8
    r.add(0, o(0), 1, 1.0, o(1), False, False)
    r.add(0, o(1), 2, 2.0, o(2), False, False)
    assert r.size == 0
    r.add(0, o(2), 3, 4.0, o(3), False, False)  # first full 3-step window emitted
    assert r.size == 1
    assert r.ret[0] == pytest.approx(1 + g * 2 + g * g * 4) and r.disc[0] == pytest.approx(g ** 3)
    assert r.obs[0][0] == 0 and r.next_obs[0][0] == 3
    r.add(0, o(3), 4, 8.0, o(4), True, False)  # terminal: flush the 3 pending transitions
    assert r.size == 4
    # transition starting at obs 1: 2 + g*4 + g^2*8, no bootstrap
    assert r.ret[1] == pytest.approx(2 + g * 4 + g * g * 8) and r.disc[1] == 0.0
    assert r.ret[2] == pytest.approx(4 + g * 8) and r.ret[3] == pytest.approx(8.0)
    assert all(r.next_obs[i][0] == 4 for i in (1, 2, 3))
    assert not r.pending[0]


def test_truncation_bootstraps():
    r = NStepReplay(10, (1,), np.float32, 1, 2, 0.9)
    o = lambda i: np.array([i], dtype=np.float32)  # noqa: E731
    r.add(0, o(0), 0, 1.0, o(1), False, True)  # truncated after a single step
    assert r.size == 1 and r.disc[0] == pytest.approx(0.9)


def test_replay_ring_buffer_wraps():
    r = NStepReplay(5, (1,), np.float32, 1, 1, 0.9)
    for i in range(12):
        r.add(0, np.array([i], dtype=np.float32), 0, 0.0, np.array([i + 1], dtype=np.float32), False, False)
    assert r.size == 5 and sorted(r.obs[:, 0].tolist()) == [7, 8, 9, 10, 11]


@pytest.mark.parametrize("arch", ARCHS)
def test_model_shapes_and_dueling(arch):
    for dueling in (True, False):
        m = build_model(arch, 16, dueling)
        x = torch.zeros(3, *(FIELD_SHAPE if arch != "mlp" else (FEATURE_DIM,)))
        assert m(x).shape == (3, 5)


def test_resnet_blocks_start_as_identity():
    m = build_model("res8", 16)
    x = torch.rand(2, *FIELD_SHAPE)
    stem = m.trunk[1](m.trunk[0](x))
    h = stem
    for blk in list(m.trunk)[2:10]:
        h = blk(h)
    assert torch.allclose(h, stem, atol=1e-6)  # zero-init second conv => identity blocks


def test_receptive_field_side_lengths():
    assert receptive_field("cnn2") == 5 and receptive_field("res2") == 11
    assert receptive_field("res4") == 19 and receptive_field("res8") == 35
    assert receptive_field("res8") >= maps.W > receptive_field("res4")


def test_features_are_finite_and_bounded():
    env = PacmanEnv(STANDARD)
    rng = np.random.default_rng(0)
    for seed in range(20):
        env.reset(seed)
        for _ in range(60):
            f = feature_vector(env)
            assert f.shape == (FEATURE_DIM,) and np.isfinite(f).all() and f.min() >= -1 and f.max() <= 1.0
            assert 0 <= tabular_state(env) < NUM_TABULAR_STATES
            _, _, term, trunc, _ = env.step(int(rng.integers(5)))
            if term or trunc:
                f = feature_vector(env)  # must also work on terminal / won states
                break


def test_features_on_won_state():
    env = PacmanEnv(STANDARD)
    env.reset(0)
    env.gold[:] = False
    assert np.isfinite(feature_vector(env)).all()


def test_dqn_smoke_training_runs_and_checkpoint_roundtrips(tmp_path):
    from pacman_rl.dqn import TrainConfig, evaluate_model, load_checkpoint, train
    from pacman_rl.evaluate import VAL_SEEDS

    cfg = TrainConfig(arch="cnn2", total_env_steps=480, learn_start=64, eval_every=480, n_envs=4,
                      buffer=2000, batch=8, seed=0)
    train(cfg, tmp_path, log=lambda *_: None)
    model, cfg2, _ = load_checkpoint(tmp_path / "last.pt")
    a = evaluate_model(model, cfg2, STANDARD, VAL_SEEDS[:4])
    b = evaluate_model(model, cfg2, STANDARD, VAL_SEEDS[:4])
    assert a == b  # same checkpoint, same seeds -> identical results
    assert (tmp_path / "train_log.jsonl").exists() and (tmp_path / "summary.json").exists()


def test_distance_field_observation():
    env = PacmanEnv(STANDARD)
    env.reset(3)
    obs = env.observation_fields()
    assert obs.shape == FIELD_SHAPE and obs.dtype == np.float32 and np.isfinite(obs).all()
    assert (obs[:5] == env.observation()).all()
    a = env.agent
    ax, ay = maps.CELL_X[a], maps.CELL_Y[a]
    gold = np.flatnonzero(env.gold)
    c = int(gold[0])
    assert obs[5, maps.CELL_Y[c], maps.CELL_X[c]] == 0.0  # zero on a gold cell
    assert obs[5, ay, ax] == pytest.approx(min(int(maps.DIST[a, gold].min()), 25) / 25.0)
    for g in env.ghosts:  # ghost field is zero exactly at the ghosts
        assert obs[6, maps.CELL_Y[g], maps.CELL_X[g]] == 0.0
    assert (obs[5][maps.WALL] == 1).all() and (obs[6][maps.WALL] == 1).all()
    assert obs[5:].min() >= 0 and obs[5:].max() <= 1
    env.gold[:] = False
    assert np.isfinite(env.observation_fields()).all()  # won state


def test_raw_grid_mode_still_supported(tmp_path):
    from pacman_rl.dqn import TrainConfig, train

    train(TrainConfig(arch="cnn2", obs="grid", total_env_steps=160, learn_start=32, eval_every=160, n_envs=4,
                      buffer=500, batch=8), tmp_path, log=lambda *_: None)
    assert (tmp_path / "best.pt").exists()


def test_readout_is_translation_equivariant_and_uses_agent_cell():
    """Q-values depend on the neighbourhood of Pacman only (within the receptive field)."""
    torch.manual_seed(0)
    m = build_model("cnn2", 8)
    x = torch.rand(1, *FIELD_SHAPE)
    x[:, 2] = 0
    x[0, 2, 10, 10] = 1.0
    q0 = m(x)
    far = x.clone()
    far[0, :2, 2:4, 2:4] += 1.0          # change cells far outside the 5x5 receptive field
    far[0, 5:, 2:4, 2:4] += 1.0
    assert torch.allclose(m(far), q0, atol=1e-6)
    near = x.clone()
    near[0, 5, 10, 11] += 0.5            # change a neighbour of Pacman
    assert not torch.allclose(m(near), q0, atol=1e-6)
    # moving Pacman *and* its surroundings together leaves Q unchanged (equivariance, interior of the map)
    shifted = torch.roll(x, shifts=(0, 3), dims=(2, 3))
    assert torch.allclose(m(shifted), q0, atol=1e-5)


def test_replay_gif_is_written(tmp_path):
    from pacman_rl.baselines import RandomAgent
    from pacman_rl.render import record

    agent = RandomAgent(0)
    out = tmp_path / "r.gif"
    score, steps, died, won = record(agent.act, STANDARD, 10000, out, "random")
    assert out.exists() and out.stat().st_size > 1000 and steps > 0


def test_resolve_device_and_cpu_default():
    from pacman_rl.dqn import TrainConfig, resolve_device

    assert TrainConfig().device == "cpu"
    assert resolve_device("cpu").type == "cpu"
    assert resolve_device("auto").type in ("cpu", "cuda")
    if not torch.cuda.is_available():
        with pytest.raises(RuntimeError, match="CUDA"):
            resolve_device("cuda")


def test_old_checkpoint_without_device_field_still_loads(tmp_path):
    """Checkpoints written before the 'device' field existed must keep loading."""
    from pacman_rl.dqn import TrainConfig, load_checkpoint, save_checkpoint
    from dataclasses import asdict

    cfg = TrainConfig(arch="cnn2")
    model = build_model("cnn2", cfg.width, cfg.dueling, 7)
    d = asdict(cfg)
    d.pop("device")
    torch.save({"state_dict": model.state_dict(), "cfg": d}, tmp_path / "old.pt")
    m2, cfg2, _ = load_checkpoint(tmp_path / "old.pt")
    assert cfg2.device == "cpu" and next(m2.parameters()).device.type == "cpu"


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs a CUDA GPU")
def test_gpu_training_smoke_and_cpu_eval_roundtrip(tmp_path):
    from pacman_rl.dqn import TrainConfig, evaluate_model, load_checkpoint, train
    from pacman_rl.evaluate import VAL_SEEDS

    cfg = TrainConfig(arch="res2", device="cuda", total_env_steps=480, learn_start=64, eval_every=480,
                      n_envs=4, buffer=2000, batch=8)
    train(cfg, tmp_path, log=lambda *_: None)
    for dev in ("cpu", "cuda"):  # a GPU-trained checkpoint evaluates on either device
        model, cfg2, _ = load_checkpoint(tmp_path / "last.pt", dev)
        a = evaluate_model(model, cfg2, STANDARD, VAL_SEEDS[:3])
        b = evaluate_model(model, cfg2, STANDARD, VAL_SEEDS[:3])
        assert a == b


def test_bench_command_runs_on_cpu(capsys):
    import sys
    from pacman_rl import cli

    sys.argv = ["cli", "bench", "--device", "cpu", "--archs", "mlp", "cnn2", "--iters", "2"]
    cli.main()
    out = capsys.readouterr().out
    assert "ms/update" in out and "mlp" in out and "cnn2" in out


def test_uint8_replay_roundtrip_matches_float_observations():
    from pacman_rl.dqn import quant_scale

    env = PacmanEnv(STANDARD)
    env.reset(5)
    q = NStepReplay(50, FIELD_SHAPE, np.float32, 1, 1, 0.9, quant_scale("res4", "fields"))
    ref = NStepReplay(50, FIELD_SHAPE, np.float32, 1, 1, 0.9)
    rng = np.random.default_rng(0)
    for _ in range(40):
        o = env.observation_fields()
        _, r, term, trunc, _ = env.step(int(rng.integers(5)))
        n = env.observation_fields()
        q.add(0, o, 1, r, n, term, trunc)
        ref.add(0, o, 1, r, n, term, trunc)
        if term or trunc:
            env.reset(6)
    assert q.obs.dtype == np.uint8 and q.obs.nbytes * 4 == ref.obs.nbytes
    a = q.sample(16, np.random.default_rng(1))
    b = ref.sample(16, np.random.default_rng(1))
    assert float((a[0] - b[0]).abs().max()) < 1e-6 and float((a[3] - b[3]).abs().max()) < 1e-6
    assert torch.equal(a[1], b[1]) and torch.equal(a[2], b[2])


def test_training_resumes_after_interruption(tmp_path):
    """Kill-and-restart: an interrupted run continues from its last eval boundary and completes."""
    import json

    from pacman_rl.dqn import TrainConfig, load_checkpoint, train

    cfg = TrainConfig(arch="cnn2", total_env_steps=640, learn_start=64, eval_every=160, n_envs=4, buffer=2000,
                      batch=8, seed=1)
    first = train(cfg, tmp_path, log=lambda *_: None, _stop_after=320)
    assert first["interrupted"] and (tmp_path / "resume.pt").exists() and not (tmp_path / "last.pt").exists()
    msgs = []
    out = train(cfg, tmp_path, log=msgs.append)
    assert any("[resume]" in m and "env_steps=320" in m for m in msgs)
    assert (tmp_path / "last.pt").exists() and not (tmp_path / "resume.pt").exists()
    rows = [json.loads(x) for x in (tmp_path / "train_log.jsonl").read_text().splitlines()]
    evals = [r["env_steps"] for r in rows if r["type"] == "eval"]
    assert evals == sorted(evals) and evals[-1] == 640 and 320 in evals  # one continuous log
    _, cfg2, ck = load_checkpoint(tmp_path / "last.pt")
    assert ck["env_steps"] == 640


def test_resume_ignores_state_from_a_different_config(tmp_path):
    from pacman_rl.dqn import TrainConfig, train

    base = dict(arch="cnn2", total_env_steps=320, learn_start=64, eval_every=160, n_envs=4, buffer=2000, batch=8)
    train(TrainConfig(seed=1, **base), tmp_path, log=lambda *_: None, _stop_after=160)
    msgs = []
    train(TrainConfig(seed=2, **base), tmp_path, log=msgs.append)
    assert any("does not match" in m for m in msgs)


def test_stale_lock_is_taken_over(tmp_path, monkeypatch):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("run_experiments", REPO / "python" / "scripts" / "run_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    run = tmp_path / "r"
    run.mkdir()
    assert mod.take_lock(run) and not mod.take_lock(run)  # held by this (alive) process
    (run / ".lock" / "pid").write_text("999999999")      # owner that does not exist
    assert mod.take_lock(run)                              # stale -> taken over


def test_pid_alive_is_portable():
    import importlib.util
    import os

    spec = importlib.util.spec_from_file_location("run_experiments2", REPO / "python" / "scripts" / "run_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.pid_alive(os.getpid())
    assert not mod.pid_alive(0) and not mod.pid_alive(-5)
    assert not mod.pid_alive(999999999)  # no such process


def _load_script(name, monkeypatch):
    """Load a script as a module that reads the COMMITTED results/ even when the test run itself happens
    under acceptance.sh --quick (which exports PACMAN_RESULTS_DIR=<throw-away dir>)."""
    import importlib.util
    import sys

    monkeypatch.delenv("PACMAN_RESULTS_DIR", raising=False)
    monkeypatch.delitem(sys.modules, "acceptance_lib", raising=False)  # it reads the env var at import time
    monkeypatch.syspath_prepend(str(REPO / "python" / "scripts"))
    spec = importlib.util.spec_from_file_location(name, REPO / "python" / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_matrix_validation_passes_on_committed_results_and_catches_damage(tmp_path, monkeypatch):
    lib = _load_script("acceptance_lib", monkeypatch)
    assert lib.validate_matrix() == []  # the committed cloud matrix is complete and consistent
    # a run whose config disagrees with its name, and a truncated evaluation, must be reported
    import json
    import shutil

    shutil.copytree(REPO / "results" / "runs" / "mlp_s0", tmp_path / "runs" / "mlp_s0")
    monkeypatch.setattr(lib, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(lib, "RESULTS", tmp_path)
    cfg = json.loads((tmp_path / "runs" / "mlp_s0" / "config.json").read_text())
    cfg["n_step"] = 1
    (tmp_path / "runs" / "mlp_s0" / "config.json").write_text(json.dumps(cfg))
    p = json.loads((tmp_path / "runs" / "mlp_s0" / "test_standard.json").read_text())
    p["records"] = p["records"][:299]
    (tmp_path / "runs" / "mlp_s0" / "test_standard.json").write_text(json.dumps(p))
    problems = lib.validate_matrix()
    assert any("mlp_s0: config n_step=1" in x for x in problems)
    assert any("mlp_s0/standard: 299 episodes" in x for x in problems)


def test_m2_check_and_timing_strip(monkeypatch):
    chk = _load_script("check_acceptance", monkeypatch)
    status, detail = chk.check_m2()
    assert status == "PASS" and "identical" in detail, (status, detail)
    lib = _load_script("acceptance_lib", monkeypatch)
    assert lib.strip_timing("46 passed, 1 skipped in 20.31s") == "46 passed, 1 skipped"
    assert lib.strip_timing("45 passed, 1 skipped in 95.89s (0:01:35)") == "45 passed, 1 skipped"


def test_res8_readout_does_not_see_the_whole_map_everywhere():
    """Side 35 >= width 32 does NOT mean whole-map view: Q is read at Pacman's cell, so the radius (17) counts."""
    layers = 2 * 8 + 1  # = receptive-field radius in cells (each 3x3 conv adds 1)
    cx, cy = maps.CELL_X.astype(int), maps.CELL_Y.astype(int)
    dist = np.maximum(np.abs(cx[:, None] - cx[None, :]), np.abs(cy[:, None] - cy[None, :]))  # Chebyshev
    inside = dist <= layers
    assert not inside.all()
    a, b = int(maps.CELL_ID[1, 1]), int(maps.CELL_ID[1, 30])  # both open; 29 columns apart
    assert dist[a, b] == 29 > layers
    assert 0.75 < inside.mean() < 0.85               # ~80 % of (Pacman cell, other cell) pairs
    assert 0.10 < inside.all(axis=1).mean() < 0.20   # ~14 % of Pacman positions see every open cell
    assert (dist <= 2 * 4 + 1).mean() < 0.45         # res4: ~37 % of pairs


def test_tabular_truncation_bootstraps_from_the_real_next_state(monkeypatch):
    """A time-limit truncation is not terminal: the target must use the REAL next state's Q, not the old one."""
    import pacman_rl.tabular as T
    from pacman_rl.env import EnvConfig

    calls = {"n": 0}

    def fake_state(env):  # state 0 after reset, state 1 after the (truncated) step
        calls["n"] += 1
        return 0 if calls["n"] == 1 else 1

    monkeypatch.setattr(T, "tabular_state", fake_state)
    q0 = np.zeros((T.NUM_TABULAR_STATES, T.NUM_ACTIONS))
    q0[1, :] = 10.0
    cfg = EnvConfig(num_ghosts=0, max_steps=1, r_step=0.0, r_gold=0.0)
    q, _ = T.train_tabular(episodes=1, seed=0, cfg=cfg, alpha=1.0, gamma=0.9, q0=q0)
    assert q[0].max() == pytest.approx(9.0)  # 0 + 0.9 * max Q[1]; the old code gave 0.0 (it used Q[0])
    # a true terminal does not bootstrap
    q2 = q0.copy()
    T.q_update(q2, 0, 0, 1.0, 1, True, 1.0, 0.9)
    assert q2[0, 0] == pytest.approx(1.0)


def test_resume_truncates_the_interrupted_segment_and_marks_it(tmp_path):
    import json

    from pacman_rl.dqn import TrainConfig, train, truncate_log_to

    # unit: rows after the checkpoint are dropped, earlier ones (incl. exactly at it) are kept
    p = tmp_path / "unit.jsonl"
    rows = [{"type": "eval", "env_steps": 20000}, {"type": "train", "env_steps": 20000},
            {"type": "train", "env_steps": 24000}, {"type": "train", "env_steps": 28000}]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert truncate_log_to(p, 20000) == 2
    assert [json.loads(x)["env_steps"] for x in p.read_text().splitlines()] == [20000, 20000]
    assert truncate_log_to(tmp_path / "missing.jsonl", 5) == 0
    # integration: a stray row written after the last checkpoint must not survive the resume
    cfg = TrainConfig(arch="cnn2", total_env_steps=640, learn_start=64, eval_every=160, n_envs=4, buffer=2000,
                      batch=8, seed=2)
    run = tmp_path / "run"
    train(cfg, run, log=lambda *_: None, _stop_after=320)
    with open(run / "train_log.jsonl", "a") as f:
        f.write(json.dumps({"type": "train", "env_steps": 400, "score": 1.0}) + "\n")  # from the interrupted segment
    train(cfg, run, log=lambda *_: None)
    rows = [json.loads(x) for x in (run / "train_log.jsonl").read_text().splitlines()]
    assert not any(r["type"] == "train" and r["env_steps"] == 400 for r in rows)
    marks = [r for r in rows if r["type"] == "resume"]
    assert len(marks) == 1 and marks[0]["env_steps"] == 320 and marks[0]["dropped_rows"] == 1
    steps = [r["env_steps"] for r in rows if r["type"] in ("eval", "train")]
    assert steps == sorted(steps)  # the log no longer goes backwards


def test_log_paths_are_not_absolute(capsys, tmp_path):
    from pacman_rl import cli

    shown = cli.rel(cli.REPO_ROOT / "results" / "runs" / "x")
    assert shown == "results/runs/x" and not shown.startswith("/")
    assert cli.rel(tmp_path / "somewhere" / "run1") == "run1"  # outside the repo: just the name
