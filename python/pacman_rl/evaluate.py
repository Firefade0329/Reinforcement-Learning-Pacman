"""Unified evaluation: fixed seed splits, per-episode records, bootstrap / paired CIs."""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .baselines import make_agent
from .env import HARD, STANDARD, EnvConfig, PacmanEnv

VAL_SEEDS = list(range(5000, 5050))  # model selection only
TEST_SEEDS = list(range(10000, 10300))  # final numbers only
EQUIV_SEEDS = list(range(20000, 20300))  # fidelity checks of NON-learning agents (never used for selection or final numbers)
# Preregistered architecture x n-step study (docs/prereg/): its own selection / sealed final / smoke partitions.
PREREG_VAL_SEEDS = list(range(21000, 21050))  # model selection of the preregistered runs
PREREG_TEST_SEEDS = list(range(30000, 30300))  # SEALED by protocol: the final evaluation reads it after all runs are complete (the constant itself is public)
SMOKE_EVAL_SEEDS = list(range(40000, 40010))  # throughput / correctness smoke runs only
SCENARIOS = {"standard": STANDARD, "hard": HARD}
TRAIN_SEED_BASE = 1_000_000  # training episode seeds: base * (run_seed + 1) + k  (disjoint from val/test)

SEED_SETS: dict[str, list[int]] = {
    "val": VAL_SEEDS, "test": TEST_SEEDS, "equiv": EQUIV_SEEDS,
    "prereg_val": PREREG_VAL_SEEDS, "prereg_test": PREREG_TEST_SEEDS, "smoke_eval": SMOKE_EVAL_SEEDS,
}
SEALED_SETS = frozenset({"prereg_test"})  # cannot be resolved without an unseal token (see pacman_rl/seal.py)
SELECTION_SETS = ("val", "prereg_val", "smoke_eval")  # the only sets a training run may use for checkpoint selection


class SealedSetError(RuntimeError):
    pass


def seed_set(name: str, unseal=None) -> list[int]:
    """Seed list of a named partition, resolved at call time (never bound at import).  Sealed partitions
    need ``unseal`` = the token returned by ``seal.verify_manifest`` (all runs complete, hashes verified)."""
    if name not in SEED_SETS:
        raise KeyError(f"unknown seed set {name!r}; known: {sorted(SEED_SETS)}")
    if name in SEALED_SETS:
        from .seal import UnsealToken

        if not isinstance(unseal, UnsealToken):
            raise SealedSetError(f"seed set {name!r} is sealed: it can only be read by the final evaluation with a verified "
                                 f"integrity manifest (prereg.py final-eval --manifest ... --unseal)")
    return list(SEED_SETS[name])


def train_seed(run_seed: int, k: int) -> int:
    return TRAIN_SEED_BASE * (run_seed + 1) + k


def splits() -> dict[str, list[int]]:
    return {"val": VAL_SEEDS, "test": TEST_SEEDS}  # legacy two-split view; use seed_set() for the named partitions


# --------------------------------------------------------------------------- running
def play_episode(agent, cfg: EnvConfig, seed: int) -> dict:
    env = PacmanEnv(cfg)
    env.reset(seed)
    agent.reset()
    info = {"score": 0, "steps": 0, "died": False, "won": False}
    done = False
    while not done:
        _, _, term, trunc, info = env.step(agent.act(env))
        done = term or trunc
    return {"seed": seed, "score": info["score"], "steps": info["steps"],
            "died": bool(info["died"]), "won": bool(info["won"])}


def _worker(args):
    name, cfg, seed = args
    return play_episode(make_agent(name, seed), cfg, seed)


def evaluate_named(name: str, cfg: EnvConfig, seeds, workers: int = 4) -> list[dict]:
    jobs = [(name, cfg, s) for s in seeds]
    if workers <= 1:
        return [_worker(j) for j in jobs]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_worker, jobs, chunksize=max(1, len(jobs) // (workers * 4))))


def evaluate_batched(policy, cfg: EnvConfig, seeds, observe, record_truncated: bool = False) -> list[dict]:
    """Run all episodes in lock-step so a neural policy can be called once per step on a batch.

    ``observe(env) -> array`` builds one observation; ``policy(batch) -> actions``.
    ``record_truncated`` adds the time-limit flag to every record (new evaluation path only; the default keeps the
    historical record layout byte-for-byte).
    """
    envs = [PacmanEnv(cfg) for _ in seeds]
    for e, s in zip(envs, seeds):
        e.reset(s)
    live = list(range(len(envs)))
    out: dict[int, dict] = {}
    infos = {i: {"score": 0, "steps": 0, "died": False, "won": False} for i in live}
    while live:
        batch = np.stack([observe(envs[i]) for i in live])
        actions = policy(batch)
        nxt = []
        for i, a in zip(live, actions):
            _, _, term, trunc, info = envs[i].step(int(a))
            infos[i] = info
            if term or trunc:
                out[i] = {"seed": seeds[i], "score": info["score"], "steps": info["steps"],
                          "died": bool(info["died"]), "won": bool(info["won"])}
                if record_truncated:
                    out[i]["truncated"] = bool(trunc)
            else:
                nxt.append(i)
        live = nxt
    return [out[i] for i in range(len(seeds))]


# --------------------------------------------------------------------------- statistics
def bootstrap_ci(x, n_boot: int = 5000, seed: int = 0, alpha: float = 0.05):
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def paired_diff_ci(a, b, n_boot: int = 5000, seed: int = 0):
    """Mean of (a - b) over episodes with identical seeds, plus 95 % bootstrap CI."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    lo, hi = bootstrap_ci(d, n_boot, seed)
    return float(d.mean()), lo, hi


def summarize(records: list[dict]) -> dict:
    score = np.array([r["score"] for r in records], dtype=float)
    died = np.array([r["died"] for r in records], dtype=float)
    won = np.array([r["won"] for r in records], dtype=float)
    steps = np.array([r["steps"] for r in records], dtype=float)
    return {
        "episodes": len(records),
        "score_mean": float(score.mean()), "score_ci": bootstrap_ci(score),
        "score_median": float(np.median(score)),
        "death_rate": float(died.mean()), "death_ci": bootstrap_ci(died),
        "win_rate": float(won.mean()), "win_ci": bootstrap_ci(won),
        "steps_mean": float(steps.mean()),
    }


# --------------------------------------------------------------------------- persistence
def save_eval(path: Path, agent: str, scenario: str, split: str, records: list[dict], extra: dict | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"agent": agent, "scenario": scenario, "split": split,
               "env_config": asdict(SCENARIOS[scenario]), "summary": summarize(records),
               "records": records}
    if extra:
        payload["extra"] = extra
    path.write_text(json.dumps(payload, indent=1), newline="\n")  # LF on every platform (these files are compared and hashed)
    return payload


def load_eval(path: Path) -> dict:
    return json.loads(Path(path).read_text())
