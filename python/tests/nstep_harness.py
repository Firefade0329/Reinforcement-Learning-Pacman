"""Drives the REAL pipeline (``dqn.collect_step`` -> ``NStepReplay`` -> ``replay.sample`` -> ``dqn.td_target``)
with scripted environments and table-lookup "networks", so the result can be compared with ``nstep_oracle``.
Implementations are parameters so that deliberately broken variants can be plugged in (mutation tests)."""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import torch

import nstep_oracle as oracle
import pacman_rl.dqn as dqn
from pacman_rl.replay import NStepReplay

K = 512  # one-hot state space of the toy problems
CASES = json.loads((Path(__file__).parent / "data" / "nstep_oracle_cases.json").read_text(encoding="utf-8"))


class TableQ(torch.nn.Module):
    """Q(s, .) = row s of a fixed table; the observation is a one-hot state (channel 0 when 4-D)."""

    def __init__(self, table):
        super().__init__()
        self.register_buffer("table", torch.as_tensor(table, dtype=torch.float32))

    def forward(self, x):
        onehot = x[:, 0].reshape(len(x), -1) if x.dim() == 4 else x
        return onehot @ self.table


def table_from(q: dict) -> np.ndarray:
    t = np.zeros((K, 5), np.float32)
    for s, row in q.items():
        t[int(s)] = row
    return t


class ScriptedEnv:
    """Replays a fixed list of episodes; ``reset`` starts the next one.  A step must be asked for the scripted action."""

    SENTINEL = K - 1

    def __init__(self, episodes):
        self.episodes, self.ep, self.t, self.state = episodes, -1, 0, self.SENTINEL

    def reset(self, seed=None):
        self.ep += 1
        self.t = 0
        eps = self.episodes
        self.state = eps[self.ep][0][0] if self.ep < len(eps) and eps[self.ep] else self.SENTINEL

    def step(self, action):
        s, a, r, s2, status = self.episodes[self.ep][self.t]
        assert s == self.state and action == a, "the harness fed a different state/action than scripted"
        self.t += 1
        self.state = s2
        return None, float(r), status == "terminated", status == "truncated", {"score": 0, "died": False}


def encoder(quant: bool):
    """quant=False: (K,) one-hot float; quant=True: (2,1,K) planes through the uint8 replay (second plane carries
    multiples of 1/4 so decoding is exercised)."""
    def observe(env):
        if not quant:
            v = np.zeros(K, np.float32)
            v[env.state] = 1.0
            return v
        v = np.zeros((2, 1, K), np.float32)
        v[0, 0, env.state] = 1.0
        v[1, 0, env.state] = (env.state % 4) / 4.0
        return v

    return observe


class SeqRng:
    """Makes ``replay.sample`` return every stored sample exactly once, in storage order."""

    def integers(self, lo, hi, size):
        return np.arange(size) % hi


def run_pipeline(envs, q_online, q_target, n, gamma, double=True, quant=False, *,
                 replay_cls=NStepReplay, td_target=None, collect_step=None):
    td_target = td_target or dqn.td_target
    collect_step = collect_step or dqn.collect_step
    observe = encoder(quant)
    shape = (2, 1, K) if quant else (K,)
    scale = np.array([1.0, 4.0], np.float32) if quant else None
    replay = replay_cls(4096, shape, np.float32, len(envs), n, gamma, scale)
    scripted = [ScriptedEnv(eps) for eps in envs]
    for e in scripted:
        e.reset()
    obs = [observe(e) for e in scripted]
    ep_ret = np.zeros(len(envs))
    rounds = sum(len(ep) for ep in envs[0])
    counts, finished = [], []
    cursors = [0] * len(envs)
    flat = [[st for ep in eps for st in ep] for eps in envs]
    for r in range(rounds):
        actions = [flat[i][r][1] for i in range(len(envs))]
        finished += collect_step(scripted, obs, actions, replay, observe, ep_ret, lambda e: e.reset())
        counts.append(replay.size)
    online, target = TableQ(table_from(q_online)), TableQ(table_from(q_target))
    o, a, ret, o2, disc = replay.sample(replay.size, SeqRng())
    y = td_target(online, target, ret, disc, o2, double)
    dec = (lambda t: t[:, 0].reshape(len(t), -1)) if quant else (lambda t: t)
    s, s2 = dec(o).argmax(1), dec(o2).argmax(1)
    samples = sorted((int(s[i]), int(a[i]), Fraction(float(ret[i])), Fraction(float(disc[i])), int(s2[i]), Fraction(float(y[i])))
                     for i in range(len(y)))
    return samples, counts, finished, replay


def expected(envs, q_online, q_target, n, gamma, double=True):
    norm = lambda q: {int(k): v for k, v in q.items()}  # noqa: E731  (JSON keys are strings)
    return oracle.expected_samples(envs, n, gamma, norm(q_online), norm(q_target), double)


def compare(actual, counts, want, want_counts, rel=0.0):
    """Raises AssertionError on the first difference.  rel=0 -> exact equality (gamma = 1/2 values are dyadic)."""
    assert counts == want_counts, f"stored samples after each round: {counts} != {want_counts}"
    assert len(actual) == len(want), f"{len(actual)} samples, expected {len(want)}"
    for got, exp in zip(actual, want):
        assert got[:2] == exp[:2] and got[4] == exp[4], f"sample identity differs: {got} vs {exp}"
        for g, e in zip(got[2:4] + got[5:], exp[2:4] + exp[5:]):
            assert abs(g - e) <= rel * max(1, abs(e)) if rel else g == e, f"value differs: {got} vs {exp}"


def run_and_compare(envs, q_online, q_target, n, gamma, double=True, quant=False, rel=0.0, **impl):
    actual, counts, _, replay = run_pipeline(envs, q_online, q_target, n, gamma, double, quant, **impl)
    want, want_counts = expected(envs, q_online, q_target, n, gamma, double)
    compare(actual, counts, want, want_counts, rel)
    return actual, counts, replay
