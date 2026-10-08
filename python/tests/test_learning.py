import numpy as np
import pytest
import torch

from pacman_rl import maps
from pacman_rl.env import FIELD_SHAPE, OBS_SHAPE, STANDARD, PacmanEnv
from pacman_rl.features import FEATURE_DIM, NUM_TABULAR_STATES, feature_vector, tabular_state
from pacman_rl.models import ARCHS, build_model, receptive_field
from pacman_rl.replay import NStepReplay


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


def test_receptive_field_covers_map_only_for_res8():
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
