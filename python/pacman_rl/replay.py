"""Uniform replay buffer fed through per-environment n-step accumulators.

Observations may be stored as uint8 (``quant_scale``): every channel value must then be an integer
divided by a per-channel constant (true for the 0/1 planes and the BFS distance fields), so decoding
reproduces the float32 observation to within 1 ulp while using 4x less memory (a conv run with a
100k buffer needs ~1.1 GB instead of ~4.3 GB; without this 4 parallel runs exhaust a 15 GB machine).
"""
from __future__ import annotations

from collections import deque

import numpy as np
import torch


class NStepReplay:
    def __init__(self, capacity: int, obs_shape, obs_dtype, n_envs: int, n_step: int, gamma: float,
                 quant_scale: np.ndarray | None = None):
        self.cap, self.n, self.gamma = capacity, n_step, gamma
        self.scale = None if quant_scale is None else np.asarray(quant_scale, dtype=np.float32).reshape(-1, 1, 1)
        store = np.uint8 if self.scale is not None else obs_dtype
        self.obs = np.zeros((capacity, *obs_shape), dtype=store)
        self.next_obs = np.zeros((capacity, *obs_shape), dtype=store)
        self.act = np.zeros(capacity, dtype=np.int64)
        self.ret = np.zeros(capacity, dtype=np.float32)    # discounted n-step return
        self.disc = np.zeros(capacity, dtype=np.float32)   # gamma^k, or 0 after a true terminal
        self.pos = 0
        self.size = 0
        self.pending = [deque() for _ in range(n_envs)]  # (obs, action, reward)

    def _enc(self, obs):
        return obs if self.scale is None else np.rint(obs * self.scale).astype(np.uint8)

    def _emit(self, obs, action, ret, next_obs, disc):
        i = self.pos
        obs, next_obs = self._enc(obs), self._enc(next_obs)
        self.obs[i], self.act[i], self.ret[i], self.next_obs[i], self.disc[i] = obs, action, ret, next_obs, disc
        self.pos = (i + 1) % self.cap
        self.size = min(self.size + 1, self.cap)

    def add(self, env_i: int, obs, action: int, reward: float, next_obs, terminated: bool, truncated: bool):
        q = self.pending[env_i]
        q.append((obs, action, reward))
        if terminated or truncated:
            # flush every pending transition with the (shorter) horizon that is left
            items = list(q)
            for start in range(len(items)):
                ret, k = 0.0, len(items) - start
                for j in range(k):
                    ret += (self.gamma ** j) * items[start + j][2]
                disc = 0.0 if terminated else self.gamma ** k  # truncation still bootstraps
                self._emit(items[start][0], items[start][1], ret, next_obs, disc)
            q.clear()
        elif len(q) == self.n:
            ret = sum((self.gamma ** j) * q[j][2] for j in range(self.n))
            self._emit(q[0][0], q[0][1], ret, next_obs, self.gamma ** self.n)
            q.popleft()

    def sample(self, batch: int, rng: np.random.Generator):
        idx = rng.integers(0, self.size, size=batch)
        if self.scale is None:
            to_t = lambda a: torch.from_numpy(np.ascontiguousarray(a)).float()  # noqa: E731
        else:
            sc = torch.from_numpy(self.scale)
            to_t = lambda a: torch.from_numpy(np.ascontiguousarray(a)).float() / sc  # noqa: E731
        return (to_t(self.obs[idx]), torch.from_numpy(self.act[idx]), torch.from_numpy(self.ret[idx]),
                to_t(self.next_obs[idx]), torch.from_numpy(self.disc[idx]))
