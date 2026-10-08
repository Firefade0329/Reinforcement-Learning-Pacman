"""Hand-engineered observations for the tabular agent (64 states) and the MLP (29-d vector).

All distances are BFS steps on the fixed map (``maps.DIST``), ghosts are not obstacles - the
same information the Java agent computed with its Dijkstra/BFS helper.
"""
from __future__ import annotations

import numpy as np

from . import maps
from .maps import DIST, NEIGHBOURS

GHOST_RANGE = 4  # BFS steps; Java: path.size() <= 5  <=>  steps <= 4
FEATURE_DIM = 29
NUM_TABULAR_STATES = 64


def _first_dir_to(agent: int, target: int) -> int:
    best, best_d = 0, None
    for d in range(4):
        n = NEIGHBOURS[agent, d]
        if n >= 0:
            dist = 1 + int(DIST[n, target])
            if best_d is None or dist < best_d:
                best, best_d = d, dist
    return best


def ghost_mask(env, rng_steps: int = GHOST_RANGE) -> int:
    """4-bit mask: bit d is set if some ghost within ``rng_steps`` has its shortest path from
    Pacman starting in direction d (right, down, left, up)."""
    mask = 0
    for g in env.ghosts:
        if DIST[env.agent, g] <= rng_steps:
            mask |= 1 << _first_dir_to(env.agent, int(g))
    return mask


def tabular_state(env) -> int:
    """gold direction (4) x ghost mask (16) = 64 states, the design sketched in QLearning.java."""
    return env.nearest_gold()[2] * 16 + ghost_mask(env)


def feature_vector(env) -> np.ndarray:
    f = np.zeros(FEATURE_DIM, dtype=np.float32)
    gold_cells = np.flatnonzero(env.gold)
    a = env.agent
    dist_now, _, gdir = env.nearest_gold()
    f[gdir] = 1.0
    f[4] = dist_now / 50.0
    gd = DIST[env.ghosts]  # (num_ghosts, N)
    nearest_ghost = gd.min(axis=0)
    i = 5
    for d in range(4):
        n = NEIGHBOURS[a, d]
        if n < 0:
            f[i:i + 3] = (0.0, 1.0, 0.0)
        else:
            f[i] = 1.0
            f[i + 1] = (1 + int(DIST[n, gold_cells].min())) / 50.0 if gold_cells.size else 0.0
            f[i + 2] = min(int(nearest_ghost[n]), 25) / 25.0
        i += 3
    f[17] = min(int(nearest_ghost[a]), 25) / 25.0
    d_now = np.sort(DIST[a, env.ghosts].astype(np.int32))
    order = np.argsort(DIST[a, env.ghosts])
    for k in range(3):
        if k < len(order):
            g, gp = env.ghosts[order[k]], env.ghost_prev[order[k]]
            f[18 + k] = min(int(d_now[k]), 25) / 25.0
            f[21 + k] = float(np.sign(int(DIST[a, gp]) - int(DIST[a, g])))  # +1 = approaching
        else:
            f[18 + k] = 1.0
    mask = ghost_mask(env)
    for d in range(4):
        f[24 + d] = float(mask >> d & 1)
    f[28] = gold_cells.size / maps.N
    return f
