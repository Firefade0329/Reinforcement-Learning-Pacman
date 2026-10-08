import re
from pathlib import Path

import numpy as np
import pytest

from pacman_rl import maps
from pacman_rl.env import HARD, OBS_SHAPE, STANDARD, TOTAL_GOLD, EnvConfig, PacmanEnv

REPO = Path(__file__).resolve().parents[2]


def parse_java_map(path: Path):
    src = path.read_text().split("int width")[0]
    rows = re.findall(r"\{((?:\s*\d+,?)+)\}", src)
    grid = [[int(x) for x in r.replace("\n", " ").split(",") if x.strip()] for r in rows]
    return [r for r in grid if len(r) == 32]


@pytest.mark.parametrize("pkg", ["ReinforcementLearning", "DijkstraPathFinding", "HumanPlayGame"])
def test_map_matches_java_source(pkg):
    java = parse_java_map(REPO / pkg / "Game.java")
    assert len(java) == maps.H and all(len(r) == maps.W for r in java)
    for y in range(maps.H):
        for x in range(maps.W):
            assert (java[y][x] == 255) == bool(maps.WALL[y, x]), (pkg, x, y)
            if java[y][x] != 255:
                assert java[y][x] == 1  # every open cell holds gold in the Java map


def test_map_topology():
    assert maps.N == 378 and TOTAL_GOLD == 377
    assert (maps.DIST >= 0).all() and (maps.DIST == maps.DIST.T).all()
    assert (np.diag(maps.DIST) == 0).all()
    # border is all wall, no open cell without an exit
    assert maps.WALL[0].all() and maps.WALL[-1].all() and maps.WALL[:, 0].all() and maps.WALL[:, -1].all()
    assert ((maps.NEIGHBOURS >= 0).sum(axis=1) >= 1).all()
    # adjacent cells are at distance 1
    for c in range(maps.N):
        for n in maps.NEIGHBOURS[c]:
            if n >= 0:
                assert maps.DIST[c, n] == 1


def test_reset_state():
    env = PacmanEnv()
    for seed in range(50):
        obs, _ = env.reset(seed)
        assert obs.shape == OBS_SHAPE and obs.dtype == np.float32
        assert env.gold.sum() == TOTAL_GOLD and not env.gold[env.agent]
        ax, ay = maps.CELL_X[env.agent], maps.CELL_Y[env.agent]
        assert (maps.CELL_X[env.ghosts] != ax).all() and (maps.CELL_Y[env.ghosts] != ay).all()
        assert obs[2].sum() == 1 and obs[0].sum() == maps.WALL.sum() and obs[1].sum() == TOTAL_GOLD


def test_determinism():
    def rollout(seed):
        env = PacmanEnv()
        env.reset(seed)
        arng = np.random.default_rng(123)
        out = []
        for _ in range(200):
            _, r, term, trunc, info = env.step(int(arng.integers(5)))
            out.append((r, env.agent, tuple(env.ghosts), info["score"]))
            if term or trunc:
                break
        return out

    assert rollout(7) == rollout(7)
    assert rollout(7) != rollout(8)


def test_wall_and_move_semantics():
    env = PacmanEnv(EnvConfig(num_ghosts=0))
    env.reset(3)
    for _ in range(300):
        before = env.agent
        a = int(env.rng.integers(5))
        env.step(a)
        if a == 0:
            assert env.agent == before
        else:
            n = maps.NEIGHBOURS[before, a - 1]
            assert env.agent == (before if n < 0 else n)
        if env.done:
            break


def test_gold_eaten_once_and_reward():
    env = PacmanEnv(EnvConfig(num_ghosts=0, r_step=0.0))
    env.reset(5)
    total = 0.0
    for _ in range(400):
        _, d_cell, d = env.nearest_gold()
        _, r, term, trunc, info = env.step(d + 1)
        total += r
        if term or trunc:
            break
    assert info["score"] == TOTAL_GOLD - env.gold.sum()  # score counts removed pellets
    assert total == pytest.approx(info["score"] + (10.0 if info.get("won") else 0.0))


def test_win_by_eating_everything_without_ghosts():
    env = PacmanEnv(EnvConfig(num_ghosts=0, max_steps=5000))
    env.reset(11)
    term = False
    while not term:
        _, _, term, trunc, info = env.step(env.nearest_gold()[2] + 1)
        assert not trunc
    assert info["won"] and not info["died"] and info["score"] == TOTAL_GOLD
    assert env.done


def test_truncation():
    env = PacmanEnv(EnvConfig(num_ghosts=0, max_steps=10))
    env.reset(0)
    for i in range(10):
        _, _, term, trunc, _ = env.step(0)
    assert trunc and not term and env.done


def test_ghosts_stay_on_open_cells_and_do_not_reverse():
    env = PacmanEnv(HARD)
    env.reset(21)
    prev_dir = env.ghost_dir.copy()
    for _ in range(300):
        before = env.ghosts.copy()
        _, _, term, trunc, _ = env.step(0)
        if term or trunc:
            break
        assert (env.ghosts >= 0).all()
        for i in range(env.cfg.num_ghosts):
            assert maps.DIST[before[i], env.ghosts[i]] == 1
            if prev_dir[i] >= 0:  # no dead ends on this map => never reverses
                assert env.ghost_dir[i] != (prev_dir[i] + 2) % 4
        prev_dir = env.ghost_dir.copy()


def test_collision_kills_and_no_pass_through():
    # Put a ghost directly in front of Pacman in a corridor and walk into it.
    env = PacmanEnv(EnvConfig(num_ghosts=1, chase_prob=0.0))
    env.reset(1)
    a = env.agent
    d = next(d for d in range(4) if maps.NEIGHBOURS[a, d] >= 0)
    env.ghosts[0] = maps.NEIGHBOURS[a, d]
    _, r, term, _, info = env.step(d + 1)
    assert term and info["died"] and r < -5


def test_chase_rate():
    """Greedy move frequency must equal chase_prob + (1 - chase_prob) * E[1/#choices]."""
    def run(p, n=3000):
        env = PacmanEnv(EnvConfig(chase_prob=p, num_ghosts=1), seed=4)
        env.reset(4)
        hits = decisions = 0
        expected = 0.0
        for _ in range(n):
            if env.done:
                env.reset()
            g, cur = int(env.ghosts[0]), int(env.ghost_dir[0])
            ax, ay = maps.CELL_X[env.agent], maps.CELL_Y[env.agent]
            env.step(0)  # Pacman stays, so the ghost aims at (ax, ay)
            cand = [d for d in range(4) if maps.NEIGHBOURS[g, d] >= 0 and (cur < 0 or d != (cur + 2) % 4)]
            if len(cand) < 2:
                continue
            dist = [(int(maps.CELL_X[maps.NEIGHBOURS[g, d]]) - ax) ** 2
                    + (int(maps.CELL_Y[maps.NEIGHBOURS[g, d]]) - ay) ** 2 for d in cand]
            best = cand[int(np.argmin(dist))]  # first minimum: same tie rule as Java's strict '<'
            decisions += 1
            expected += p + (1 - p) / len(cand)
            hits += int(env.ghost_dir[0] == best)
        return hits / decisions, expected / decisions

    for p in (0.0, 0.3, 0.7, 1.0):
        observed, expected = run(p)
        assert observed == pytest.approx(expected, abs=0.04), (p, observed, expected)
