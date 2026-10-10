"""The preregistered architecture x n-step study: matrix and frozen-configuration handling (no process orchestration,
see scripts/prereg.py).

The run order is FIXED BY THE MATRIX FILE (column ``order``); nothing here generates or shuffles it.  Everything a run is
trained with is derived from the matrix row plus the frozen configuration and passed to ``cli train`` explicitly, so no
default of the code can silently change a preregistered setting.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, fields
from pathlib import Path

from .dqn import TrainConfig
from .provenance import ROOT, file_sha256

PREREG_DIR = ROOT / "docs" / "prereg"
MATRIX_FILE = PREREG_DIR / "matrix.csv"
FREEZE_FILE = PREREG_DIR / "frozen_config_v0.3.2.json"
MATRIX_SHA256 = "5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe"
COLUMNS = ("order", "run_name", "arch", "n_step", "seed", "total_env_steps", "obs", "width", "double", "dueling", "lr", "gamma",
           "n_envs", "steps_per_update", "batch", "buffer", "learn_start", "eval_every", "threads", "device", "primary_checkpoint")
ARCHS, NSTEPS, SEEDS = ("cnn2", "res4", "res8"), (1, 3), (100, 101, 102, 103, 104)
# what every row must contain (the study's fixed conditions)
FIXED_ROW = {"total_env_steps": 300000, "obs": "fields", "width": 16, "double": True, "dueling": True, "lr": 0.0005, "gamma": 0.99,
             "n_envs": 8, "steps_per_update": 4, "batch": 32, "buffer": 100000, "learn_start": 4000, "eval_every": 20000,
             "threads": 1, "device": "cuda", "primary_checkpoint": "last"}
FROZEN_HPARAMS = ("eps_start", "eps_end", "eps_frac", "tau", "grad_clip")
_INT = {"order", "n_step", "seed", "total_env_steps", "width", "n_envs", "steps_per_update", "batch", "buffer", "learn_start", "eval_every", "threads"}
_FLOAT = {"lr", "gamma"}
_BOOL = {"double", "dueling"}


def load_matrix(path: Path | None = None) -> list[dict]:
    with open(path or MATRIX_FILE, newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    rows = []
    for r in raw:
        row = {}
        for k, v in r.items():
            row[k] = int(v) if k in _INT else float(v) if k in _FLOAT else {"true": True, "false": False}[v] if k in _BOOL else v
        rows.append(row)
    return rows


def load_freeze(path: Path | None = None) -> dict:
    return json.loads((path or FREEZE_FILE).read_text(encoding="utf-8"))


def validate_matrix(rows: list[dict], *, official: bool = True) -> list[str]:
    """Problems found in a matrix (empty = fine).  ``official`` also demands the full 30-row design."""
    problems = []
    if rows and tuple(rows[0]) != COLUMNS:
        problems.append(f"columns {tuple(rows[0])} != {COLUMNS}")
    for r in rows:
        want = f"prereg_{r['arch']}_n{r['n_step']}_s{r['seed']}"
        if r["run_name"] != want:
            problems.append(f"row {r['order']}: run_name {r['run_name']!r} != {want!r}")
        for k, v in FIXED_ROW.items():
            if r[k] != v:
                problems.append(f"row {r['order']}: {k}={r[k]!r} but the study fixes {v!r}")
        if r["arch"] not in ARCHS or r["n_step"] not in NSTEPS:
            problems.append(f"row {r['order']}: unexpected arch/n_step {r['arch']}/{r['n_step']}")
    if len({r["run_name"] for r in rows}) != len(rows):
        problems.append("duplicate run names")
    if official:
        if [r["order"] for r in rows] != list(range(1, 31)):
            problems.append("order column must be 1..30")
        for b in range(5):
            block = rows[6 * b: 6 * b + 6]
            combos = {(r["arch"], r["n_step"]) for r in block}
            if {r["seed"] for r in block} != {SEEDS[b]} or len(combos) != 6 or combos != {(a, n) for a in ARCHS for n in NSTEPS}:
                problems.append(f"rows {6 * b + 1}-{6 * b + 6}: must be the six distinct (arch, n_step) configurations of seed {SEEDS[b]}")
    return problems


def check_matrix_file(path: Path | None = None) -> list[str]:
    path = path or MATRIX_FILE
    problems = []
    if file_sha256(path) != MATRIX_SHA256:
        problems.append(f"{path.name}: SHA-256 {file_sha256(path)} != {MATRIX_SHA256}")
    return problems + validate_matrix(load_matrix(path))


def train_config(row: dict, freeze: dict, **overrides) -> TrainConfig:
    """TrainConfig of a run: matrix row + fixed hyper-parameters + selection set of the frozen configuration."""
    kw = {k: row[k] for k in ("arch", "obs", "width", "double", "dueling", "n_step", "gamma", "lr", "batch", "buffer", "learn_start",
                              "n_envs", "steps_per_update", "total_env_steps", "eval_every", "seed", "threads", "device")}
    kw.update({k: freeze[k] for k in FROZEN_HPARAMS})  # the five settings the CSV does not carry
    kw["val_set"] = freeze["val_set"]
    kw.update(overrides)
    return TrainConfig(**kw)


def train_args(cfg: TrainConfig, name: str) -> list[str]:
    """Explicit ``cli train`` arguments for EVERY field of the config (no reliance on defaults); bools use --no-<flag>."""
    args = ["--name", name]
    for f in fields(TrainConfig):
        v = getattr(cfg, f.name)
        if isinstance(v, bool):
            if not v:
                args.append(f"--no-{f.name}")
        else:
            args += [f"--{f.name}", str(v)]
    return args


def expected_config_json(cfg: TrainConfig) -> dict:
    return json.loads(json.dumps(asdict(cfg)))


def check_frozen_config(freeze: dict) -> list[str]:
    """The frozen configuration must agree with what the code really uses (seed arrays, defaults, scenario facts)."""
    from . import evaluate as ev
    from .env import HARD, STANDARD

    problems = []
    for key, name in (("val_seeds", freeze["val_set"]), ("test_seeds", freeze["test_set"]), ("smoke_eval_seeds", freeze["smoke_val_set"])):
        if freeze[key] != ev.SEED_SETS[name]:
            problems.append(f"{key} differs from the seeds the code uses for {name!r}")
    if freeze["eval_episodes"] != len(freeze["val_seeds"]):
        problems.append("eval_episodes != number of validation seeds")
    for k in FROZEN_HPARAMS:
        if freeze[k] != getattr(TrainConfig(), k):
            problems.append(f"{k}={freeze[k]} differs from the code default {getattr(TrainConfig(), k)} (it would be passed explicitly, but the defaults must not drift)")
    if freeze["max_episode_steps"] != STANDARD.max_steps or freeze["hard_chase_p"] != HARD.chase_prob:
        problems.append("max_episode_steps / hard_chase_p differ from the environment definitions")
    if freeze["matrix_sha256"] != MATRIX_SHA256:
        problems.append("frozen config matrix_sha256 differs from the pinned value")
    if freeze["formal_run_seeds"] != list(SEEDS):
        problems.append("formal_run_seeds differs from the matrix design")
    return problems


def effective_config(row: dict, freeze: dict, cfg: TrainConfig, code_commit: str | None, frozen_config_sha256: str) -> dict:
    """The merged effective configuration written as runs/<run>/config.json: every TrainConfig field actually used (this
    covers each CSV column and the five CSV-external settings) plus the run identity and the frozen supplementary values."""
    out = expected_config_json(cfg)
    out.update({"order": row["order"], "run_name": row["run_name"], "primary_checkpoint": row["primary_checkpoint"],
                "code_commit": code_commit, "frozen_config_sha256": frozen_config_sha256})
    for k in ("val_seeds", "test_seeds", "smoke_eval_seeds", "smoke_run_seeds", "eval_episodes", "final_eval_device", "final_eval_threads",
              "hard_enabled", "machine_id", "train_device", "validation_device", "worker_count", "max_episode_steps", "train_scenario",
              "hard_chase_p"):
        out[k] = freeze[k]
    return out


def summary_contract_problems(summary, cfg: TrainConfig, name: str, log_rows=None) -> list[str]:
    """Does a run's summary.json (and, when given, its train_log rows) satisfy the preregistered contract for ``cfg``?  Used when a run is
    finalized AND again before the sealed seeds may be read, so a summary that was removed or edited afterwards cannot pass."""
    from .evaluate import seed_set

    if not isinstance(summary, dict):
        return ["summary.json is not a JSON object"]
    problems = []
    boundaries = list(range(cfg.eval_every, cfg.total_env_steps + 1, cfg.eval_every))
    want_steps = boundaries + ([cfg.total_env_steps] if cfg.total_env_steps % cfg.eval_every else [])  # formal: exactly 15
    isint = lambda x: isinstance(x, int) and not isinstance(x, bool)  # noqa: E731
    cks = summary.get("checkpoints") if isinstance(summary.get("checkpoints"), dict) else {}
    last, best = (cks.get("last") or {}), (cks.get("best") or {})
    if summary.get("run_name") != name:
        problems.append(f"summary run_name {summary.get('run_name')!r} != {name!r}")
    if summary.get("total_env_steps") != cfg.total_env_steps or summary.get("env_steps") != cfg.total_env_steps:
        problems.append(f"budget: total_env_steps={summary.get('total_env_steps')}, env_steps={summary.get('env_steps')}, expected {cfg.total_env_steps}")
    if not isint(summary.get("actual_updates")) or summary["actual_updates"] < 0:
        problems.append("actual_updates must be a non-negative integer")
    size = (summary.get("replay") or {}).get("size") if isinstance(summary.get("replay"), dict) else None
    if not isint(size) or not 0 <= size <= cfg.buffer:
        problems.append(f"replay.size must be an integer in [0, {cfg.buffer}]")
    if summary.get("validation_steps") != want_steps:
        problems.append(f"validation_steps {summary.get('validation_steps')} != {want_steps}")
    if summary.get("validation_episodes_each") != len(seed_set(cfg.val_set)):
        problems.append(f"validation_episodes_each != {len(seed_set(cfg.val_set))}")
    if last.get("step") != cfg.total_env_steps:
        problems.append("last checkpoint step != the full budget")
    if best.get("step") not in want_steps:
        problems.append("best checkpoint step is not one of the validation steps")
    if any(not (isinstance(c.get("weights_sha256"), str) and len(c["weights_sha256"]) == 64) for c in (last, best)):
        problems.append("checkpoint weight hashes missing")
    if log_rows is not None:
        init = [r for r in log_rows if r.get("type") == "init"]
        evals = [r for r in log_rows if r.get("type") == "eval"]
        if len(init) != 1 or any(r.get("type") == "resume" for r in log_rows):
            problems.append("train_log.jsonl must hold exactly one init row and no resume marker")
        elif summary.get("initial_state_dict_sha256") != init[0].get("online_hash"):
            problems.append("summary initial hash differs from the init row of train_log.jsonl")
        if [r.get("env_steps") for r in evals] != want_steps:
            problems.append(f"train_log.jsonl validation rows {[r.get('env_steps') for r in evals]} != {want_steps}")
        elif evals:
            top = max(r["val_score"] for r in evals)
            first = next(r["env_steps"] for r in evals if r["val_score"] == top)
            if best.get("step") != first or summary.get("best_val_score") != top:
                problems.append("best checkpoint step / score differ from the first strict maximum of the validation rows in train_log.jsonl")
    return problems
