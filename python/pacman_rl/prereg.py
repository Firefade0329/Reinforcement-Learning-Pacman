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
MATRIX_FILE = PREREG_DIR / "matrix_v0.3.1.csv"
FREEZE_FILE = PREREG_DIR / "freeze_config.json"
MATRIX_SHA256 = "5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe"
COLUMNS = ("order", "run_name", "arch", "n_step", "seed", "total_env_steps", "obs", "width", "double", "dueling", "lr", "gamma",
           "n_envs", "steps_per_update", "batch", "buffer", "learn_start", "eval_every", "threads", "device", "primary_checkpoint")
ARCHS, NSTEPS, SEEDS = ("cnn2", "res4", "res8"), (1, 3), (100, 101, 102, 103, 104)
# what every row must contain (the study's fixed conditions)
FIXED_ROW = {"total_env_steps": 300000, "obs": "fields", "width": 16, "double": True, "dueling": True, "lr": 0.0005, "gamma": 0.99,
             "n_envs": 8, "steps_per_update": 4, "batch": 32, "buffer": 100000, "learn_start": 4000, "eval_every": 20000,
             "threads": 1, "device": "cuda", "primary_checkpoint": "last"}
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
    kw.update(freeze["fixed_hparams"])
    kw["val_set"] = freeze["seeds"]["val_set"]
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
