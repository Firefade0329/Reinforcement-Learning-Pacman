"""Guard for the sealed preregistered test partition.

``evaluate.seed_set("prereg_test")`` refuses to return the seeds unless it is handed an ``UnsealToken``.
Tokens are only issued by ``verify_manifest`` (all preregistered runs complete, checkpoint hashes verified).
This prevents accidents (a stray ``--split`` or a copy-pasted call); it cannot stop someone who edits the code,
which is what the frozen commit hash and the procedural rules in docs/RESEARCH_LOG.md are for.
"""
from __future__ import annotations

_ISSUE_KEY = object()


class UnsealToken:
    """Proof that an integrity manifest was verified.  Do not construct directly."""

    def __init__(self, key, manifest_sha256: str):
        if key is not _ISSUE_KEY:
            raise TypeError("UnsealToken can only be issued by seal.verify_manifest")
        self.manifest_sha256 = manifest_sha256


# ---------------------------------------------------------------------------------------------- manifest
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

MANIFEST_VERSION = 1


class ManifestError(RuntimeError):
    pass


def _sha_file(path):
    from .provenance import file_sha256

    return file_sha256(path)


def _state_sha(path):
    import torch

    from .provenance import state_hash

    return state_hash(torch.load(path, weights_only=False, map_location="cpu")["state_dict"])


def run_problems(results_dir: Path, rows, freeze, *, allow_unfrozen: bool, tiny_overrides: dict | None = None) -> tuple[list[str], dict]:
    """Everything that must hold before the sealed test seeds may be read.  Returns (problems, per-run facts)."""
    from . import prereg as PR

    problems, facts = [], {}
    results_dir = Path(results_dir)
    if PR.file_sha256(PR.MATRIX_FILE) != PR.MATRIX_SHA256:
        problems.append("the committed matrix file is not the registered one")
    codes, envs, trees = {}, {}, {}
    for r in rows:
        name, run = r["run_name"], results_dir / "runs" / r["run_name"]
        done_file = run / "run_complete.json"
        if not done_file.exists():
            problems.append(f"{name}: no run_complete.json (run missing or unfinished)")
            continue
        done = json.loads(done_file.read_text())
        if (run / "failure.json").exists():
            problems.append(f"{name}: failure.json present")
        stray = [p.name for p in run.iterdir() if p.name.startswith(("test", "final")) or p.name.startswith("resume") or p.name == "eval_final"]
        if stray:
            problems.append(f"{name}: forbidden files present before the final evaluation: {stray}")
        if done["config"] != PR.expected_config_json(PR.train_config(r, freeze, **(tiny_overrides or {}))):
            problems.append(f"{name}: recorded configuration differs from the one derived from the matrix row")
        for label in ("last", "best"):
            f = run / f"{label}.pt"
            if not f.exists():
                problems.append(f"{name}: {label}.pt missing")
            elif _sha_file(f) != done[f"{label}_file_sha256"] or _state_sha(f) != done[f"{label}_state_sha256"]:
                problems.append(f"{name}: {label}.pt does not match the hash recorded when the run completed (modified?)")
        cv = done["code_version"]
        codes[name], trees[name], envs[name] = (cv["git_sha"], cv["git_dirty"]), cv["python_tree_sha256"], done["environment"]
        facts[name] = {"order": r["order"], "arch": r["arch"], "n_step": r["n_step"], "seed": r["seed"], "attempt": done["attempt"],
                       "init_online_hash": done["init_online_hash"], "run_complete_sha256": _sha_file(done_file),
                       **{k: done[k] for k in ("last_file_sha256", "best_file_sha256", "last_state_sha256", "best_state_sha256")}}
    for key in {(f["arch"], f["seed"]) for f in facts.values()}:
        hs = {f["init_online_hash"] for f in facts.values() if (f["arch"], f["seed"]) == key}
        if len(hs) != 1:
            problems.append(f"{key[0]} seed {key[1]}: n_step=1 and n_step=3 did not start from the same initial weights")
    if len(set(codes.values())) > 1 or len(set(trees.values())) > 1:
        problems.append("runs were produced by different code versions")
    if len({json.dumps(e, sort_keys=True) for e in envs.values()}) > 1:
        problems.append("runs were produced in different software/GPU environments")
    if not allow_unfrozen:
        frozen = freeze["to_fill_at_freeze"].get("frozen_commit")
        if any(c[0] != frozen or c[1] for c in codes.values()):
            problems.append("runs were not produced by the frozen commit with a clean working tree")
    return problems, facts


def build_manifest(results_dir, rows, freeze, analysis_script, *, allow_unfrozen=False, tiny_overrides=None) -> dict:
    from . import prereg as PR

    problems, facts = run_problems(results_dir, rows, freeze, allow_unfrozen=allow_unfrozen, tiny_overrides=tiny_overrides)
    analysis_script = Path(analysis_script)
    if not analysis_script.is_file():
        problems.append("analysis script not found")
    elif not allow_unfrozen and _sha_file(analysis_script) != freeze["to_fill_at_freeze"].get("analysis_script_sha256"):
        problems.append("analysis script differs from the frozen hash")
    if problems:
        raise ManifestError("not ready to unseal:\n  - " + "\n  - ".join(problems))
    attempts = Path(results_dir) / "attempts.jsonl"
    return {"version": MANIFEST_VERSION, "complete": True, "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "matrix_sha256": PR.MATRIX_SHA256, "n_runs": len(facts), "analysis_script_sha256": _sha_file(analysis_script),
            "failed_attempts_archived": len(attempts.read_text().splitlines()) if attempts.exists() else 0, "runs": facts}


def write_manifest(path, manifest: dict) -> str:
    text = json.dumps(manifest, indent=1, sort_keys=True)
    Path(path).write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def verify_manifest(path, results_dir, rows, freeze, analysis_script, *, allow_unfrozen=False, tiny_overrides=None) -> UnsealToken:
    """Re-check the manifest against the files on disk NOW; only then issue the token that unlocks the sealed seeds."""
    path = Path(path)
    if not path.is_file():
        raise ManifestError("integrity manifest not found")
    m = json.loads(path.read_text(encoding="utf-8"))
    if m.get("version") != MANIFEST_VERSION or m.get("complete") is not True:
        raise ManifestError("manifest is not a complete version-1 manifest")
    problems, facts = run_problems(results_dir, rows, freeze, allow_unfrozen=allow_unfrozen, tiny_overrides=tiny_overrides)
    if facts != m["runs"]:
        problems.append("the runs on disk differ from the manifest (hash, attempt or initial weights)")
    if not Path(analysis_script).is_file() or _sha_file(analysis_script) != m["analysis_script_sha256"]:
        problems.append("analysis script differs from the one in the manifest")
    if m["n_runs"] != len(rows):
        problems.append("manifest and matrix disagree on the number of runs")
    if problems:
        raise ManifestError("manifest verification failed:\n  - " + "\n  - ".join(problems))
    return UnsealToken(_ISSUE_KEY, hashlib.sha256(path.read_bytes()).hexdigest())
