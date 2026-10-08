"""Uniform replay buffer fed through per-environment n-step accumulators."""
from __future__ import annotations

from collections import deque

import numpy as np
import torch


class NStepReplay:
    def __init__(self, capacity: int, obs_shape, obs_dtype, n_envs: int, n_step: int, gamma: float):
        self.cap, self.n, self.gamma = capacity, n_step, gamma
        self.obs = np.zeros((capacity, *obs_shape), dtype=obs_dtype)
        self.next_obs = np.zeros((capacity, *obs_shape), dtype=obs_dtype)
        self.act = np.zeros(capacity, dtype=np.int64)
        self.ret = np.zeros(capacity, dtype=np.float32)    # discounted n-step return
        self.disc = np.zeros(capacity, dtype=np.float32)   # gamma^k, or 0 after a true terminal
        self.pos = 0
        self.size = 0
        self.pending = [deque() for _ in range(n_envs)]  # (obs, action, reward)

    def _emit(self, obs, action, ret, next_obs, disc):
        i = self.pos
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
        to_t = lambda a: torch.from_numpy(np.ascontiguousarray(a)).float()  # noqa: E731
        return (to_t(self.obs[idx]), torch.from_numpy(self.act[idx]), torch.from_numpy(self.ret[idx]),
                to_t(self.next_obs[idx]), torch.from_numpy(self.disc[idx]))
