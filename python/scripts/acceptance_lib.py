"""Loading + statistics shared by check_acceptance.py and make_report.py.

Everything is derived from the raw per-episode records in results/**.json.
"""
from __future__ import annotations

import json
import os
import re
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


# ------------------------------------------------------------------ matrix validation (M6)
TEST_SEED_LIST = list(range(10000, 10300))
REQUIRED_FIELDS = ("seed", "score", "steps", "died", "won")
SHARED_HPARAMS = ("total_env_steps", "lr", "batch", "buffer", "gamma", "tau", "n_envs", "steps_per_update",
                  "eps_start", "eps_end", "eps_frac", "grad_clip", "learn_start", "eval_every", "width")
CFG_DEFAULTS = {"n_step": 3, "double": True, "dueling": True, "obs": "fields"}


def expected_config(name: str) -> dict:
    """What the run name promises about its config (variant flags relative to the defaults)."""
    base, seed = name.rsplit("_s", 1)
    exp = {"seed": int(seed)}
    if base.endswith("raw"):
        exp.update(arch=base[:-3], obs="grid")
    elif "-" in base:
        arch, var = base.split("-", 1)
        exp["arch"] = arch
        exp.update({"nodouble": {"double": False}, "nodueling": {"dueling": False}, "nstep1": {"n_step": 1}}[var])
    else:
        exp["arch"] = base
    return exp


def _check_eval_payload(problems, label, p, scenario):
    if p is None:
        problems.append(f"{label}: missing")
        return
    recs = p.get("records", [])
    if p.get("scenario") != scenario or p.get("split") != "test":
        problems.append(f"{label}: scenario/split tag is {p.get('scenario')}/{p.get('split')}")
    if len(recs) != len(TEST_SEED_LIST):
        problems.append(f"{label}: {len(recs)} episodes (expected {len(TEST_SEED_LIST)})")
    elif sorted(r.get("seed") for r in recs) != TEST_SEED_LIST:
        problems.append(f"{label}: test seeds differ from {TEST_SEED_LIST[0]}..{TEST_SEED_LIST[-1]}")
    elif any(k not in r for r in recs for k in REQUIRED_FIELDS):
        problems.append(f"{label}: records missing fields")


def validate_matrix() -> list[str]:
    """Problems found in the committed matrix (empty list = M6 satisfied): every required run exists with
    300 test episodes on the fixed test seeds in both scenarios, a summary, and a config matching its name;
    shared hyper-parameters (incl. training steps) are identical across all runs."""
    problems: list[str] = []
    for b in BASELINES:
        for sc in ("standard", "hard"):
            _check_eval_payload(problems, f"baseline {b}/{sc}", baseline(b, sc), sc)
    for s in SEEDS:
        for sc in ("standard", "hard"):
            _check_eval_payload(problems, f"tabular_s{s}/{sc}", run_eval(f"tabular_s{s}", sc), sc)
    names = [n for a in ARCHS for n in run_names(a)]
    names += [f"{a}-{v}_s{s}" for a in (ABLATION_ARCH, "mlp") for v in ("nodouble", "nodueling", "nstep1") for s in SEEDS]
    names += [f"{ABLATION_ARCH}raw_s{s}" for s in SEEDS]
    seen: dict[str, set] = {k: set() for k in SHARED_HPARAMS}
    for n in names:
        for sc in ("standard", "hard"):
            _check_eval_payload(problems, f"{n}/{sc}", run_eval(n, sc), sc)
        if load(RUNS / n / "summary.json") is None:
            problems.append(f"{n}: summary.json missing")
        cfg = load(RUNS / n / "config.json")
        if cfg is None:
            problems.append(f"{n}: config.json missing")
            continue
        exp = expected_config(n)
        for k, v in exp.items():
            if cfg.get(k, CFG_DEFAULTS.get(k)) != v:
                problems.append(f"{n}: config {k}={cfg.get(k)} but the run name implies {v}")
        for k, dflt in CFG_DEFAULTS.items():
            if k not in exp and not (k == "obs" and cfg.get("arch") == "mlp") and cfg.get(k, dflt) != dflt:
                problems.append(f"{n}: config {k}={cfg.get(k)} differs from the default {dflt} without being a named variant")
        for k in SHARED_HPARAMS:
            seen[k].add(json.dumps(cfg.get(k)))
    for k, vals in seen.items():
        if len(vals) > 1:
            problems.append(f"shared hyper-parameter {k} differs across runs: {sorted(vals)}")
    return problems


def strip_timing(line: str) -> str:
    """'46 passed, 1 skipped in 20.31s (0:00:20)' -> '46 passed, 1 skipped' (stable across machines)."""
    return re.sub(r" in [0-9.]+s( \([0-9:]+\))?\s*$", "", line.strip())
