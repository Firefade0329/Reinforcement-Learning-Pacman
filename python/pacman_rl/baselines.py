"""Non-learning reference agents.  All expose ``act(env) -> action`` and use the
environment's privileged state (positions), exactly like the Java code did.

* RandomAgent       - lower bound.
* GreedyBFSAgent    - walks to the nearest gold, ignores ghosts.
* LegacyAgent       - exact replica of the Java RL agent's *behaviour*: BFS direction to the
                      nearest gold (the trained Q-table reduces to this, see tests) plus the
                      hard-coded flee rule, including its quirks.
* SafeHeuristicAgent - a careful hand-written planner used to judge whether learning really
                      beats "just writing good rules".
"""
from __future__ import annotations

from collections import deque

import numpy as np

from . import maps
from .maps import DIST, NEIGHBOURS

SEARCH_DISTANCE = 5  # Game.searchDistant in Java


class Agent:
    name = "agent"

    def reset(self) -> None:  # called at the start of every episode
        pass

    def act(self, env) -> int:
        raise NotImplementedError

    def act_batch(self, envs):
        return [self.act(e) for e in envs]


class RandomAgent(Agent):
    name = "random"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def act(self, env) -> int:
        return int(self.rng.integers(5))


class GreedyBFSAgent(Agent):
    name = "greedy-bfs"

    def act(self, env) -> int:
        return env.nearest_gold()[2] + 1


def first_step_towards(env, target: int) -> int:
    """Direction of the first step of a shortest path agent -> target; ties go to the earliest
    direction in (right, down, left, up) order, which is what the Java BFS produces."""
    best, best_d = 0, None
    for d in range(4):
        n = NEIGHBOURS[env.agent, d]
        if n < 0:
            continue
        dist = 1 + int(DIST[n, target])
        if best_d is None or dist < best_d:
            best, best_d = d, dist
    return best


class LegacyAgent(Agent):
    """Java ``GamePanel.actionPerformed`` for the trained (readQ) configuration.

    * ghost 'distance' is Java's ``path.size()`` = BFS steps + 1; a ghost counts as near when
      that is <= searchDistant (5), i.e. BFS steps <= 4.
    * Quirk: ``closestGhost`` is the direction of the *last* near ghost in ghost order, not the
      nearest one.
    * Quirk: the ghost direction codes differ from the gold ones (1 = up, 3 = down); the flee
      table below is written in Java's own convention and translated to env directions
      (0 right, 1 down, 2 left, 3 up).
    """

    name = "legacy"

    def act(self, env) -> int:
        near = None
        for g in env.ghosts:
            if int(DIST[env.agent, g]) + 1 <= SEARCH_DISTANCE:
                near = first_step_towards(env, int(g))  # env direction code, last near ghost wins
        if near is None:
            return env.nearest_gold()[2] + 1
        free = [NEIGHBOURS[env.agent, d] >= 0 for d in range(4)]  # Java notWall: right, down, left, up
        if near == 0:  # ghost to the right -> go left, else down, else up
            move = 2 if free[2] else (1 if free[1] else 3)
        elif near == 3:  # ghost above -> go down, else right, else left
            move = 1 if free[1] else (0 if free[0] else 2)
        elif near == 2:  # ghost to the left -> go right, else down, else up
            move = 0 if free[0] else (1 if free[1] else 3)
        else:  # near == 1, ghost below -> go up, else right, else left
            move = 3 if free[3] else (0 if free[0] else 2)
        return move + 1


class SafeHeuristicAgent(Agent):
    """Time-expanded BFS to the nearest gold along cells no ghost can reach before (or just
    when) Pacman does.  If no safe gold exists, step to the neighbour farthest from the ghosts."""

    name = "safe-heuristic"

    def __init__(self, margin: int = 0):
        self.margin = margin

    def act(self, env) -> int:
        gdist = DIST[env.ghosts].min(axis=0)  # fastest any ghost can reach each cell
        gold = env.gold
        start = env.agent
        # first[c] = first direction taken on the path to c
        first = {start: -1}
        q = deque([(start, 0)])
        m = self.margin
        while q:
            u, t = q.popleft()
            for d in range(4):
                v = int(NEIGHBOURS[u, d])
                if v < 0 or v in first or gdist[v] <= t + 1 + m:
                    continue
                first[v] = d if u == start else first[u]
                if gold[v]:
                    return first[v] + 1
                q.append((v, t + 1))
        # trapped: maximise distance to the nearest ghost
        best, best_score = 0, int(gdist[start])
        for d in range(4):
            v = int(NEIGHBOURS[start, d])
            if v >= 0 and int(gdist[v]) > best_score:
                best, best_score = d + 1, int(gdist[v])
        return best


def make_agent(name: str, seed: int = 0) -> Agent:
    table = {
        "random": lambda: RandomAgent(seed),
        "greedy-bfs": GreedyBFSAgent,
        "legacy": LegacyAgent,
        "safe-heuristic": SafeHeuristicAgent,
    }
    return table[name]()
