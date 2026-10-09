import json
from math import sqrt
from pathlib import Path

import numpy as np
import pytest

from pacman_rl import maps
from pacman_rl.baselines import LegacyAgent, SafeHeuristicAgent, make_agent
from pacman_rl.env import STANDARD, EnvConfig, PacmanEnv
from pacman_rl.evaluate import EQUIV_SEEDS, TEST_SEEDS, VAL_SEEDS, evaluate_named, train_seed

REPO = Path(__file__).resolve().parents[2]


def test_seed_splits_disjoint():
    train = {train_seed(r, k) for r in range(5) for k in range(20000)}
    assert not train & set(VAL_SEEDS) and not train & set(TEST_SEEDS)
    assert not set(VAL_SEEDS) & set(TEST_SEEDS)
    # fidelity checks of non-learning agents use their own seeds: never the validation/test/training ones
    assert not set(EQUIV_SEEDS) & (set(VAL_SEEDS) | set(TEST_SEEDS) | train)


def test_java_qtable_is_equivalent_to_bfs_direction():
    """The Q-table the Java code loads (line 20) maps state d -> action d+1, i.e. 'follow the BFS
    direction', which is what LegacyAgent does when no ghost is near."""
    line = (REPO / "data" / "QTable.txt").read_text().splitlines()[20]
    q = np.array([float(x) for x in line.strip(",").split(",")]).reshape(4, 5)
    assert list(q.argmax(axis=1)) == [1, 2, 3, 4]


def _place(env, agent_xy, ghost_xy):
    env.reset(0)
    env.agent = int(maps.CELL_ID[agent_xy[1], agent_xy[0]])
    env.ghosts = np.array([maps.CELL_ID[y, x] for x, y in ghost_xy], dtype=np.int32)


def test_legacy_flees_opposite_to_near_ghost():
    env = PacmanEnv(EnvConfig(num_ghosts=1))
    # open corridor row y=13: x=1..9 are all open, ghost 2 cells to the right -> flee left (action 3)
    _place(env, (4, 13), [(6, 13)])
    assert LegacyAgent().act(env) == 3
    # ghost 2 cells to the left -> flee right (action 1)
    _place(env, (6, 13), [(4, 13)])
    assert LegacyAgent().act(env) == 1


def test_legacy_ignores_far_ghost():
    env = PacmanEnv(EnvConfig(num_ghosts=1))
    _place(env, (1, 1), [(30, 22)])
    expected = env.nearest_gold()[2] + 1
    assert LegacyAgent().act(env) == expected


def test_legacy_last_near_ghost_quirk():
    """Java overwrites closestGhost for every near ghost, so the LAST one decides, not the nearest."""
    env = PacmanEnv(EnvConfig(num_ghosts=2))
    _place(env, (4, 13), [(5, 13), (4, 15)])  # ghost0 adjacent on the right, ghost1 below (further)
    a = LegacyAgent().act(env)
    # last near ghost (index 1) lies 'down' in env codes -> flee up if possible (action 4) else right/left
    assert a in (4, 1, 3)
    _place(env, (4, 13), [(4, 15), (5, 13)])  # order swapped: now the right-hand ghost is last
    assert LegacyAgent().act(env) == 3  # flee left


def test_agents_are_deterministic_and_valid():
    for name in ["random", "greedy-bfs", "legacy", "safe-heuristic"]:
        a = evaluate_named(name, STANDARD, VAL_SEEDS[:5], workers=1)
        b = evaluate_named(name, STANDARD, VAL_SEEDS[:5], workers=1)
        assert a == b, name


def test_safe_heuristic_never_walks_into_adjacent_ghost_when_alternative_exists():
    env = PacmanEnv(EnvConfig(num_ghosts=1))
    agent = SafeHeuristicAgent()
    # ghost adjacent to the right in a corridor: moving right (action 1) would be fatal
    _place(env, (4, 13), [(5, 13)])
    assert agent.act(env) != 1


def test_legacy_replica_matches_original_java_run():
    """results/reference/java_legacy.json holds 150 games of the ORIGINAL Java agent (see
    scripts/run_java_legacy.sh).  The Python replica must be statistically indistinguishable."""
    ref = json.loads((REPO / "results" / "reference" / "java_legacy.json").read_text())["records"]
    py = evaluate_named("legacy", STANDARD, EQUIV_SEEDS, workers=4)  # not the test seeds (PLAN section 6)
    for key in ("score", "steps", "died"):
        a = np.array([r[key] for r in ref], float)
        b = np.array([r[key] for r in py], float)
        z = (a.mean() - b.mean()) / sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        assert abs(z) < 3.0, (key, a.mean(), b.mean(), z)
    a = np.sort([r["score"] for r in ref])
    b = np.sort([r["score"] for r in py])
    grid = np.arange(0, 380, 5)
    ks = np.abs((a[:, None] <= grid).mean(0) - (b[:, None] <= grid).mean(0)).max()
    assert ks < 1.36 * sqrt((len(a) + len(b)) / (len(a) * len(b))), ks
