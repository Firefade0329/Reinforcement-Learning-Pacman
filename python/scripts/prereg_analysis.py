#!/usr/bin/env python3
"""Analysis of the preregistered architecture x n-step study (ANALYSIS_SPEC_v0.3.2.md).

  python prereg_analysis.py analyze --mode synthetic --manifest M --input-root R --output-dir O [--project-root P]
  python prereg_analysis.py analyze --mode formal    --manifest docs/prereg/freeze_manifest.json \\
        --input-root results_prereg/runs --output-dir results_prereg/analysis/<analysis_id> --project-root .

Reads ONLY the files the manifest and the evaluation seal name (no scanning of results/ or results_gpu/, no .pt files, no
training or validation records).  Every input is validated completely before any statistic is computed; an integrity error
exits with status 2 and a JSON error object on stderr and leaves no output directory behind.  Depends on numpy only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from itertools import combinations  # noqa: F401  (kept for clarity of the sign-test formula below)
from pathlib import Path

import numpy as np

SPEC_VERSION = "0.3.2"
MATRIX_SHA256 = "5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe"
ARCHS = ("cnn2", "res4", "res8")
NSTEPS = (1, 3)
SEEDS = (100, 101, 102, 103, 104)
TEST_SEEDS = tuple(range(30000, 30300))
VAL_SEEDS = tuple(range(21000, 21050))
RESERVED = {"smoke40000-40009": range(40000, 40010), "equiv20000-20299": range(20000, 20300),
            "old_val5000-5049": range(5000, 5050), "old_test10000-10299": range(10000, 10300)}
VALIDATION_STEPS = list(range(20000, 300001, 20000))
T95, T975 = 2.7764451051977944, 3.4954059325164377  # df=4: t(0.975), t(0.9875); checked against the analytic CDF
B, BOOT_SEED = 10000, 271828
EXPECTED_INDEX_SHA = "f3c35599fe764bf0a2c124544930609b643c2d5aa33ee0acc5b34454d91c9f69"
ENDPOINTS = ("last_standard", "best_standard", "last_hard")
CSV_COLUMNS = ("order", "run_name", "arch", "n_step", "seed", "total_env_steps", "obs", "width", "double", "dueling", "lr", "gamma",
               "n_envs", "steps_per_update", "batch", "buffer", "learn_start", "eval_every", "threads", "device", "primary_checkpoint")
FROZEN_REQUIRED = ("eps_start", "eps_end", "eps_frac", "tau", "grad_clip", "val_seeds", "test_seeds", "smoke_eval_seeds", "smoke_run_seeds",
                   "eval_episodes", "final_eval_device", "final_eval_threads", "hard_enabled", "code_commit", "machine_id", "train_device",
                   "validation_device", "worker_count", "max_episode_steps", "train_scenario", "hard_chase_p")
HEX64 = set("0123456789abcdef")
SCRIPT_PATH = Path(__file__).resolve()  # the bytes of THIS file must equal the hash the freeze manifest locked
REQUIRED_DOCS = ("docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md", "docs/prereg/ANALYSIS_SPEC_v0.3.2.md")  # must be in frozen_files in formal mode


class AnalysisError(Exception):
    def __init__(self, code, message, path=None, run_name=None, record_index=None, seed=None, expected=None, actual=None, json_path=None):
        super().__init__(message)
        self.obj = {"code": code, "path": path, "json_path": json_path, "run_name": run_name, "record_index": record_index, "seed": seed,
                    "expected": expected, "actual": actual, "message": message}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_hex64(x):
    return isinstance(x, str) and len(x) == 64 and set(x) <= HEX64


# ----------------------------------------------------------------------------------------------- strict JSON
def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise AnalysisError("E_JSON_DUPLICATE_KEY", f"duplicate key {k!r}", actual=k)
        d[k] = v
    return d


def _walk_finite(obj, rel, name):
    if isinstance(obj, float) and not math.isfinite(obj):
        raise AnalysisError("E_NONFINITE", "non-finite number in the JSON tree", path=rel, run_name=name, actual="NaN" if obj != obj else ("Infinity" if obj > 0 else "-Infinity"))
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_finite(v, rel, name)
    elif isinstance(obj, list):
        for v in obj:
            _walk_finite(v, rel, name)


def read_json(path: Path, rel: str, run_name=None):
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise AnalysisError("E_JSON_PARSE", f"cannot read {rel}: {e}", path=rel, run_name=run_name)

    def bad_const(name):
        raise AnalysisError("E_NONFINITE", f"JSON constant {name} is not allowed", path=rel, run_name=run_name, actual=name)

    try:
        obj = json.loads(text, object_pairs_hook=_no_dupes, parse_constant=bad_const)
    except AnalysisError as e:
        e.obj.update(path=rel, run_name=run_name)
        raise
    except (ValueError, RecursionError) as e:
        raise AnalysisError("E_JSON_PARSE", f"invalid JSON in {rel}: {e}", path=rel, run_name=run_name)
    _walk_finite(obj, rel, run_name)
    return obj


# ----------------------------------------------------------------------------------------------- inputs
def load_matrix(path: Path):
    import csv as _csv

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(_csv.DictReader(f))
    conv = {"order": int, "n_step": int, "seed": int, "total_env_steps": int, "width": int, "n_envs": int, "steps_per_update": int, "batch": int,
            "buffer": int, "learn_start": int, "eval_every": int, "threads": int, "lr": float, "gamma": float,
            "double": lambda v: {"true": True, "false": False}[v], "dueling": lambda v: {"true": True, "false": False}[v]}
    return [{k: conv.get(k, str)(v) for k, v in r.items()} for r in rows]


def validate_inputs(manifest_path: Path, input_root: Path, project_root: Path | None, mode: str):
    """Steps 1-7 of ANALYSIS_SPEC 2.3.  Returns a context dict; raises AnalysisError."""
    if not manifest_path.is_file():
        raise AnalysisError("E_MISSING_FILE", "freeze manifest not found", path=manifest_path.name)
    manifest = _obj(read_json(manifest_path, manifest_path.name), manifest_path.name, None, "$")
    need = ("schema_version", "synthetic", "complete", "spec_version", "code_commit", "project_root", "matrix_path", "config_path",
            "analysis_script_path", "dependency_lock_path", "frozen_files", "seal_path")
    for k in need:
        if k not in manifest:
            raise AnalysisError("E_MANIFEST", f"manifest lacks {k!r}", path=manifest_path.name, expected=k)
    if manifest["schema_version"] != "prereg-freeze-1" or manifest["spec_version"] != SPEC_VERSION:
        raise AnalysisError("E_MANIFEST", "unsupported manifest schema / spec version", actual=[manifest["schema_version"], manifest["spec_version"]])
    if manifest["synthetic"] is not (mode == "synthetic") or manifest["complete"] is not True:
        raise AnalysisError("E_MANIFEST", f"mode {mode!r} needs synthetic={mode == 'synthetic'} and complete=true", actual=[manifest["synthetic"], manifest["complete"]])
    if not (isinstance(manifest["code_commit"], str) and len(manifest["code_commit"]) == 40 and set(manifest["code_commit"]) <= HEX64):
        raise AnalysisError("E_MANIFEST", "code_commit must be a full 40-hex commit", actual=manifest["code_commit"])
    for k in ("project_root", "matrix_path", "config_path", "analysis_script_path", "dependency_lock_path", "seal_path"):
        _str(manifest[k], manifest_path.name, None, f"$.{k}")
    _obj(manifest["frozen_files"], manifest_path.name, None, "$.frozen_files")
    root = Path(manifest["project_root"])
    if not root.is_absolute():
        if project_root is None:
            raise AnalysisError("E_MANIFEST", "manifest project_root is relative: pass an explicit --project-root", actual=manifest["project_root"])
        root = Path(project_root) / root
    root = root.resolve()
    for rel, want in manifest["frozen_files"].items():
        f = root / rel
        if not f.is_file():
            raise AnalysisError("E_MISSING_FILE", f"frozen file {rel} not found", path=rel)
        if not f.is_file() or not is_hex64(want) or sha256_file(f) != want:
            raise AnalysisError("E_HASH_MISMATCH", f"frozen file {rel} differs from its frozen hash", path=rel, expected=want, actual=sha256_file(f))
    matrix_path, config_path = root / manifest["matrix_path"], root / manifest["config_path"]
    for rel in (manifest["matrix_path"], manifest["config_path"], manifest["analysis_script_path"], manifest["dependency_lock_path"]):
        if rel not in manifest["frozen_files"]:
            raise AnalysisError("E_MANIFEST", f"{rel} is not listed in frozen_files", path=rel)
    if mode == "formal":
        for rel in REQUIRED_DOCS:
            if rel not in manifest["frozen_files"]:
                raise AnalysisError("E_MANIFEST", f"the preregistration / specification text {rel} is not frozen (missing from frozen_files)", path=rel)
    running = sha256_file(SCRIPT_PATH)
    if running != manifest["frozen_files"][manifest["analysis_script_path"]]:
        raise AnalysisError("E_HASH_MISMATCH", "the analysis script being run is not the frozen one", path=manifest["analysis_script_path"],
                            expected=manifest["frozen_files"][manifest["analysis_script_path"]], actual=running)
    if sha256_file(matrix_path) != MATRIX_SHA256:
        raise AnalysisError("E_HASH_MISMATCH", "matrix.csv is not the registered file", path=manifest["matrix_path"], expected=MATRIX_SHA256, actual=sha256_file(matrix_path))
    rows = load_matrix(matrix_path)
    names = [r["run_name"] for r in rows]
    combos = {(r["arch"], r["n_step"], r["seed"]) for r in rows}
    if len(set(names)) != 30 or combos != {(a, n, s) for a in ARCHS for n in NSTEPS for s in SEEDS}:
        raise AnalysisError("E_RUN_SET", "matrix.csv is not the 3 x 2 x 5 design")
    for b in range(5):
        block = rows[6 * b: 6 * b + 6]
        if {r["seed"] for r in block} != {SEEDS[b]} or len({(r["arch"], r["n_step"]) for r in block}) != 6:
            raise AnalysisError("E_RUN_SET", f"matrix rows {6 * b + 1}-{6 * b + 6} are not the six distinct configurations of one training seed")
    frozen = _obj(read_json(config_path, manifest["config_path"]), manifest["config_path"], None, "$")
    for k in FROZEN_REQUIRED:
        _req(frozen, k, manifest["config_path"], None)
    if not isinstance(frozen["hard_enabled"], bool):
        raise AnalysisError("E_CONFIG_MISMATCH", "hard_enabled must be declared true/false in the frozen configuration", path=manifest["config_path"], actual=frozen["hard_enabled"])
    for key, want in (("val_seeds", list(VAL_SEEDS)), ("test_seeds", list(TEST_SEEDS)), ("eval_episodes", 50), ("final_eval_device", "cpu"),
                      ("final_eval_threads", 1), ("max_episode_steps", 1000), ("train_scenario", "standard"),
                      ("eps_start", 1.0), ("eps_end", 0.05), ("eps_frac", 0.4), ("tau", 0.01), ("grad_clip", 10.0)):
        if frozen[key] != want or type(frozen[key]) is bool:
            raise AnalysisError("E_CONFIG_MISMATCH", f"frozen config {key} differs from the preregistered value", path=manifest["config_path"], expected=want if key not in ("val_seeds", "test_seeds") else "range", actual=frozen[key] if key not in ("val_seeds", "test_seeds") else "array")
    if frozen["code_commit"] != manifest["code_commit"]:
        raise AnalysisError("E_CONFIG_MISMATCH", "frozen config code_commit differs from the manifest", expected=manifest["code_commit"], actual=frozen["code_commit"])
    want_status = "frozen" if mode == "formal" else "synthetic"
    if frozen.get("status") != want_status:
        raise AnalysisError("E_CONFIG_MISMATCH", f"{mode} mode needs a frozen configuration with status {want_status!r} (a draft is never a formal input)",
                            path=manifest["config_path"], json_path="$.status", expected=want_status, actual=frozen.get("status"))
    hard = frozen["hard_enabled"]
    frozen_sha = sha256_file(config_path)
    # --- seal
    seal_path = root / manifest["seal_path"]
    if not seal_path.is_file():
        raise AnalysisError("E_MISSING_FILE", "evaluation seal not found", path=manifest["seal_path"])
    seal = _obj(read_json(seal_path, manifest["seal_path"]), manifest["seal_path"], None, "$")
    if (seal.get("schema_version") != "prereg-seal-1" or seal.get("synthetic") is not (mode == "synthetic")
            or seal.get("freeze_manifest_sha256") != sha256_file(manifest_path) or seal.get("all_training_complete") is not True
            or seal.get("all_checkpoint_checks_passed") is not True or seal.get("runs") != names or not isinstance(seal.get("attempts"), list)
            or not isinstance(seal.get("files"), dict)):
        raise AnalysisError("E_MANIFEST", "evaluation seal is not a valid seal for this manifest / mode / run list", path=manifest["seal_path"])
    for i, a in enumerate(seal["attempts"]):  # each failed attempt is an object about one of the 30 runs; the report lists them one by one
        jp = f"$.attempts[{i}]"
        a = _obj(a, manifest["seal_path"], None, jp)
        if _str(_req(a, "run", manifest["seal_path"], None, jp), manifest["seal_path"], None, f"{jp}.run") not in names:
            raise AnalysisError("E_MANIFEST", "an archived attempt names a run that is not in the matrix", path=manifest["seal_path"], json_path=f"{jp}.run", actual=a["run"])
        if not is_int(_req(a, "attempt", manifest["seal_path"], None, jp)) or a["attempt"] < 1:
            raise AnalysisError("E_FIELD_TYPE", "attempt must be an integer >= 1", path=manifest["seal_path"], json_path=f"{jp}.attempt", actual=a["attempt"])
        _str(_req(a, "reason", manifest["seal_path"], None, jp), manifest["seal_path"], None, f"{jp}.reason")
    declared = manifest.get("deviations", [])  # optional: deviations declared in the freeze record; the script never invents any
    if not isinstance(declared, list):
        raise AnalysisError("E_FIELD_TYPE", "deviations must be an array", path=manifest_path.name, json_path="$.deviations", actual=type(declared).__name__)
    for i, dv in enumerate(declared):
        jp = f"$.deviations[{i}]"
        dv = _obj(dv, manifest_path.name, None, jp)
        for k in ("id", "description", "source"):
            _str(_req(dv, k, manifest_path.name, None, jp), manifest_path.name, None, f"{jp}.{k}")
    rels = ["config.json", "summary.json", "last/standard.json", "best/standard.json"] + (["last/hard.json"] if hard else [])
    required = {f"{n}/{rel}" for n in names for rel in rels}
    if set(seal["files"]) != required:
        raise AnalysisError("E_MANIFEST", "seal files differ from the required file set", path=manifest["seal_path"],
                            expected=sorted(required - set(seal["files"]))[:3], actual=sorted(set(seal["files"]) - required)[:3])
    # --- step 2: existence of everything, no extra runs, undeclared hard
    if not input_root.is_dir():
        raise AnalysisError("E_MISSING_FILE", "input root not found", path=str(input_root.name))
    extra = sorted(p.name for p in input_root.iterdir() if p.is_dir() and p.name.startswith("prereg") and p.name not in names)
    if extra:
        raise AnalysisError("E_RUN_SET", f"unexpected preregistered run directories: {extra}", actual=extra, expected=names[:1])
    for n in names:
        for rel in rels:
            if not (input_root / n / rel).is_file():
                raise AnalysisError("E_MISSING_FILE", f"required file {n}/{rel} not found", path=f"{n}/{rel}", run_name=n)
        if not hard and (input_root / n / "last" / "hard.json").exists():
            raise AnalysisError("E_UNDECLARED_HARD", "last/hard.json exists but hard_enabled is false", path=f"{n}/last/hard.json", run_name=n)
    for key, want in seal["files"].items():
        got = sha256_file(input_root / key)
        if got != want:
            raise AnalysisError("E_HASH_MISMATCH", f"{key} differs from the sealed hash", path=key, run_name=key.split("/")[0], expected=want, actual=got)
    # --- step 3: parse everything (duplicate keys, bad JSON, non-finite numbers anywhere in the tree)
    docs = {}
    for n in names:
        for rel in rels:
            docs[f"{n}/{rel}"] = read_json(input_root / n / rel, f"{n}/{rel}", n)
    # --- step 4: config / summary / meta
    ctx = {"manifest": manifest, "root": root, "rows": rows, "frozen": frozen, "frozen_sha": frozen_sha, "hard": hard, "seal": seal,
           "seal_sha": sha256_file(seal_path), "docs": docs, "names": names, "rels": rels, "mode": mode, "input_root": input_root,
           "manifest_sha": sha256_file(manifest_path)}
    check_run_documents(ctx)
    # --- steps 5-7: records
    Y, files = check_records(ctx)
    ctx["Y"], ctx["files"] = Y, files
    return ctx


def _req(d, k, rel, name, where="$"):
    """d[k] for a required field; a non-object container is a schema error (with the JSON path), a missing key a required-field error."""
    if not isinstance(d, dict):
        raise AnalysisError("E_SCHEMA", f"{rel}: expected a JSON object at {where}", path=rel, run_name=name, json_path=where, expected="object", actual=type(d).__name__)
    if k not in d:
        raise AnalysisError("E_REQUIRED_FIELD", f"{rel} lacks field {k!r} at {where}", path=rel, run_name=name, json_path=f"{where}.{k}", expected=k)
    return d[k]


def _int(v, rel, name, jp):
    """Integer-valued identity / count fields must be JSON integers: no floats (20000.0), no booleans, no strings."""
    if not is_int(v):
        raise AnalysisError("E_FIELD_TYPE", f"{rel}: {jp} must be a JSON integer", path=rel, run_name=name, json_path=jp, expected="integer", actual=v)
    return v


def _str(v, rel, name, jp):
    if not isinstance(v, str):
        raise AnalysisError("E_FIELD_TYPE", f"{rel}: {jp} must be a string", path=rel, run_name=name, json_path=jp, expected="string", actual=v)
    return v


def _obj(v, rel, name, jp):
    if not isinstance(v, dict):
        raise AnalysisError("E_SCHEMA", f"{rel}: {jp} must be a JSON object", path=rel, run_name=name, json_path=jp, expected="object", actual=type(v).__name__)
    return v


def check_run_documents(ctx):
    rows, frozen, docs, hard = ctx["rows"], ctx["frozen"], ctx["docs"], ctx["hard"]
    inits = {}
    for r in rows:
        n = r["run_name"]
        cfg, summ = docs[f"{n}/config.json"], docs[f"{n}/summary.json"]
        crel, srel = f"{n}/config.json", f"{n}/summary.json"
        for col in CSV_COLUMNS:
            v = _req(cfg, col, crel, n)
            if type(v) is not type(r[col]):  # strict: seed 100.0 is not the integer 100, "true" is not true
                raise AnalysisError("E_FIELD_TYPE", f"config {col} has the wrong type", path=crel, run_name=n, json_path=f"$.{col}", expected=r[col], actual=v)
            if v != r[col]:
                raise AnalysisError("E_CONFIG_MISMATCH", f"config {col} differs from matrix.csv", path=crel, run_name=n, expected=r[col], actual=v)
        for k in FROZEN_REQUIRED:
            v = _req(cfg, k, crel, n)
            if k == "code_commit":
                continue
            if v != frozen[k] or type(v) is not type(frozen[k]):
                raise AnalysisError("E_CONFIG_MISMATCH", f"config {k} differs from the frozen configuration", path=crel, run_name=n, expected=frozen[k] if not isinstance(frozen[k], list) else "array", actual=v if not isinstance(v, list) else "array")
        if _req(cfg, "code_commit", crel, n) != ctx["manifest"]["code_commit"]:
            raise AnalysisError("E_CONFIG_MISMATCH", "config code_commit differs from the frozen commit", path=crel, run_name=n, expected=ctx["manifest"]["code_commit"], actual=cfg["code_commit"])
        if _req(cfg, "frozen_config_sha256", crel, n) != ctx["frozen_sha"]:
            raise AnalysisError("E_CONFIG_MISMATCH", "config frozen_config_sha256 differs from the frozen configuration file hash", path=crel, run_name=n, expected=ctx["frozen_sha"], actual=cfg["frozen_config_sha256"])
        if cfg.get("run_name") != n:
            raise AnalysisError("E_CONFIG_MISMATCH", "config run_name differs", path=crel, run_name=n, expected=n, actual=cfg.get("run_name"))
        # summary
        if _req(summ, "run_name", srel, n) != n:
            raise AnalysisError("E_METADATA_MISMATCH", "summary run_name differs", path=srel, run_name=n, expected=n, actual=summ["run_name"])
        tot = _req(summ, "total_env_steps", srel, n)
        if not is_int(tot):
            raise AnalysisError("E_FIELD_TYPE", "total_env_steps must be an integer", path=srel, run_name=n, actual=tot)
        if tot != 300000:
            raise AnalysisError("E_TRAIN_BUDGET", "total_env_steps != 300000", path=srel, run_name=n, expected=300000, actual=tot)
        rep = _req(summ, "replay", srel, n)
        size = _req(rep, "size", srel, n, "$.replay")
        if not is_int(size) or not 0 <= size <= 100000:
            raise AnalysisError("E_FIELD_TYPE", "replay.size must be an integer in [0, 100000]", path=srel, run_name=n, actual=size)
        upd = _req(summ, "actual_updates", srel, n)
        if not is_int(upd) or upd < 0:
            raise AnalysisError("E_FIELD_TYPE", "actual_updates must be a non-negative integer", path=srel, run_name=n, actual=upd)
        vs, ve = _req(summ, "validation_steps", srel, n), _req(summ, "validation_episodes_each", srel, n)
        if not isinstance(vs, list):
            raise AnalysisError("E_FIELD_TYPE", "validation_steps must be an array", path=srel, run_name=n, json_path="$.validation_steps", actual=type(vs).__name__)
        for i, x in enumerate(vs):
            _int(x, srel, n, f"$.validation_steps[{i}]")
        _int(ve, srel, n, "$.validation_episodes_each")
        if vs != VALIDATION_STEPS or ve != 50:
            raise AnalysisError("E_VALIDATION_SCHEDULE", "validation must be exactly the 15 steps 20000..300000, 50 episodes each", path=srel, run_name=n, expected=VALIDATION_STEPS, actual=[vs, ve] if vs == VALIDATION_STEPS else vs)
        init = _req(summ, "initial_state_dict_sha256", srel, n)
        if not is_hex64(init):
            raise AnalysisError("E_FIELD_TYPE", "initial_state_dict_sha256 must be 64 lower-case hex characters", path=srel, run_name=n, actual=init)
        cks = _req(summ, "checkpoints", srel, n)
        for label in ("last", "best"):
            c = _req(cks, label, srel, n, "$.checkpoints")
            st, w = _req(c, "step", srel, n, f"$.checkpoints.{label}"), _req(c, "weights_sha256", srel, n, f"$.checkpoints.{label}")
            if not is_int(st) or not is_hex64(w):
                raise AnalysisError("E_FIELD_TYPE", f"checkpoints.{label} needs an integer step and a 64-hex weights hash", path=srel, run_name=n, actual=[st, w])
        if cks["last"]["step"] != 300000:
            raise AnalysisError("E_TRAIN_BUDGET", "last checkpoint step must be 300000", path=srel, run_name=n, expected=300000, actual=cks["last"]["step"])
        if cks["best"]["step"] not in VALIDATION_STEPS:
            raise AnalysisError("E_VALIDATION_SCHEDULE", "best checkpoint step is not one of the 15 validation steps", path=srel, run_name=n, actual=cks["best"]["step"])
        inits.setdefault((r["arch"], r["seed"]), {})[r["n_step"]] = init
        # evaluation meta
        for rel in ctx["rels"][2:]:
            doc = docs[f"{n}/{rel}"]
            erel = f"{n}/{rel}"
            if not isinstance(doc, dict) or _req(doc, "schema_version", erel, n) != "prereg-eval-1":
                raise AnalysisError("E_SCHEMA", "evaluation file must be a prereg-eval-1 wrapper object", path=erel, run_name=n)
            meta = _obj(_req(doc, "meta", erel, n), erel, n, "$.meta")
            label, scen = rel.split("/")[0], rel.split("/")[1].removesuffix(".json")
            want = {"synthetic": ctx["mode"] == "synthetic", "run_name": n, "arch": r["arch"], "n_step": r["n_step"], "train_seed": r["seed"],
                    "checkpoint": label, "checkpoint_step": cks[label]["step"], "weights_sha256": cks[label]["weights_sha256"],
                    "code_commit": ctx["manifest"]["code_commit"], "scenario": scen, "device": frozen["final_eval_device"],
                    "torch_threads": frozen["final_eval_threads"]}
            for k, v in want.items():
                got = _req(meta, k, erel, n, "$.meta")
                if got != v or type(got) is not type(v):
                    raise AnalysisError("E_METADATA_MISMATCH", f"meta.{k} differs from what the run / path / freeze requires", path=erel, run_name=n, expected=v, actual=got)
            if "reused_from" in meta and (meta["reused_from"] != "last" or label != "best" or cks["best"]["weights_sha256"] != cks["last"]["weights_sha256"]):
                raise AnalysisError("E_METADATA_MISMATCH", "reused_from is only valid for a best file whose weights equal last", path=erel, run_name=n, actual=meta["reused_from"])
    for (a, s), d in inits.items():
        if d.get(1) != d.get(3):
            raise AnalysisError("E_INIT_PAIR_MISMATCH", f"n_step=1 and n_step=3 of {a} seed {s} did not start from the same initial weights",
                                run_name=f"prereg_{a}_n1_s{s}", expected=d.get(3), actual=d.get(1))


def check_records(ctx):
    rows, docs, hard = ctx["rows"], ctx["docs"], ctx["hard"]
    kinds = [("last_standard", "last/standard.json"), ("best_standard", "best/standard.json")] + ([("last_hard", "last/hard.json")] if hard else [])
    Y = {q: np.zeros((3, 2, 5, 300), dtype=np.int64) for q, _ in kinds}
    aux = {q: {k: np.zeros((3, 2, 5, 300), dtype=np.int64) for k in ("died", "won", "truncated", "steps")} for q, _ in kinds}
    files = {}
    for r in rows:  # ANALYSIS_SPEC 2.3: files in CSV run order, and within a run last/standard, best/standard, last/hard
        for q, rel in kinds:
            n = r["run_name"]
            erel = f"{n}/{rel}"
            recs = _req(docs[erel], "records", erel, n)
            if not isinstance(recs, list):
                raise AnalysisError("E_SCHEMA", "records must be an array", path=erel, run_name=n, json_path="$.records", actual=type(recs).__name__)
            if len(recs) != 300:
                raise AnalysisError("E_EPISODE_COUNT", "each evaluation file needs exactly 300 records", path=erel, run_name=n, expected=300, actual=len(recs))
            for i, rec in enumerate(recs):
                ctxd = dict(path=erel, run_name=n, record_index=i)
                if not isinstance(rec, dict):
                    raise AnalysisError("E_FIELD_TYPE", "record must be an object", **ctxd)
                for k in ("seed", "score", "steps", "died", "won", "truncated"):
                    if k not in rec:
                        raise AnalysisError("E_REQUIRED_FIELD", f"record lacks {k!r}", expected=k, **ctxd)
                seed, score, steps = rec["seed"], rec["score"], rec["steps"]
                if not is_int(seed) or not is_int(steps):
                    raise AnalysisError("E_FIELD_TYPE", "seed and steps must be JSON integers", seed=seed if is_int(seed) else None, actual=[seed, steps], **ctxd)
                if isinstance(score, bool) or not isinstance(score, (int, float)):
                    raise AnalysisError("E_FIELD_TYPE", "score must be a number", seed=seed, actual=score, **ctxd)
                if isinstance(score, float) and score != int(score):  # finite but not a whole number of pellets: outside the legal score set
                    raise AnalysisError("E_SCORE_RANGE", "score must be a whole number of pellets in [0, 377]", seed=seed, expected="integer 0..377", actual=score, **ctxd)
                for k in ("died", "won", "truncated"):
                    if not isinstance(rec[k], bool):
                        raise AnalysisError("E_FIELD_TYPE", f"{k} must be a JSON boolean", seed=seed, actual=rec[k], **ctxd)
                score = int(score)
                if not 0 <= score <= 377:
                    raise AnalysisError("E_SCORE_RANGE", "score outside [0, 377]", seed=seed, expected="0..377", actual=score, **ctxd)
                if not 1 <= steps <= 1000:
                    raise AnalysisError("E_STEPS_RANGE", "steps outside [1, 1000]", seed=seed, expected="1..1000", actual=steps, **ctxd)
                if rec["won"] and score != 377:
                    raise AnalysisError("E_WON_SCORE", "won=true requires score 377", seed=seed, expected=377, actual=score, **ctxd)
                flags = [rec["died"], rec["won"], rec["truncated"]]
                if sum(flags) != 1 or (rec["truncated"] and steps != 1000):
                    raise AnalysisError("E_END_FLAGS", "exactly one of died/won/truncated must be true, and truncated requires steps == 1000", seed=seed, actual={"died": rec["died"], "won": rec["won"], "truncated": rec["truncated"], "steps": steps}, **ctxd)
            seeds = [rec["seed"] for rec in recs]
            dups = sorted({s for s in seeds if seeds.count(s) > 1})
            if dups:
                raise AnalysisError("E_DUPLICATE_SEED", f"duplicate test seed(s) {dups}", path=erel, run_name=n, seed=dups[0], actual=dups)
            sset = set(seeds)
            mixed = sorted(sset & set(VAL_SEEDS))
            if mixed:
                raise AnalysisError("E_VAL_TEST_MIXED", f"validation seed(s) {mixed} found among the test records (validation partition 21000-21049)", path=erel, run_name=n, seed=mixed[0], actual=mixed)
            for label, rng in RESERVED.items():
                hit = sorted(sset & set(rng))
                if hit:
                    raise AnalysisError("E_RESERVED_SEED_MIXED", f"seed(s) {hit} belong to the reserved partition {label}", path=erel, run_name=n, seed=hit[0], actual=hit)
            if sset != set(TEST_SEEDS):
                raise AnalysisError("E_TEST_SEED_SET", "test seeds are not exactly 30000..30299", path=erel, run_name=n,
                                    expected={"missing": sorted(set(TEST_SEEDS) - sset)}, actual={"unexpected": sorted(sset - set(TEST_SEEDS))})
            order = np.argsort(np.asarray(seeds))  # align by seed, never by file row
            ai, ni, si = ARCHS.index(r["arch"]), NSTEPS.index(r["n_step"]), SEEDS.index(r["seed"])
            files[erel] = sha256_file(ctx["input_root"] / erel)
            Y[q][ai, ni, si] = np.asarray([int(recs[j]["score"]) for j in order], dtype=np.int64)
            for k in ("died", "won", "truncated"):
                aux[q][k][ai, ni, si] = np.asarray([int(recs[j][k]) for j in order], dtype=np.int64)
            aux[q]["steps"][ai, ni, si] = np.asarray([int(recs[j]["steps"]) for j in order], dtype=np.int64)
    ctx["aux"] = aux
    return Y, files


# ----------------------------------------------------------------------------------------------- statistics
def vec_stats(num, den, metric_id, formula_id, sources, seeds=SEEDS):
    """5 training-seed values given as integer numerators over `den`.  Exact arithmetic where the decision depends on it."""
    num = [int(x) for x in num]
    n = len(num)
    mean_f = Fraction(sum(num), den * n)
    var_f = Fraction(sum((n * x - sum(num)) ** 2 for x in num), den * den * n * n * (n - 1))
    sd = math.sqrt(var_f) if var_f > 0 else 0.0
    mean = float(mean_f)
    se = sd / math.sqrt(n)
    return {"metric_id": metric_id, "training_seeds": list(seeds), "raw_values": [x / den for x in num], "integer_numerators": num,
            "denominator": den, "mean": mean, "sd_ddof1": sd, "se": se, "positive_count": sum(x > 0 for x in num), "zero_count": sum(x == 0 for x in num),
            "negative_count": sum(x < 0 for x in num), "ci95_t": [mean - T95 * se, mean + T95 * se], "ci975_t": [mean - T975 * se, mean + T975 * se],
            "ci95_cross_bootstrap": None, "degenerate": sd == 0.0, "source_metric_ids": sources, "formula_id": formula_id}


def interval_sign(ci):
    return "positive" if ci[0] > 0 else "negative" if ci[1] < 0 else "contains_zero"


def magnitude_label(ci, bound, two_sided):
    lo, hi = ci
    if two_sided:  # H2
        if lo > bound or hi < -bound:
            return "supported"
        return "refuted" if lo > -bound and hi < bound else "uncertain"
    return "supported" if lo > bound else "refuted" if hi < bound else "uncertain"  # H1


def sign_test(num):
    pos, neg = sum(x > 0 for x in num), sum(x < 0 for x in num)
    neff = pos + neg
    if neff == 0:
        return {"n_effective": 0, "k_positive": 0, "zero_count": len(num) - neff, "numerator": 1, "denominator": 1, "p": 1.0, "status": "no_effective_samples", "p_lt_0_05": False}
    numer = sum(math.comb(neff, j) for j in range(pos, neff + 1))
    den = 2 ** neff
    return {"n_effective": neff, "k_positive": pos, "zero_count": len(num) - neff, "numerator": numer, "denominator": den, "p": numer / den, "status": "ok", "p_lt_0_05": numer * 20 < den}


def bootstrap_stream():
    """Yield (I, J) for B rounds in the contracted order, and accumulate the SHA-256 of the index bytes."""
    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    h = hashlib.sha256()
    for _ in range(B):
        I = rng.integers(0, 5, size=5, dtype=np.int64, endpoint=False)
        J = rng.integers(0, 300, size=300, dtype=np.int64, endpoint=False)
        h.update(I.astype("<u4").tobytes())
        h.update(J.astype("<u4").tobytes())
        yield I, J, h


def contrasts_for(Y, endpoints):
    """name -> int64 array (5, 300) of per-episode signed contrasts (training seed x test episode)."""
    out = {}
    ia = {a: i for i, a in enumerate(ARCHS)}
    for q in endpoints:
        z = Y[q]
        d = {a: z[ia[a], 0] - z[ia[a], 1] for a in ARCHS}  # n=1 minus n=3
        for a in ARCHS:
            out[f"{q}.d.{a}"] = d[a]
        out[f"{q}.c"] = d["res8"] - d["cnn2"]
        out[f"{q}.u"] = d["res4"] - d["cnn2"]
        out[f"{q}.v"] = d["res8"] - d["res4"]
        out[f"{q}.r"] = z[ia["res8"], 0] - z[ia["cnn2"], 0]
    if "best_standard" in Y:
        zb, zl = Y["best_standard"], Y["last_standard"]
        for a in ARCHS:
            for ni, n in enumerate(NSTEPS):
                out[f"best_minus_last.b.{a}.n{n}"] = zb[ia[a], ni] - zl[ia[a], ni]
        for a in ARCHS:
            out[f"best_minus_last.g.{a}"] = (zb[ia[a], 0] - zb[ia[a], 1]) - (zl[ia[a], 0] - zl[ia[a], 1])
    return out


def run_bootstrap(contrasts):
    names = list(contrasts)
    W = np.stack([contrasts[k] for k in names])  # (K, 5, 300)
    vals = np.zeros((B, len(names)), dtype=np.float64)
    h = None
    for b, (I, J, h) in enumerate(bootstrap_stream()):
        vals[b] = W[:, I][:, :, J].sum(axis=(1, 2)) / 1500  # integer sum, one division
    q = np.quantile(vals, [0.025, 0.975], axis=0, method="linear")
    return names, vals, {k: [float(q[0, i]), float(q[1, i])] for i, k in enumerate(names)}, h.hexdigest()


def analyze_arrays(ctx):
    Y = ctx["Y"]
    endpoints = [q for q in ENDPOINTS if q in Y]
    ia = {a: i for i, a in enumerate(ARCHS)}
    S = {q: Y[q].sum(axis=3) for q in endpoints}  # (3, 2, 5) int64
    contrasts = contrasts_for(Y, endpoints)
    names, vals, boot_ci, index_sha = run_bootstrap(contrasts)
    if index_sha != EXPECTED_INDEX_SHA:
        raise AnalysisError("E_MANIFEST", "the bootstrap index stream differs from the contracted one (numpy version / generator)", expected=EXPECTED_INDEX_SHA, actual=index_sha)
    src_runs = {(r["arch"], r["n_step"], r["seed"]): r["run_name"] for r in ctx["rows"]}
    ep = {}
    for q in endpoints:
        kind = {"last_standard": "last/standard.json", "best_standard": "best/standard.json", "last_hard": "last/hard.json"}[q]
        e = {"model_metrics": {}, "config_summaries": {}, "effects": {}, "rates_steps": {}}
        for a in ARCHS:
            for ni, n in enumerate(NSTEPS):
                mid = f"{q}.m.{a}.n{n}"
                st = vec_stats([S[q][ia[a], ni, si] for si in range(5)], 300, mid, "m_score_sum_over_300",
                               [{"run_name": src_runs[(a, n, s)], "file": f"{src_runs[(a, n, s)]}/{kind}", "sha256": ctx["files"][f"{src_runs[(a, n, s)]}/{kind}"],
                                 "test_seeds": "30000..30299", "integer_score_sum": int(S[q][ia[a], ni, si])} for si, s in enumerate(SEEDS)])
                e["model_metrics"][f"{a}.n{n}"] = st
                a_ = ctx["aux"][q]
                rates = {}
                for k in ("died", "won", "truncated", "steps"):
                    per = [int(a_[k][ia[a], ni, si].sum()) for si in range(5)]
                    key = k + ("_rate" if k != "steps" else "_mean")
                    rate_stat = vec_stats(per, 300, f"{q}.{key}.{a}.n{n}", f"{k}_sum_over_300", [mid])
                    rates[key] = {"per_model": rate_stat["raw_values"], "mean": rate_stat["mean"], "sd_ddof1": rate_stat["sd_ddof1"],
                                  "metric_id": rate_stat["metric_id"], "formula_id": rate_stat["formula_id"], "training_seeds": rate_stat["training_seeds"],
                                  "integer_numerators": per, "denominator": 300, "record_field": k, "source_metric_ids": [mid],
                                  "sources": [{"run_name": src_runs[(a, n, s)], "file": f"{src_runs[(a, n, s)]}/{kind}",
                                               "sha256": ctx["files"][f"{src_runs[(a, n, s)]}/{kind}"], "test_seeds": "30000..30299",
                                               "integer_sum": per[si], "episodes": 300} for si, s in enumerate(SEEDS)]}
                e["rates_steps"][f"{a}.n{n}"] = rates
        d = {a: [int(S[q][ia[a], 0, si] - S[q][ia[a], 1, si]) for si in range(5)] for a in ARCHS}
        def fin(key, num, fid, srcs):
            st = vec_stats(num, 300, f"{q}.{key}", fid, srcs)
            st["ci95_cross_bootstrap"] = boot_ci[f"{q}.{key}"]
            return st
        dd = {a: fin(f"d.{a}", d[a], "d_n1_minus_n3", [f"{q}.m.{a}.n1", f"{q}.m.{a}.n3"]) for a in ARCHS}
        e["effects"]["d"] = dd
        e["effects"]["c"] = fin("c", [d["res8"][i] - d["cnn2"][i] for i in range(5)], "c_d_res8_minus_d_cnn2", [f"{q}.d.res8", f"{q}.d.cnn2"])
        e["effects"]["u"] = fin("u", [d["res4"][i] - d["cnn2"][i] for i in range(5)], "u_d_res4_minus_d_cnn2", [f"{q}.d.res4", f"{q}.d.cnn2"])
        e["effects"]["v"] = fin("v", [d["res8"][i] - d["res4"][i] for i in range(5)], "v_d_res8_minus_d_res4", [f"{q}.d.res8", f"{q}.d.res4"])
        r = fin("r", [int(S[q][ia["res8"], 0, si] - S[q][ia["cnn2"], 0, si]) for si in range(5)], "r_n1_res8_minus_cnn2", [f"{q}.m.res8.n1", f"{q}.m.cnn2.n1"])
        r["label"] = "res8_higher" if r["ci95_t"][0] > 0 else "cnn2_higher" if r["ci95_t"][1] < 0 else "order_uncertain"
        e["effects"]["r"] = r
        for key, st in [(f"d.{a}", dd[a]) for a in ARCHS] + [("c", e["effects"]["c"]), ("u", e["effects"]["u"]), ("v", e["effects"]["v"])]:
            lab = {"interval_sign_t95": interval_sign(st["ci95_t"]), "interval_sign_bootstrap95": interval_sign(st["ci95_cross_bootstrap"])}
            lab["method_sensitive_zero"] = lab["interval_sign_t95"] != lab["interval_sign_bootstrap95"]
            st["sensitivity"] = lab
        e["config_summaries"] = {f"{a}.n{n}": {"mean": e["model_metrics"][f"{a}.n{n}"]["mean"], "sd_ddof1": e["model_metrics"][f"{a}.n{n}"]["sd_ddof1"],
                                               "source_metric_id": f"{q}.m.{a}.n{n}"} for a in ARCHS for n in NSTEPS}
        ep[q] = e
    # best minus last, selection effect
    expl = {"best_minus_last": {"b": {}, "g": {}}}
    if "best_standard" in Y:
        for a in ARCHS:
            for ni, n in enumerate(NSTEPS):
                st = vec_stats([S["best_standard"][ia[a], ni, si] - S["last_standard"][ia[a], ni, si] for si in range(5)], 300, f"best_minus_last.b.{a}.n{n}", "b_m_best_minus_m_last",
                               [f"best_standard.m.{a}.n{n}", f"last_standard.m.{a}.n{n}"])
                st["ci95_cross_bootstrap"] = boot_ci[f"best_minus_last.b.{a}.n{n}"]
                st["best_selected_steps"] = [ctx["docs"][f"{src_runs[(a, n, s)]}/summary.json"]["checkpoints"]["best"]["step"] for s in SEEDS]
                expl["best_minus_last"]["b"][f"{a}.n{n}"] = st
            dl, db = [int(S["last_standard"][ia[a], 0, si] - S["last_standard"][ia[a], 1, si]) for si in range(5)], [int(S["best_standard"][ia[a], 0, si] - S["best_standard"][ia[a], 1, si]) for si in range(5)]
            st = vec_stats([db[i] - dl[i] for i in range(5)], 300, f"best_minus_last.g.{a}", "g_d_best_minus_d_last", [f"best_standard.d.{a}", f"last_standard.d.{a}"])
            st["ci95_cross_bootstrap"] = boot_ci[f"best_minus_last.g.{a}"]
            st["direction_of_mean"] = "positive" if sum(db) - sum(dl) > 0 else "negative" if sum(db) - sum(dl) < 0 else "zero"
            expl["best_minus_last"]["g"][a] = st
        expl["best_minus_last"]["selection_device"] = ctx["frozen"]["validation_device"]
        expl["best_minus_last"]["test_device"] = ctx["frozen"]["final_eval_device"]
    # primary decisions (last_standard only)
    L = ep["last_standard"]["effects"]
    d_res4, c = L["d"]["res4"], L["c"]
    h1 = magnitude_label(d_res4["ci975_t"], 10, False)
    h2 = magnitude_label(c["ci975_t"], 10, True)
    h1b, h2b = magnitude_label(d_res4["ci95_cross_bootstrap"], 10, False), magnitude_label(c["ci95_cross_bootstrap"], 10, True)
    prim = {"H1": {"label": h1, "positive_gain_refuted": bool(h1 == "refuted" and d_res4["ci975_t"][1] < 0), "ci975_t": d_res4["ci975_t"], "metric_id": d_res4["metric_id"],
                   "bootstrap95_magnitude_check": h1b, "magnitude_check_differs": h1b != h1,
                   "note": "bootstrap95 vs t97.5 are different coverage levels: not a same-level re-test"},
            "H2": {"label": h2, "ci975_t": c["ci975_t"], "metric_id": c["metric_id"], "bootstrap95_magnitude_check": h2b, "magnitude_check_differs": h2b != h2,
                   "note": "bootstrap95 vs t97.5 are different coverage levels: not a same-level re-test"},
            "direction_signal": {a: ("supported_signal" if (L["d"][a]["mean"] >= 10 and L["d"][a]["ci95_t"][0] > 0 and L["d"][a]["positive_count"] >= 4) else "insufficient_evidence") for a in ARCHS},
            "interaction_signal": ("supported_signal" if (abs(c["mean"]) >= 10 and (c["ci95_t"][0] > 0 or c["ci95_t"][1] < 0)) else "insufficient_evidence"),
            "res4_sign_test": {**sign_test(d_res4["integer_numerators"]), "source_metric_id": d_res4["metric_id"], "formula_id": "exact_one_sided_binomial_sign_test",
                               "integer_numerators": d_res4["integer_numerators"]}}
    prim["interaction_signal_bootstrap_contains_zero"] = bool(prim["interaction_signal"] == "supported_signal" and c["ci95_cross_bootstrap"][0] <= 0 <= c["ci95_cross_bootstrap"][1])
    prim["interaction_signal_method_sensitive_zero"] = prim["interaction_signal_bootstrap_contains_zero"]
    return ep, expl, prim, names, vals, index_sha


# ----------------------------------------------------------------------------------------------- output
def fnum(x, digits=4):
    return f"{x:.{digits}f}"


def vec_row(st):
    return ("| " + st["metric_id"] + " | " + " | ".join(fnum(v) for v in st["raw_values"]) + f" | {fnum(st['mean'])} | {fnum(st['sd_ddof1'])} | {st['positive_count']}/{st['zero_count']}/{st['negative_count']} | "
            f"[{fnum(st['ci95_t'][0])}, {fnum(st['ci95_t'][1])}] | [{fnum(st['ci95_cross_bootstrap'][0])}, {fnum(st['ci95_cross_bootstrap'][1])}] |")


def model_table(e):
    rows = ["| config | seed100 | seed101 | seed102 | seed103 | seed104 | mean | sd | death rate | win rate | truncated rate | steps |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, st in e["model_metrics"].items():
        rt = e["rates_steps"][key]
        rows.append(f"| {key} | " + " | ".join(fnum(v) for v in st["raw_values"]) + f" | {fnum(st['mean'])} | {fnum(st['sd_ddof1'])} | {fnum(rt['died_rate']['mean'])} | {fnum(rt['won_rate']['mean'])} | {fnum(rt['truncated_rate']['mean'])} | {fnum(rt['steps_mean']['mean'])} |")
    return rows


def rate_table(e):
    """Per-seed rates and mean steps (5 training-seed values each) with their integer numerators: the counts behind the configuration means."""
    rows = ["| config | quantity | seed100 | seed101 | seed102 | seed103 | seed104 | mean | sd | integer sums / 300 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for key, rt in e["rates_steps"].items():
        for qn, st in rt.items():
            rows.append(f"| {key} | {qn} | " + " | ".join(fnum(v) for v in st["per_model"]) + f" | {fnum(st['mean'])} | {fnum(st['sd_ddof1'])} | {st['integer_numerators']} |")
    return rows


def opt(f):
    return "n/a" if f["value"] is None else fnum(f["value"], 1)


def build_report(ctx, ep, expl, prim, index_sha, res, devs):
    mode = ctx["mode"]
    out = [f"# Architecture x n-step: analysis report (spec {SPEC_VERSION})", "",
           ("**SYNTHETIC DATA: this is an acceptance run of the analysis code, not a result.**" if mode == "synthetic" else "**FORMAL ANALYSIS of the frozen study.**"), "",
           "## 1. Frozen identity and integrity", f"- code commit `{ctx['manifest']['code_commit']}`; mode `{mode}`; hard scenario: {'enabled' if ctx['hard'] else 'not run'}",
           f"- 30 runs, {len(ctx['files'])} evaluation files x 300 unique test seeds 30000..30299, 15 initial-weight pairs equal, validation 15 x 50 each (all checked before any statistic)",
           f"- failed attempts archived (seal): {len(ctx['seal']['attempts'])}; bootstrap index SHA-256 `{index_sha}`",
           f"- deviations on record: {len(devs)}" + ("" if devs else " (none declared in the freeze manifest, none archived in the seal; the script does not infer deviations)")]
    out += [f"  - `{d['id']}` ({d['origin']}): {d['description']} [source: {d['source']}]" for d in devs]
    L = ep["last_standard"]
    out += ["", "## 2. Primary endpoint: last checkpoint, standard scenario (mean score per training seed)", ""] + model_table(L)
    hdr = ["| effect | seed100 | seed101 | seed102 | seed103 | seed104 | mean | sd | pos/zero/neg | 95% t | 95% cross-bootstrap |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    hdr_r = ["| effect | seed100 | seed101 | seed102 | seed103 | seed104 | mean | sd | pos/zero/neg | 95% t | 95% cross-bootstrap | order label |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    out += ["", "## 3. Effects n=1 minus n=3 (d), interactions (c primary; u, v auxiliary), last/standard", ""] + hdr
    for st in list(L["effects"]["d"].values()) + [L["effects"][k] for k in ("c", "u", "v")]:
        out.append(vec_row(st))
    out += ["", f"H1/H2 use the 97.5% two-sided t interval (t = {T975}); 95% intervals use t = {T95}.", ""]
    out += ["## 4. Formal labels", "", f"- **H1** (d.res4 >= 10): **{prim['H1']['label']}**; 97.5% t = [{fnum(prim['H1']['ci975_t'][0])}, {fnum(prim['H1']['ci975_t'][1])}]; positive gain refuted: {prim['H1']['positive_gain_refuted']}; bootstrap95 magnitude check: {prim['H1']['bootstrap95_magnitude_check']} (differs: {prim['H1']['magnitude_check_differs']}; a different coverage level, not a same-level re-test)",
            f"- **H2** (|c| >= 10): **{prim['H2']['label']}**; 97.5% t = [{fnum(prim['H2']['ci975_t'][0])}, {fnum(prim['H2']['ci975_t'][1])}]; bootstrap95 magnitude check: {prim['H2']['bootstrap95_magnitude_check']} (differs: {prim['H2']['magnitude_check_differs']})",
            "- direction signals: " + ", ".join(f"{a}: {v}" for a, v in prim["direction_signal"].items()), f"- interaction signal: {prim['interaction_signal']} (bootstrap95 contains zero: {prim['interaction_signal_bootstrap_contains_zero']})",
            "- sensitivity (interval sign, t95 vs bootstrap95): " + "; ".join(f"{k}: {v['sensitivity']['interval_sign_t95']}/{v['sensitivity']['interval_sign_bootstrap95']}" for k, v in {**{f'd.{a}': L['effects']['d'][a] for a in ARCHS}, 'c': L['effects']['c'], 'u': L['effects']['u'], 'v': L['effects']['v']}.items()),
            f"- Res4 one-sided exact sign test: N_eff={prim['res4_sign_test']['n_effective']}, K={prim['res4_sign_test']['k_positive']}, zeros={prim['res4_sign_test']['zero_count']}, p={prim['res4_sign_test']['numerator']}/{prim['res4_sign_test']['denominator']}={prim['res4_sign_test']['p']:.6g}, status={prim['res4_sign_test']['status']} (a direction test, not a mean test, and it does not decide H1/H2)", ""]
    out += ["## 5. Exploratory and secondary endpoints (all reported, none selected)", "", "### last_standard: per-seed death / win / truncation rates and mean steps", "", *rate_table(L), "",
            "### n=1: res8 minus cnn2 (r)", "", *hdr_r]
    for q in ep:
        out.append(vec_row(ep[q]["effects"]["r"]) + f" {ep[q]['effects']['r']['label']} |")
    for q in ep:
        if q != "last_standard":
            out += ["", f"### {q}: model scores, rates and steps", "", *model_table(ep[q]), "", f"### {q}: per-seed rates and mean steps", "", *rate_table(ep[q]),
                    "", f"### {q}: d / c / u / v", "", *hdr] + [vec_row(st) for st in list(ep[q]["effects"]["d"].values()) + [ep[q]["effects"][k] for k in ("c", "u", "v")]]
    if "best_minus_last" in expl and expl["best_minus_last"]["b"]:
        out += ["", "### best minus last (b per configuration) and change of the n-step effect (g)", f"(selection device {expl['best_minus_last']['selection_device']}, test device {expl['best_minus_last']['test_device']}; best-selected validation steps per configuration are in analysis.json)", "", *hdr]
        out += [vec_row(st) for st in expl["best_minus_last"]["b"].values()] + [vec_row(st) for st in expl["best_minus_last"]["g"].values()]
    if not ctx["hard"]:
        out += ["", "hard scenario: not run (frozen configuration)."]
    out += ["", "## 6. Resource records (from summary.json; n/a = null in the file, reason in analysis.json)", "",
            "| run | replay.size at end | actual_updates | best step | minutes | peak working set MB | peak commit MB | CUDA max allocated MB | CUDA max reserved MB | failed attempts |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res:
        f = r["resources"]
        out.append(f"| {r['run_name']} | {r['replay_size']} | {r['actual_updates']} | {r['best_step']} | {opt(f['minutes'])} | {opt(f['peak_working_set_mb'])} | {opt(f['peak_commit_mb'])} | "
                   f"{opt(f['cuda_max_allocated_mb'])} | {opt(f['cuda_max_reserved_mb'])} | {len(r['attempts'])} |")
    att = [a for r in res for a in r["attempts"]]
    if att:
        out += ["", "Archived failed attempts (evaluation seal):", "", "| run | attempt | archived (UTC) | reason | files archived |", "|---|---|---|---|---|"]
        out += [f"| {a['run']} | {a['attempt']} | {a.get('archived_utc', 'n/a')} | {a['reason']} | {len(a['files']) if isinstance(a.get('files'), list) else 'n/a'} |" for a in att]
    else:
        out += ["", "No failed attempts were archived."]
    out += ["", "replay.size is the buffer occupancy at the end (capped at 100000), not cumulative inserts; n=3 holds up to 16 pending tail items with 8 active environments.", "",
            "## 7. Number sources and limits",
            "- Statistic objects in analysis.json carry `metric_id`, `formula_id`, `source_metric_ids` and the integer numerators; every model score and every rate / step mean lists, per training seed, its run, evaluation file, SHA-256, the 300 test seeds and the integer sum it came from.",
            "- Resource numbers cite the summary.json field they were read from (`resource_records[].resources.<field>.source`); constants (t quantiles, B, thresholds, RNG) are under `parameters`, taken from the frozen protocol; labels are computed from the unrounded values before formatting.",
            "- The evaluation files read, with SHA-256, are listed in input_manifest.json; tables here show 4 decimals only.",
            "- limits: 5 training seeds; one map; privileged input (BFS distance fields); same budget is not the same compute; model selection on GPU vs test on CPU; the t intervals assume near-normal differences, which 5 seeds cannot check; the bootstrap is a sensitivity analysis and does not add training seeds.",
            "- this report makes no statement about mechanisms."]
    return "\n".join(out) + "\n"


def write_csv(path, names, vals):
    order = [k for q in ENDPOINTS for k in names if k.startswith(q + ".")] + [k for k in names if k.startswith("best_minus_last.")]
    idx = [names.index(k) for k in order]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["replicate_index"] + order)
        for b in range(B):
            w.writerow([b] + [repr(float(vals[b, i])) for i in idx])


RESOURCE_FIELDS = ("minutes", "peak_working_set_mb", "peak_commit_mb", "cuda_max_allocated_mb", "cuda_max_reserved_mb")
MEMORY_FIELDS = RESOURCE_FIELDS[1:]


def resource_records(ctx):
    """Per run: the budget / occupancy fields and every optional resource field of summary.json, each with its source; an absent or null
    optional field is reported as null WITH a reason (the summary's own peak_memory_error when it gave one), never as NaN or a guess.
    Failed attempts archived for the run are listed with their details."""
    attempts = {}
    for i, a in enumerate(ctx["seal"]["attempts"]):
        attempts.setdefault(a["run"], []).append({**a, "source": f"{ctx['manifest']['seal_path']}#attempts[{i}]"})
    out = []
    for n in ctx["names"]:
        s = ctx["docs"][f"{n}/summary.json"]
        srel = f"{n}/summary.json"
        fields = {}
        for k in RESOURCE_FIELDS:
            v = s.get(k)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
                raise AnalysisError("E_FIELD_TYPE", f"summary {k} must be a non-negative number or null", path=srel, run_name=n, json_path=f"$.{k}", actual=v)
            if v is None:
                err = s.get("peak_memory_error") if k in MEMORY_FIELDS else None
                reason = ("null in summary.json" if k in s else "field absent from summary.json") + (f"; peak_memory_error: {err}" if err else "")
                fields[k] = {"value": None, "reason": reason, "source": f"{srel}#{k}"}
            else:
                fields[k] = {"value": v, "reason": None, "source": f"{srel}#{k}"}
        out.append({"run_name": n, "replay_size": s["replay"]["size"], "actual_updates": s["actual_updates"], "total_env_steps": s["total_env_steps"],
                    "best_step": s["checkpoints"]["best"]["step"], "source": srel, "sources": {"replay_size": f"{srel}#replay.size", "actual_updates": f"{srel}#actual_updates",
                    "total_env_steps": f"{srel}#total_env_steps", "best_step": f"{srel}#checkpoints.best.step"}, "resources": fields,
                    "attempts": attempts.get(n, [])})
    return out


def deviations(ctx):
    """Only what a record states: deviations declared in the freeze manifest (copied verbatim) and every archived failed attempt of the
    seal.  The script does not infer deviations from the data."""
    out = [{"id": d["id"], "origin": "freeze_manifest", "description": d["description"], "source": d["source"]} for d in ctx["manifest"].get("deviations", [])]
    for i, a in enumerate(ctx["seal"]["attempts"]):
        out.append({"id": f"failed_attempt:{a['run']}:{a['attempt']}", "origin": "evaluation_seal", "run_name": a["run"],
                    "description": f"attempt {a['attempt']} of {a['run']} was archived and the run restarted from scratch: {a['reason']}",
                    "source": f"{ctx['manifest']['seal_path']}#attempts[{i}]"})
    return out


def analyze(manifest: Path, input_root: Path, output_dir: Path, mode: str, project_root: Path | None = None) -> dict:
    if mode not in ("synthetic", "formal"):
        raise AnalysisError("E_MANIFEST", "mode must be synthetic or formal")
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise AnalysisError("E_MANIFEST", "output directory already exists; an analysis id is never overwritten", path=output_dir.name)
    ctx = validate_inputs(Path(manifest), Path(input_root), Path(project_root) if project_root else None, mode)
    ep, expl, prim, names, vals, index_sha = analyze_arrays(ctx)
    script = SCRIPT_PATH
    analysis = {
        "schema_version": "prereg-analysis-1", "analysis_spec_version": SPEC_VERSION, "mode": mode, "complete": True,
        "provenance": {"analysis_script_sha256": sha256_file(SCRIPT_PATH), "code_commit": ctx["manifest"]["code_commit"], "freeze_manifest_sha256": ctx["manifest_sha"],
                       "frozen_files": ctx["manifest"]["frozen_files"], "evaluation_seal_sha256": ctx["seal_sha"], "evaluation_device": ctx["frozen"]["final_eval_device"],
                       "numpy_version": np.__version__, "python_version": sys.version.split()[0], "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "integrity": {"expected_runs": 30, "actual_runs": 30, "evaluation_files": len(ctx["files"]), "records_per_file": 300, "test_seed_range": [30000, 30299],
                      "initial_hash_pairs_equal": 15, "validation_schedule": "15 x 50", "hard_enabled": ctx["hard"], "all_checks_passed": True},
        "parameters": {"t95_df4": T95, "t975_df4": T975, "ddof": 1, "bootstrap": {"B": B, "rng": "numpy.random.Generator(PCG64(271828))", "per_round_order": "I=integers(0,5,5) then J=integers(0,300,300)",
                       "quantile_method": "linear (type 7)", "index_stream_sha256": index_sha, "index_stream_sha256_expected": EXPECTED_INDEX_SHA},
                       "magnitude_threshold": 10},
        "endpoints": ep, "primary_decisions": prim, "exploratory": expl,
        "resource_records": resource_records(ctx),
        "deviations": deviations(ctx), "limitations": ["5 training seeds", "single map", "privileged BFS-field input", "equal budget is not equal compute", "GPU selection vs CPU test devices", "t intervals assume near-normal differences"],
    }
    input_manifest = {"mode": mode, "files": {k: {"sha256": v} for k, v in sorted(ctx["files"].items())}, "seal_sha256": ctx["seal_sha"],
                      "config_and_summary_files": {k: v for k, v in ctx["seal"]["files"].items() if k.endswith(("config.json", "summary.json"))}}
    out_parent = output_dir.parent
    out_parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".analysis_tmp_", dir=out_parent))
    try:
        (tmp / "analysis.json").write_text(json.dumps(analysis, indent=1), encoding="utf-8")
        (tmp / "REPORT.md").write_text(build_report(ctx, ep, expl, prim, index_sha, analysis["resource_records"], analysis["deviations"]), encoding="utf-8")
        (tmp / "bootstrap_indices.sha256").write_text(f"{index_sha}  bootstrap_index_stream_12200000_bytes\n", encoding="utf-8")
        (tmp / "input_manifest.json").write_text(json.dumps(input_manifest, indent=1), encoding="utf-8")
        write_csv(tmp / "bootstrap_replicates.csv", names, vals)
        os.rename(tmp, output_dir)  # atomic publish: all files or nothing
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return analysis


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--mode", choices=["synthetic", "formal"], required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--input-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--project-root", type=Path)
    a = ap.parse_args(argv)
    try:
        analyze(a.manifest, a.input_root, a.output_dir, a.mode, a.project_root)
    except AnalysisError as e:
        sys.stderr.write(json.dumps(e.obj, allow_nan=False, default=str) + "\n")
        return 2
    print(f"analysis written to {a.output_dir.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
