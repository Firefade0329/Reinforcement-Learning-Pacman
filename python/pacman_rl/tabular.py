"""Standard tabular Q-learning on the 64-state design (gold direction x ghost mask).

Differences from the Java QLearning.java: no per-row normalisation, alpha < 1, a real
epsilon-greedy schedule, terminal states handled, and the ghost-avoidance behaviour is *learned*
(the Java agent used a hard-coded flee rule).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .baselines import Agent
from .env import NUM_ACTIONS, STANDARD, EnvConfig, PacmanEnv
from .evaluate import train_seed
from .features import NUM_TABULAR_STATES, tabular_state


class TabularAgent(Agent):
    name = "tabular-q"

    def __init__(self, q: np.ndarray):
        self.q = q

    def act(self, env) -> int:
        return int(np.argmax(self.q[tabular_state(env)]))


def train_tabular(episodes: int = 3000, seed: int = 0, cfg: EnvConfig = STANDARD, alpha: float = 0.1,
                  gamma: float = 0.9, eps_start: float = 1.0, eps_end: float = 0.05, log=None):
    rng = np.random.default_rng(seed)
    q = np.zeros((NUM_TABULAR_STATES, NUM_ACTIONS))
    env = PacmanEnv(cfg)
    curve = []
    for ep in range(episodes):
        eps = max(eps_end, eps_start - (eps_start - eps_end) * ep / (0.5 * episodes))
        env.reset(train_seed(seed, ep))
        s, ret, done = tabular_state(env), 0.0, False
        while not done:
            a = int(rng.integers(NUM_ACTIONS)) if rng.random() < eps else int(np.argmax(q[s]))
            _, r, term, trunc, info = env.step(a)
            done = term or trunc
            s2 = tabular_state(env) if not done else s
            target = r if term else r + gamma * q[s2].max()  # truncation still bootstraps
            q[s, a] += alpha * (target - q[s, a])
            s, ret = s2, ret + r
        curve.append((ep, ret, info["score"]))
        if log and (ep + 1) % 500 == 0:
            recent = np.array(curve[-500:])
            log(f"tabular ep {ep + 1}: eps={eps:.2f} return={recent[:, 1].mean():.1f} score={recent[:, 2].mean():.1f}")
    return q, curve


def save_q(path: Path, q: np.ndarray, curve) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"q": q.tolist(), "curve": curve}))


def load_q(path: Path) -> np.ndarray:
    return np.array(json.loads(Path(path).read_text())["q"])
