"""Guard for the sealed preregistered test partition.

``evaluate.seed_set("prereg_test")`` refuses to return the seeds unless it is handed an ``UnsealToken``.
Tokens are only issued by ``verify_manifest`` (all preregistered runs complete, checkpoint hashes verified).
This prevents accidents (a stray ``--split`` or a copy-pasted call) when the default formal entry (``prereg.py final-eval``) is used.  It
gives no unbypassable guarantee: the low-level Python API, the public seed constants and edits of the source can all read the seeds, which
is what the frozen commit hash and the procedural rules in docs/RESEARCH_LOG.md are for (the seal is protocol-based).
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


def current_material_problems(run: Path, cfg, name: str, done: dict) -> list[str]:
    """Re-read the run's CURRENT summary.json and train_log.jsonl (not the copies cached in run_complete.json): they must exist, satisfy
    the preregistered contract and equal the summary recorded when the run completed."""
    from . import prereg as PR

    problems = []
    sp, lp = run / "summary.json", run / "train_log.jsonl"
    if not sp.is_file():
        return ["summary.json is missing"]
    try:
        summary = json.loads(sp.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"summary.json is not valid JSON ({e})"]
    rows = None
    if not lp.is_file():
        problems.append("train_log.jsonl is missing")
    else:
        try:
            rows = [json.loads(x) for x in lp.read_text(encoding="utf-8").splitlines() if x.strip()]
        except ValueError as e:
            problems.append(f"train_log.jsonl is not valid JSON ({e})")
    problems += ["summary contract: " + x for x in PR.summary_contract_problems(summary, cfg, name, rows)]
    if summary != done.get("summary"):
        problems.append("summary.json differs from the summary recorded in run_complete.json (edited or replaced after completion)")
    return problems


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
        stray = [p.name for p in run.iterdir() if p.name.startswith(("test", "final")) or p.name.startswith("resume") or p.name in ("last", "best")]
        if stray:
            problems.append(f"{name}: forbidden files present before the final evaluation: {stray}")
        want = PR.effective_config(r, freeze, PR.train_config(r, freeze, **(tiny_overrides or {})), done["code_commit"],
                                   PR.file_sha256(PR.FREEZE_FILE))
        if done["config"] != want or json.loads((run / "config.json").read_text()) != want:
            problems.append(f"{name}: recorded configuration differs from the one derived from the matrix row")
        cfg = PR.train_config(r, freeze, **(tiny_overrides or {}))
        problems += [f"{name}: {x}" for x in current_material_problems(run, cfg, name, done)]
        for label in ("last", "best"):
            f = run / f"{label}.pt"
            if not f.exists():
                problems.append(f"{name}: {label}.pt missing")
            elif _sha_file(f) != done[f"{label}_file_sha256"] or _state_sha(f) != done[f"{label}_state_sha256"]:
                problems.append(f"{name}: {label}.pt does not match the hash recorded when the run completed (modified?)")
        cv = done["code_version"]
        codes[name], trees[name], envs[name] = (done["code_commit"], cv["git_dirty"], done["freeze_commit"]), cv["python_tree_sha256"], done["environment"]
        facts[name] = {"order": r["order"], "arch": r["arch"], "n_step": r["n_step"], "seed": r["seed"], "attempt": done["attempt"],
                       "init_online_hash": done["init_online_hash"], "run_complete_sha256": _sha_file(done_file),
                       **{k: done[k] for k in ("last_file_sha256", "best_file_sha256", "last_state_sha256", "best_state_sha256")}}
    for key in {(f["arch"], f["seed"]) for f in facts.values()}:
        hs = {f["init_online_hash"] for f in facts.values() if (f["arch"], f["seed"]) == key}
        if len(hs) != 1:
            problems.append(f"{key[0]} seed {key[1]}: n_step=1 and n_step=3 did not start from the same initial weights")
    if len({c[2] for c in codes.values()}) > 1 or len({c[0] for c in codes.values()}) > 1 or len(set(trees.values())) > 1:
        problems.append("runs were produced by different code versions (code commit, freeze commit or python/ tree differ between runs)")
    if len({json.dumps(e, sort_keys=True) for e in envs.values()}) > 1:
        problems.append("runs were produced in different software/GPU environments")
    if not allow_unfrozen:
        frozen = freeze.get("code_commit")
        if any(c[0] != frozen or c[1] for c in codes.values()):
            problems.append("runs were not produced from the frozen code commit with a clean working tree")
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


# ---------------------------------------------------------------------------------- evaluation seal / freeze manifest
EVAL_SEAL_SCHEMA = "prereg-seal-1"
FREEZE_SCHEMA = "prereg-freeze-1"
REQUIRED_FROZEN_DOCS = ("docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md", "docs/prereg/ANALYSIS_SPEC_v0.3.2.md")


def required_run_files(hard_enabled: bool) -> list[str]:
    """Run-directory-relative files the analysis requires for every run."""
    files = ["config.json", "summary.json", "last/standard.json", "best/standard.json"]
    return files + (["last/hard.json"] if hard_enabled else [])


def build_evaluation_seal(results_dir, rows, freeze, pretest_manifest, freeze_manifest, *, synthetic=False) -> dict:
    """Seal written AFTER the final evaluation: the hash of every file the analysis will read, plus the facts the analysis
    must be able to rely on (training complete, checkpoints unchanged since the pre-test manifest, failed attempts)."""
    results_dir = Path(results_dir)
    m = json.loads(Path(pretest_manifest).read_text(encoding="utf-8"))
    if m.get("version") != MANIFEST_VERSION or m.get("complete") is not True:
        raise ManifestError("the pre-test integrity manifest is missing or not complete")
    hard = freeze.get("hard_enabled")
    if not isinstance(hard, bool):
        raise ManifestError("hard_enabled must be declared in the frozen configuration")
    problems, files = [], {}
    for r in rows:
        name, run = r["run_name"], results_dir / "runs" / r["run_name"]
        facts = m["runs"].get(name)
        if facts is None or not (run / "run_complete.json").exists():
            problems.append(f"{name}: not part of the pre-test manifest / not complete")
            continue
        for label in ("last", "best"):
            f = run / f"{label}.pt"
            if not f.exists() or _sha_file(f) != facts[f"{label}_file_sha256"] or _state_sha(f) != facts[f"{label}_state_sha256"]:
                problems.append(f"{name}: {label}.pt changed since the pre-test manifest")
        for rel in required_run_files(hard):
            p = run / rel
            if not p.is_file():
                problems.append(f"{name}: required file {rel} missing")
            else:
                files[f"{name}/{rel}"] = _sha_file(p)
        if not hard and (run / "last" / "hard.json").exists():
            problems.append(f"{name}: last/hard.json exists but hard_enabled is false")
    if problems:
        raise ManifestError("cannot seal the evaluation:\n  - " + "\n  - ".join(problems))
    attempts_file = results_dir / "attempts.jsonl"
    attempts = [json.loads(x) for x in attempts_file.read_text().splitlines() if x.strip()] if attempts_file.exists() else []
    return {"schema_version": EVAL_SEAL_SCHEMA, "synthetic": synthetic, "freeze_manifest_sha256": _sha_file(freeze_manifest),
            "all_training_complete": True, "all_checkpoint_checks_passed": True, "runs": [r["run_name"] for r in rows],
            "files": files, "attempts": attempts}


def build_freeze_manifest(root, matrix_path, config_path, analysis_script, dependency_lock, extra_frozen=(), *, spec_version="0.3.2", deviations=()) -> dict:
    """The freeze manifest of ANALYSIS_SPEC section 1.1.  `code_commit` is the code commit C named by the frozen configuration (the
    commit holding this manifest, F, cannot be recorded in it).  The working copy must be a legitimate freeze state of C: HEAD is C
    or a descendant, python/ identical, only freeze material changed -- uncommitted freeze files are fine here, that is the point at
    which they are being prepared.  `project_root` is written as "." so that no machine path is committed."""
    from .provenance import freeze_state

    root = Path(root)
    cfg_file = root / config_path
    if not cfg_file.is_file():
        raise ManifestError(f"frozen configuration {config_path} not found")
    code_commit = json.loads(cfg_file.read_text(encoding="utf-8")).get("code_commit")
    state = freeze_state(root, code_commit, allow_dirty_freeze_files=True)
    if state["problems"]:
        raise ManifestError("not a valid freeze state:\n  - " + "\n  - ".join(state["problems"]))
    rels = list(dict.fromkeys(str(Path(p).as_posix()) for p in (matrix_path, config_path, analysis_script, dependency_lock, *REQUIRED_FROZEN_DOCS, *extra_frozen)))
    missing = [r for r in rels if not (root / r).is_file()]
    if missing:
        raise ManifestError(f"frozen files missing (the preregistration and analysis-specification texts are mandatory): {missing}")
    devs = list(deviations)
    for i, d in enumerate(devs):  # declared deviations (id, description, source) are copied verbatim into the analysis report; nothing is inferred
        if not isinstance(d, dict) or set(d) != {"id", "description", "source"} or not all(isinstance(v, str) and v for v in d.values()):
            raise ManifestError(f"deviation {i} must be an object with non-empty string fields id, description, source")
    manifest = {"schema_version": FREEZE_SCHEMA, "synthetic": False, "complete": True, "spec_version": spec_version, "code_commit": code_commit,
            "project_root": ".", "matrix_path": str(Path(matrix_path).as_posix()), "config_path": str(Path(config_path).as_posix()),
            "analysis_script_path": str(Path(analysis_script).as_posix()), "dependency_lock_path": str(Path(dependency_lock).as_posix()),
            "frozen_files": {r: _sha_file(root / r) for r in rels}, "seal_path": "results_prereg/evaluation_seal.json"}
    if devs:
        manifest["deviations"] = devs
    from .freeze_binding import check_binding, load_json_strict

    # the generator applies the same rules the formal entries will apply to the committed manifest (it does not need an older manifest)
    problems = check_binding(root, load_json_strict(cfg_file), manifest)
    if problems:
        raise ManifestError("the frozen configuration, the files and the manifest do not agree:\n  - " + "\n  - ".join(problems))
    return manifest
