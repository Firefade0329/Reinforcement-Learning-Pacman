"""Loading + statistics shared by check_acceptance.py and make_report.py.

Everything is derived from the raw per-episode records in results/**.json.
"""
from __future__ import annotations

import json
import math
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
# Fields that older config.json files may legitimately lack (they were added after the first runs; the code
# defaults to these values).  Everything else in SHARED_HPARAMS + REQUIRED_CFG MUST be recorded.
CFG_DEFAULTS = {"n_step": 3, "double": True, "dueling": True, "obs": "fields"}
REQUIRED_CFG = ("arch", "seed")
MAX_SCORE = 377  # gold pellets on the map (Pacman's own start cell is cleared)
MAX_STEPS = 1000
SUMMARY_KEYS = ("best_val_score", "best_env_steps", "updates")
EVAL_SUMMARY_TOL = 1e-6


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
    else:
        _check_eval_values(problems, label, p)


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _check_eval_values(problems, label, p):
    """Per-episode values are in range, and the stored summary is what the records recompute to."""
    recs = p["records"]
    for r in recs:
        if not (_finite(r["score"]) and 0 <= r["score"] <= MAX_SCORE and _finite(r["steps"]) and 1 <= r["steps"] <= MAX_STEPS
                and isinstance(r["died"], bool) and isinstance(r["won"], bool) and not (r["died"] and r["won"])):
            problems.append(f"{label}: implausible record {r}")
            return
    s = p.get("summary")
    if not isinstance(s, dict):
        problems.append(f"{label}: summary block missing")
        return
    n = len(recs)
    recomputed = {"episodes": n, "score_mean": sum(r["score"] for r in recs) / n,
                  "death_rate": sum(r["died"] for r in recs) / n, "win_rate": sum(r["won"] for r in recs) / n,
                  "steps_mean": sum(r["steps"] for r in recs) / n}
    for k, v in recomputed.items():
        got = s.get(k)
        if not _finite(got) or abs(got - v) > EVAL_SUMMARY_TOL:
            problems.append(f"{label}: stored summary {k}={got} but the {n} per-episode records give {v:.6g}")


def _check_summary(problems, n, cfg):
    """summary.json is well-formed and agrees with the validation rows of train_log.jsonl."""
    s = load(RUNS / n / "summary.json")
    if s is None:
        problems.append(f"{n}: summary.json missing")
        return
    bad = [k for k in SUMMARY_KEYS if not (isinstance(s, dict) and _finite(s.get(k)))]
    if bad:
        problems.append(f"{n}: summary.json lacks finite {bad}")
        return
    if not 0 <= s["best_val_score"] <= MAX_SCORE:
        problems.append(f"{n}: summary best_val_score={s['best_val_score']} is outside [0, {MAX_SCORE}]")
    total = cfg.get("total_env_steps")
    if _finite(total) and not 0 < s["best_env_steps"] <= total:
        problems.append(f"{n}: summary best_env_steps={s['best_env_steps']} is outside (0, {total}]")
    log = RUNS / n / "train_log.jsonl"
    if not log.exists():
        problems.append(f"{n}: train_log.jsonl missing")
        return
    rows = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # a damaged line is the log's problem; the check below only needs the eval rows
    evals = [(r["env_steps"], r["val_score"]) for r in rows if r.get("type") == "eval"]
    if not evals:
        problems.append(f"{n}: train_log.jsonl has no validation rows")
        return
    best = max(v for _, v in evals)
    if abs(best - s["best_val_score"]) > EVAL_SUMMARY_TOL:
        problems.append(f"{n}: summary best_val_score={s['best_val_score']} but the best validation row in train_log.jsonl is {best}")
    elif s["best_env_steps"] not in [st for st, v in evals if v == best]:
        problems.append(f"{n}: summary best_env_steps={s['best_env_steps']} is not where train_log.jsonl reaches its best validation score")
    if _finite(total) and max(st for st, _ in evals) != total:
        problems.append(f"{n}: train_log.jsonl ends at {max(st for st, _ in evals)} steps, config says {total}")


def validate_matrix() -> list[str]:
    """Problems found in the committed matrix (empty list = M6 satisfied): every required run exists with
    300 test episodes on the fixed test seeds in both scenarios whose stored summaries recompute from the
    records, a well-formed summary.json that agrees with the validation rows of its training log, and a config
    that records every experiment setting and matches the run name; shared hyper-parameters (incl. training
    steps) are identical across all runs."""
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
        cfg = load(RUNS / n / "config.json")
        if cfg is None:
            problems.append(f"{n}: config.json missing")
            continue
        missing = [k for k in (*REQUIRED_CFG, *SHARED_HPARAMS) if cfg.get(k) is None]
        if missing:  # these are experiment settings, not optional fields: never fall back to a default
            problems.append(f"{n}: config.json lacks required field(s) {missing}")
        _check_summary(problems, n, cfg)
        exp = expected_config(n)
        for k, v in exp.items():
            if cfg.get(k, CFG_DEFAULTS.get(k)) != v:
                problems.append(f"{n}: config {k}={cfg.get(k)} but the run name implies {v}")
        for k, dflt in CFG_DEFAULTS.items():
            if k not in exp and not (k == "obs" and cfg.get("arch") == "mlp") and cfg.get(k, dflt) != dflt:
                problems.append(f"{n}: config {k}={cfg.get(k)} differs from the default {dflt} without being a named variant")
        for k in SHARED_HPARAMS:
            if cfg.get(k) is not None:
                seen[k].add(json.dumps(cfg.get(k)))
    for k, vals in seen.items():
        if len(vals) > 1:
            problems.append(f"shared hyper-parameter {k} differs across runs: {sorted(vals)}")
    return problems


def strip_timing(line: str) -> str:
    """'46 passed, 1 skipped in 20.31s (0:00:20)' -> '46 passed, 1 skipped' (stable across machines)."""
    return re.sub(r" in [0-9.]+s( \([0-9:]+\))?\s*$", "", line.strip())
