"""PacmanEnv: faithful Python port of the Java game (ReinforcementLearning/Game.java
and GamePanel.java), exposing a Gymnasium-style reset/step API.

Actions: 0 = stay, 1 = right, 2 = down, 3 = left, 4 = up (action a>0 moves along
``DIRS[a-1]``).  Moving into a wall leaves Pacman in place, as in Java.

Turn order (matches GamePanel.actionPerformed): Pacman moves -> eats gold ->
collision check -> ghosts move -> collision check -> win check.  A collision is
two entities on the same cell; because it is checked after *each* move, Pacman
and a ghost can never pass through each other.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import maps
from .maps import DIRS, H, N, NEIGHBOURS, W

NUM_ACTIONS = 5
OBS_CHANNELS = 5  # wall, gold, pacman, ghosts, ghosts one step ago
OBS_SHAPE = (OBS_CHANNELS, H, W)
TOTAL_GOLD = N - 1  # every open cell holds gold except Pacman's spawn cell


@dataclass(frozen=True)
class EnvConfig:
    num_ghosts: int = 3
    chase_prob: float = 0.3  # Java: nextInt(10) > 2 picks a random move => 70 % random, 30 % chase
    max_steps: int = 1000
    # training reward (evaluation never uses it)
    r_gold: float = 1.0
    r_death: float = -10.0
    r_win: float = 10.0
    r_step: float = -0.01


STANDARD = EnvConfig()
HARD = EnvConfig(chase_prob=0.7)  # out-of-distribution scenario, never trained on


class PacmanEnv:
    def __init__(self, config: EnvConfig = STANDARD, seed: int | None = None):
        self.cfg = config
        self.rng = np.random.default_rng(seed)
        self.agent = 0
        self.ghosts = np.zeros(config.num_ghosts, dtype=np.int32)
        self.ghost_prev = self.ghosts.copy()
        self.ghost_dir = np.full(config.num_ghosts, -1, dtype=np.int32)  # -1 = not moved yet
        self.gold = np.ones(N, dtype=bool)
        self.steps = 0
        self.score = 0
        self.done = True

    # ------------------------------------------------------------------ API
    def reset(self, seed: int | None = None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        rng = self.rng
        self.gold[:] = True
        self.agent = int(rng.integers(N))
        self.gold[self.agent] = False
        # Java quirk kept on purpose: ghosts never spawn in Pacman's row or column.
        ax, ay = maps.CELL_X[self.agent], maps.CELL_Y[self.agent]
        allowed = np.flatnonzero((maps.CELL_X != ax) & (maps.CELL_Y != ay))
        self.ghosts = rng.choice(allowed, size=self.cfg.num_ghosts).astype(np.int32)
        self.ghost_prev = self.ghosts.copy()
        self.ghost_dir[:] = -1
        self.steps = 0
        self.score = 0
        self.done = False
        return self.observation(), self._info()

    def step(self, action: int):
        assert not self.done, "call reset() first"
        cfg = self.cfg
        self.steps += 1
        reward = cfg.r_step

        if action > 0:
            nxt = NEIGHBOURS[self.agent, action - 1]
            if nxt >= 0:
                self.agent = int(nxt)
        if self.gold[self.agent]:
            self.gold[self.agent] = False
            self.score += 1
            reward += cfg.r_gold

        died = bool((self.ghosts == self.agent).any())
        won = False
        if not died:
            won = self.score == TOTAL_GOLD
            if not won:
                self.ghost_prev = self.ghosts.copy()
                self._move_ghosts()
                died = bool((self.ghosts == self.agent).any())

        terminated = died or won
        truncated = (not terminated) and self.steps >= cfg.max_steps
        if died:
            reward += cfg.r_death
        elif won:
            reward += cfg.r_win
        self.done = terminated or truncated
        info = self._info()
        info["died"], info["won"] = died, won
        return self.observation(), reward, terminated, truncated, info

    # ------------------------------------------------------------ internals
    def _info(self):
        return {"score": self.score, "steps": self.steps}

    def _move_ghosts(self):
        rng = self.rng
        ax, ay = maps.CELL_X[self.agent], maps.CELL_Y[self.agent]
        for i in range(self.cfg.num_ghosts):
            g = int(self.ghosts[i])
            cur = int(self.ghost_dir[i])
            cand = [d for d in range(4) if NEIGHBOURS[g, d] >= 0 and (cur < 0 or d != (cur + 2) % 4)]
            if not cand:  # dead end: only the reverse move is left (never happens on this map)
                cand = [d for d in range(4) if NEIGHBOURS[g, d] >= 0]
            if rng.random() < self.cfg.chase_prob:
                best, best_d = cand[0], None
                for d in cand:  # strict '<' => first direction wins ties, like Java
                    n = NEIGHBOURS[g, d]
                    dist = (int(maps.CELL_X[n]) - ax) ** 2 + (int(maps.CELL_Y[n]) - ay) ** 2
                    if best_d is None or dist < best_d:
                        best, best_d = d, dist
                d = best
            else:
                d = cand[int(rng.integers(len(cand)))]
            self.ghost_dir[i] = d
            self.ghosts[i] = NEIGHBOURS[g, d]

    # ----------------------------------------------------------- observation
    def observation(self) -> np.ndarray:
        obs = np.zeros(OBS_SHAPE, dtype=np.float32)
        obs[0] = maps.WALL
        g = np.flatnonzero(self.gold)
        obs[1, maps.CELL_Y[g], maps.CELL_X[g]] = 1.0
        obs[2, maps.CELL_Y[self.agent], maps.CELL_X[self.agent]] = 1.0
        obs[3, maps.CELL_Y[self.ghosts], maps.CELL_X[self.ghosts]] = 1.0
        obs[4, maps.CELL_Y[self.ghost_prev], maps.CELL_X[self.ghost_prev]] = 1.0
        return obs

    # ------------------------------------------------------------ utilities
    def nearest_gold(self):
        """(distance, cell, first_direction) of the nearest gold by BFS; ties resolved
        like the Java BFS (direction priority right, down, left, up)."""
        gold_cells = np.flatnonzero(self.gold)
        if gold_cells.size == 0:
            return 0, self.agent, 0
        best_d, best_dir = None, 0
        for d in range(4):
            n = NEIGHBOURS[self.agent, d]
            if n < 0:
                continue
            dist = 1 + int(maps.DIST[n, gold_cells].min())
            if best_d is None or dist < best_d:
                best_d, best_dir = dist, d
        return best_d, int(gold_cells[maps.DIST[self.agent, gold_cells].argmin()]), best_dir
