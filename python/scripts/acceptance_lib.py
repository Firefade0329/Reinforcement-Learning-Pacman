"""Loading + statistics shared by check_acceptance.py and make_report.py.

Everything is derived from the raw per-episode records in results/**.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(os.environ.get("PACMAN_RESULTS_DIR") or ROOT / "results")
RUNS = RESULTS / "runs"
SEEDS = (0, 1, 2)
ARCHS = ("mlp", "cnn2", "res2", "res4", "res8")
BASELINES = ("random", "greedy-bfs", "legacy", "safe-heuristic")
ABLATION_ARCH = "res4"  # algorithm ablations run on this architecture (fixed a priori)
JAVA_BASE_COMMIT = "1e9da5c"  # repository HEAD before any Python work started (hash after the 2026-10-08 history rewrite; was 5d5efd5)


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else None


def baseline(agent: str, scenario: str = "standard", split: str = "test"):
    return load(RESULTS / "eval" / f"{agent}__{scenario}__{split}.json")


def run_eval(name: str, scenario: str = "standard", split: str = "test"):
    return load(RUNS / name / f"{split}_{scenario}.json")


def per_episode(payload, key: str) -> np.ndarray:
    """Per-episode values ordered by seed (records are already in seed order)."""
    recs = sorted(payload["records"], key=lambda r: r["seed"])
    return np.array([float(r[key]) for r in recs])


def seed_avg(names: list[str], scenario: str, key: str):
    """Average a metric over runs episode-by-episode (same seeds => aligned). None if incomplete."""
    ps = [run_eval(n, scenario) for n in names]
    if any(p is None for p in ps):
        return None
    return np.mean([per_episode(p, key) for p in ps], axis=0)


def boot_ci(x: np.ndarray, n_boot: int = 10000, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    m = x[idx].mean(axis=1)
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def paired(a: np.ndarray, b: np.ndarray):
    d = a - b
    lo, hi = boot_ci(d)
    return float(d.mean()), lo, hi


def val_score(name: str) -> float | None:
    s = load(RUNS / name / "summary.json")
    return None if s is None else s["best_val_score"]


def arch_val_mean(arch: str) -> float | None:
    v = [val_score(f"{arch}_s{s}") for s in SEEDS]
    return None if any(x is None for x in v) else float(np.mean(v))


def final_arch() -> str | None:
    """Headline architecture, chosen by mean *validation* score only (test never consulted)."""
    cands = {a: arch_val_mean(a) for a in ARCHS}
    cands = {a: v for a, v in cands.items() if v is not None}
    return max(cands, key=cands.get) if cands else None


def best_resnet() -> str | None:
    cands = {a: arch_val_mean(a) for a in ("res2", "res4", "res8")}
    cands = {a: v for a, v in cands.items() if v is not None}
    return max(cands, key=cands.get) if cands else None


def run_names(arch: str) -> list[str]:
    return [f"{arch}_s{s}" for s in SEEDS]
