#!/usr/bin/env python3
"""Runner for the preregistered architecture x n-step study (docs/prereg/).

  python scripts/prereg.py check                       matrix file, frozen configuration, code defaults
  python scripts/prereg.py list                        the 30 runs in their fixed order
  python scripts/prereg.py run [--workers N]           train the 30 runs (formal; needs a frozen configuration)
  python scripts/prereg.py smoke --profile quick|load  correctness / throughput / memory smoke runs (seeds 900/901,
                                                        validation on the smoke seeds 40000-40009; never formal data)

Deliberately NOT built on run_experiments.run_one:
  * the formal runner never evaluates the test seeds (the sealed final evaluation is a separate, guarded step);
  * it never resumes: an unfinished run directory is moved to attempts/<run>/attempt_<k>/ (and logged in
    attempts.jsonl) and the run starts again from scratch with --no-resume;
  * everything comes from the matrix file and the frozen configuration and is passed to `cli train` explicitly;
    PACMAN_* environment variables that could change a setting silently make the runner refuse to start.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

PY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pacman_rl import prereg as PR  # noqa: E402
from pacman_rl import provenance as P  # noqa: E402

import run_experiments as RX  # noqa: E402  (only take_lock / pid_alive are used)

ROOT = PY.parent
FORBIDDEN_ENV = ("PACMAN_TRAIN_EXTRA", "PACMAN_STEPS", "PACMAN_DEVICE", "PACMAN_WORKERS", "PACMAN_SKIP_ALGO", "PACMAN_RESULTS_DIR")
DEFAULT_RESULTS = ROOT / "results_prereg"
SMOKE_RESULTS = ROOT / "results_prereg_smoke"
REQUIRED_FILES = ("config.json", "train_log.jsonl", "summary.json", "last.pt", "best.pt", "code_version.json", "environment.json")
TOP_LEVEL_TO_FILL = ("machine_id", "worker_count", "code_commit", "hard_enabled")
TO_FILL = ("analysis_script_sha256", "preregistration_document_sha256", "dependency_lock_sha256", "driver_and_os_note")


class Refused(SystemExit):
    pass


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reject_env():
    bad = [k for k in FORBIDDEN_ENV if k in os.environ]
    if bad:
        raise Refused(f"refusing to start: {bad} would override settings that must come from the matrix / frozen configuration; unset them")


# ------------------------------------------------------------------ one run
def _content(run_dir: Path) -> list[Path]:
    return [p for p in run_dir.iterdir() if p.name != ".lock"] if run_dir.exists() else []


def archive_incomplete(results: Path, name: str, reason: str) -> int:
    """Move everything in runs/<name> (except the lock) to attempts/<name>/attempt_<k>/ and log it.  Returns k."""
    run_dir = results / "runs" / name
    base = results / "attempts" / name
    k = len(list(base.glob("attempt_*"))) + 1 if base.exists() else 1
    dest = base / f"attempt_{k}"
    dest.mkdir(parents=True)
    moved = []
    for p in _content(run_dir):
        shutil.move(str(p), str(dest / p.name))
        moved.append(p.name)
    with open(results / "attempts.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": name, "attempt": k, "reason": reason, "archived_utc": utc(), "files": sorted(moved)}) + "\n")
    return k


def finalize(run_dir: Path, name: str, cfg, attempt: int, order) -> list[str]:
    """Checks a finished training run; writes run_complete.json when there is nothing to complain about."""
    problems = [f"missing {f}" for f in REQUIRED_FILES if not (run_dir / f).exists()]
    forbidden = [p.name for p in run_dir.iterdir() if p.name.startswith(("test", "final")) or p.name in ("resume.pt", "resume_replay.npz")]
    problems += [f"forbidden file/dir in a formal run: {x}" for x in forbidden]
    if problems:
        return problems
    train_config = json.loads((run_dir / "config.json").read_text())
    if train_config != PR.expected_config_json(cfg):
        problems.append("config.json differs from the configuration derived from the matrix row")
    summary = json.loads((run_dir / "summary.json").read_text())
    if summary.get("env_steps") != cfg.total_env_steps:
        problems.append(f"trained {summary.get('env_steps')} env steps, expected {cfg.total_env_steps}")
    log = [json.loads(x) for x in (run_dir / "train_log.jsonl").read_text().splitlines() if x.strip()]
    init = [r for r in log if r.get("type") == "init"]
    if len(init) != 1 or any(r.get("type") == "resume" for r in log):
        problems.append("train_log.jsonl must hold exactly one init row and no resume marker")
    if problems:
        return problems
    import torch

    state = lambda f: P.state_hash(torch.load(run_dir / f, weights_only=False, map_location="cpu")["state_dict"])  # noqa: E731
    code_version = json.loads((run_dir / "code_version.json").read_text())
    row = next((r for r in PR.load_matrix() if r["run_name"] == name), {"order": order, "run_name": name, "primary_checkpoint": "last"})
    sm = summary
    from pacman_rl.evaluate import seed_set

    boundaries = list(range(cfg.eval_every, cfg.total_env_steps + 1, cfg.eval_every))
    steps_ok = sm.get("validation_steps") == boundaries + ([cfg.total_env_steps] if cfg.total_env_steps % cfg.eval_every else [])  # formal: exactly 15
    if (sm.get("run_name") != name or sm.get("total_env_steps") != cfg.total_env_steps or not isinstance(sm.get("actual_updates"), int)
            or not isinstance(sm.get("replay", {}).get("size"), int) or not steps_ok
            or sm.get("validation_episodes_each") != len(seed_set(cfg.val_set))
            or sm.get("checkpoints", {}).get("last", {}).get("step") != cfg.total_env_steps):
        problems.append("summary.json does not satisfy the preregistered summary contract (budget / validation schedule / checkpoints)")
        return problems
    freeze = PR.load_freeze()
    code_commit = freeze.get("code_commit") or code_version["git_sha"]  # C when frozen (the run's own HEAD is F); otherwise HEAD itself
    config = PR.effective_config(row, freeze, cfg, code_commit, P.file_sha256(PR.FREEZE_FILE))
    (run_dir / "train_config.json").write_text(json.dumps(train_config, indent=1))  # what train() wrote, kept for reference
    (run_dir / "config.json").write_text(json.dumps(config, indent=1))              # merged effective configuration (the contract file)
    done = {"run": name, "attempt": attempt, "matrix_order": order, "matrix_sha256": PR.MATRIX_SHA256, "config": config,
            "last_file_sha256": P.file_sha256(run_dir / "last.pt"), "best_file_sha256": P.file_sha256(run_dir / "best.pt"),
            "last_state_sha256": state("last.pt"), "best_state_sha256": state("best.pt"),
            "init_online_hash": init[0]["online_hash"], "summary": summary,
            "code_version": code_version, "code_commit": code_commit, "freeze_commit": code_version["git_sha"],
            "environment": json.loads((run_dir / "environment.json").read_text()), "completed_utc": utc()}
    (run_dir / "run_complete.json").write_text(json.dumps(done, indent=1), encoding="utf-8")
    return []


def execute(name: str, cfg, results: Path, order=None) -> str:
    """Train one run from scratch.  Returns 'done' | 'skipped' | 'failed'."""
    run_dir = results / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    if not RX.take_lock(run_dir):
        print(f"skip {name} (running elsewhere)", flush=True)
        return "skipped"
    try:
        if (run_dir / "run_complete.json").exists():
            print(f"skip {name} (complete)", flush=True)
            return "skipped"
        attempt = 1
        if _content(run_dir):
            attempt = archive_incomplete(results, name, "unfinished run directory found at start (interrupted or failed); starting again from scratch") + 1
        print(f"start {name} (attempt {attempt})", flush=True)
        env = {k: v for k, v in os.environ.items() if k not in FORBIDDEN_ENV}
        env.update({"PYTHONPATH": str(PY), "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PACMAN_RESULTS_DIR": str(results)})
        cmd = [sys.executable, "-m", "pacman_rl.cli", "train", *PR.train_args(cfg, name), "--no-resume"]
        with open(run_dir / "stdout.log", "w", encoding="utf-8") as f:
            rc = subprocess.run(cmd, cwd=PY, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
        problems = [f"training process exited with code {rc}"] if rc else finalize(run_dir, name, cfg, attempt, order)
        if problems:
            (run_dir / "failure.json").write_text(json.dumps({"run": name, "attempt": attempt, "problems": problems, "utc": utc()}, indent=1))
            print(f"FAILED {name}: {problems}", flush=True)
            return "failed"
        print(f"done {name}", flush=True)
        return "done"
    finally:
        shutil.rmtree(run_dir / ".lock", ignore_errors=True)


# ------------------------------------------------------------------ preflight
def freeze_problems(freeze: dict) -> list[str]:
    problems = []
    if freeze.get("status") != "frozen":
        problems.append(f"{PR.FREEZE_FILE.name} status is {freeze.get('status')!r}, not 'frozen'")
    for k in TOP_LEVEL_TO_FILL:
        if freeze.get(k) in (None, ""):
            problems.append(f"{k} is not filled in")
    for k in TO_FILL:
        if freeze["to_fill_at_freeze"].get(k) in (None, ""):
            problems.append(f"to_fill_at_freeze.{k} is not filled in")
    if freeze["to_fill_at_freeze"].get("power_and_sleep_settings_confirmed") is not True:
        problems.append("to_fill_at_freeze.power_and_sleep_settings_confirmed must be true")
    if freeze["matrix_sha256"] != PR.MATRIX_SHA256:
        problems.append("frozen config matrix_sha256 differs from the code's pinned value")
    return problems + PR.check_frozen_config(freeze)


def preflight(freeze: dict, workers: int | None, *, allow_unfrozen: bool, root: Path | None = None) -> int:
    """Refuse to start unless everything is frozen.  The code commit C is the one named by the frozen configuration; the commit the
    runs are made from is F = HEAD, which must be C or a descendant that adds only freeze material (see provenance.freeze_state)."""
    reject_env()
    problems = PR.check_matrix_file()
    if not allow_unfrozen:
        problems += freeze_problems(freeze)
        problems += P.freeze_state(root or ROOT, freeze.get("code_commit"))["problems"]
    frozen_workers = freeze.get("worker_count")
    w = workers or frozen_workers or 1
    if frozen_workers and w != frozen_workers and not allow_unfrozen:
        problems.append(f"workers={w} but the frozen configuration says {frozen_workers}")
    if w > freeze["max_workers_without_explicit_setting"] and w != frozen_workers:
        problems.append(f"{w} workers: more than {freeze['max_workers_without_explicit_setting']} needs an explicit frozen setting")
    if problems:
        raise Refused("refusing to start:\n  - " + "\n  - ".join(problems))
    return w


def run_matrix(rows, freeze, results: Path, workers: int, overrides: dict | None = None, only=None) -> dict[str, str]:
    overrides = overrides or {}
    jobs = [(r["run_name"], PR.train_config(r, freeze, **overrides), r["order"]) for r in rows if not only or r["run_name"] in only]
    with ThreadPoolExecutor(workers) as ex:  # ex.map starts the jobs in matrix order
        outcomes = list(ex.map(lambda j: execute(j[0], j[1], results, j[2]), jobs))
    return {j[0]: o for j, o in zip(jobs, outcomes)}


# ------------------------------------------------------------------ smoke
PROFILES = {
    "quick": {"steps": 2000, "learn_start": 500, "buffer": 4000, "eval_every": 1000, "workers": 1,
              "pairs": [(a, n, s) for s in (900, 901) for a in PR.ARCHS for n in PR.NSTEPS]},
    "load": {"steps": 110000, "learn_start": 4000, "buffer": 100000, "eval_every": 20000, "workers": 2,
             "pairs": [("res8", 1, 900), ("res8", 3, 901)]},
}


def smoke(profile: str, device: str, results: Path, steps=None, pairs=None, workers=None, resume_check=True) -> dict:
    reject_env()
    prof = PROFILES[profile]
    freeze, rows = PR.load_freeze(), PR.load_matrix()
    template = {(r["arch"], r["n_step"]): r for r in rows if r["seed"] == 100}
    jobs = []
    for arch, n, seed in (pairs or prof["pairs"]):
        cfg = PR.train_config(template[(arch, n)], freeze, seed=seed, device=device, val_set=freeze["smoke_val_set"],
                              total_env_steps=steps or prof["steps"], learn_start=prof["learn_start"], buffer=prof["buffer"],
                              eval_every=prof["eval_every"])
        jobs.append((f"smoke_{profile}_{arch}_n{n}_s{seed}", cfg))  # profile in the name: quick and load never share a run
    t0 = time.time()
    with ThreadPoolExecutor(workers or prof["workers"]) as ex:
        outcomes = list(ex.map(lambda j: execute(j[0], j[1], results), jobs))
    report = {"profile": profile, "device": device, "note": "smoke runs only: scores are NOT used to choose anything", "runs": {}, "wall_seconds": None}
    from pacman_rl.evalrun import evaluate_checkpoint

    inits: dict = {}
    for (name, cfg), outcome in zip(jobs, outcomes):
        run_dir = results / "runs" / name
        entry = {"outcome": outcome}
        if outcome == "done" or (run_dir / "run_complete.json").exists():
            done = json.loads((run_dir / "run_complete.json").read_text())
            s = done["summary"]
            entry.update({k: s.get(k) for k in ("minutes", "updates", "env_steps", "replay_size", "episodes_started", "best_val_score", "best_env_steps",
                                                 "weights_finite", "nonfinite_loss_updates_this_session", "peak_working_set_mb", "peak_commit_mb", "peak_memory_error",
                                                 "cuda_max_allocated_mb", "cuda_max_reserved_mb")})
            entry["env_steps_per_second"] = round(s["env_steps"] / (s["minutes"] * 60), 1) if s.get("minutes") else None
            entry["init_online_hash"] = done["init_online_hash"]
            inits.setdefault((cfg.arch, cfg.seed), {})[cfg.n_step] = done["init_online_hash"]
            ev = {}
            for label in ("last", "best"):
                t = time.time()
                out = evaluate_checkpoint(run_dir / f"{label}.pt", freeze["smoke_val_set"], ["standard"], run_dir / "eval_smoke", device="cpu", threads=1, force=True)
                ev[label] = {"seconds": round(time.time() - t, 2), "n_records": len(json.loads(out["standard"].read_text())["records"])}
            entry["cpu_eval_10_episodes"] = ev
        report["runs"][name] = entry
    report["initial_hash_pairs_equal"] = {f"{a}_s{s}": (len(set(v.values())) == 1 and len(v) == 2) for (a, s), v in inits.items() if len(v) == 2}
    if resume_check:
        report["interrupt_resume_check"] = interrupt_resume_check(results / f"interrupt_check_{profile}")
    report["wall_seconds"] = round(time.time() - t0, 1)
    report["environment"] = P.environment_info(device if device != "auto" else "cpu")
    results.mkdir(parents=True, exist_ok=True)
    (results / f"smoke_report_{profile}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def interrupt_resume_check(path: Path) -> dict:
    """In-process: stop a tiny cnn2 run after its first checkpoint, resume it, and require a completed continuous log."""
    from pacman_rl.dqn import TrainConfig, load_checkpoint, train

    shutil.rmtree(path, ignore_errors=True)
    cfg = TrainConfig(arch="cnn2", total_env_steps=640, learn_start=64, eval_every=160, n_envs=4, buffer=2000, batch=8, seed=900,
                      threads=1, val_set="smoke_eval")
    train(cfg, path, log=lambda *_: None, _stop_after=320)
    train(cfg, path, log=lambda *_: None)
    rows = [json.loads(x) for x in (path / "train_log.jsonl").read_text().splitlines()]
    steps = [r["env_steps"] for r in rows if r["type"] == "eval"]
    ok = steps == sorted(steps) and steps[-1] == 640 and any(r["type"] == "resume" for r in rows) and load_checkpoint(path / "last.pt")[2]["env_steps"] == 640
    return {"ok": bool(ok), "note": "resume exists for exploratory work; formal runs never resume"}


# ------------------------------------------------------------------ sealed final evaluation
def make_manifest(results: Path, analysis_script: Path, out: Path, *, rows=None, freeze=None, allow_unfrozen=False, tiny=None) -> str:
    """Check that all runs are complete and untouched and write the integrity manifest.  Returns its SHA-256."""
    from pacman_rl import seal

    rows, freeze = rows or PR.load_matrix(), freeze or PR.load_freeze()
    manifest = seal.build_manifest(results, rows, freeze, analysis_script, allow_unfrozen=allow_unfrozen, tiny_overrides=tiny)
    return seal.write_manifest(out, manifest)


def final_eval_run(results: Path, name: str, token, freeze: dict | None = None, scenarios=None) -> dict[str, str]:
    """Evaluate last.pt and best.pt of one run on the sealed seeds (CPU, 1 thread) into runs/<name>/{last,best}/<scenario>.json
    (preregistered format).  The optional hard scenario is evaluated for last.pt only and only if the frozen configuration
    enables it.  If best and last hold identical weights the evaluation is run once and the best file reuses the records
    (and says so in meta.reused_from)."""
    from pacman_rl.evalrun import evaluate_checkpoint, prereg_eval_payload

    freeze = freeze or PR.load_freeze()
    if not isinstance(freeze.get("hard_enabled"), bool):
        raise Refused("hard_enabled must be declared (true/false) in the frozen configuration before the final evaluation")
    run = results / "runs" / name
    done = json.loads((run / "run_complete.json").read_text())
    meta = {"run_name": name, "code_commit": done["code_commit"], "synthetic": False}
    kw = dict(split=freeze["test_set"], device=freeze["final_eval_device"], threads=freeze["final_eval_threads"], unseal=token, prereg_meta=meta)
    written = {}
    for sc, path in evaluate_checkpoint(run / "last.pt", scenarios=["standard"], out_dir=run, label="last", **kw).items():
        written[f"last/{sc}"] = P.file_sha256(path)
    if done["best_state_sha256"] == done["last_state_sha256"]:
        last = json.loads((run / "last" / "standard.json").read_text())
        (run / "best").mkdir(exist_ok=True)
        best = prereg_eval_payload(last["records"], run_name=name, cfg=PR.train_config(next(r for r in PR.load_matrix() if r["run_name"] == name), freeze),
                                   label="best", step=done["summary"]["checkpoints"]["best"]["step"], weights_sha256=done["best_state_sha256"],
                                   code_commit=meta["code_commit"], scenario="standard", device=freeze["final_eval_device"],
                                   threads=freeze["final_eval_threads"], reused_from="last")
        with open(run / "best" / "standard.json", "x", encoding="utf-8") as f:
            json.dump(best, f, indent=1)
        written["best/standard"] = P.file_sha256(run / "best" / "standard.json")
    else:
        for sc, path in evaluate_checkpoint(run / "best.pt", scenarios=["standard"], out_dir=run, label="best", **kw).items():
            written[f"best/{sc}"] = P.file_sha256(path)
    if freeze["hard_enabled"]:
        for sc, path in evaluate_checkpoint(run / "last.pt", scenarios=["hard"], out_dir=run, label="last", **kw).items():
            written[f"last/{sc}"] = P.file_sha256(path)
    return written


def final_eval(manifest: Path, results: Path, analysis_script: Path, *, unseal: bool, rows=None, freeze=None,
               allow_unfrozen=False, tiny=None) -> dict:
    """The ONLY code path that reads the sealed test seeds.  Verifies the manifest against the files on disk first."""
    from pacman_rl import seal

    if not unseal:
        raise Refused("the sealed test seeds are only read with an explicit --unseal (and a verified manifest)")
    reject_env()
    rows, freeze = rows or PR.load_matrix(), freeze or PR.load_freeze()
    try:
        token = seal.verify_manifest(manifest, results, rows, freeze, analysis_script, allow_unfrozen=allow_unfrozen, tiny_overrides=tiny)
    except seal.ManifestError as e:
        raise Refused(str(e))
    with open(results / "unseal_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"utc": utc(), "manifest_sha256": token.manifest_sha256, "runs": len(rows)}) + "\n")
    index = {r["run_name"]: final_eval_run(results, r["run_name"], token, freeze) for r in rows}
    (results / "final_eval_index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")  # file hashes only, no scores
    return index


def make_evaluation_seal(results: Path, pretest_manifest: Path, freeze_manifest: Path, out: Path | None = None, *, rows=None, freeze=None) -> str:
    """After the final evaluation: hash every file the analysis reads and write evaluation_seal.json."""
    from pacman_rl import seal

    rows, freeze = rows or PR.load_matrix(), freeze or PR.load_freeze()
    out = out or results / "evaluation_seal.json"
    if out.exists():
        raise Refused(f"{out.name} already exists; the evaluation is sealed once")
    obj = seal.build_evaluation_seal(results, rows, freeze, pretest_manifest, freeze_manifest)
    out.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8")
    return P.file_sha256(out)


# ------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("list")
    p = sub.add_parser("run")
    p.add_argument("--workers", type=int)
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--only", nargs="*")
    p = sub.add_parser("manifest", help="verify that all 30 runs are complete and untouched; write the integrity manifest")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--analysis-script", type=Path, required=True)
    p.add_argument("--out", type=Path)
    p = sub.add_parser("final-eval", help="the only step that reads the sealed test seeds (CPU, 1 thread)")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--analysis-script", type=Path, required=True)
    p.add_argument("--unseal", action="store_true", help="explicit confirmation that the test seeds may be read now")
    p = sub.add_parser("seal-eval", help="after final-eval: write evaluation_seal.json (hashes of every file the analysis reads)")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--manifest", type=Path, required=True, help="the pre-test integrity manifest")
    p.add_argument("--freeze-manifest", type=Path, default=PR.PREREG_DIR / "freeze_manifest.json")
    p = sub.add_parser("freeze-manifest", help="write docs/prereg/freeze_manifest.json for the current clean commit")
    p.add_argument("--analysis-script", required=True, help="path relative to the repository root")
    p.add_argument("--dependency-lock", required=True, help="path relative to the repository root")
    p.add_argument("--extra-frozen", nargs="*", default=[], help="further files to freeze (the preregistration documents), relative paths")
    p.add_argument("--out", type=Path, default=PR.PREREG_DIR / "freeze_manifest.json")
    p = sub.add_parser("smoke")
    p.add_argument("--profile", choices=list(PROFILES), default="quick")
    p.add_argument("--device", default="cuda", choices=["cpu", "cuda", "auto"])
    p.add_argument("--results-dir", type=Path, default=SMOKE_RESULTS)
    p.add_argument("--steps", type=int)
    p.add_argument("--workers", type=int)
    p.add_argument("--pairs", nargs="*", help="arch:n:seed ... (default: the profile's)")
    a = ap.parse_args(argv)
    freeze = PR.load_freeze()
    if a.cmd == "check":
        problems = PR.check_matrix_file() + [f"(not yet frozen) {x}" for x in freeze_problems(freeze)]
        print("\n".join(problems) or "matrix and frozen configuration are consistent")
        return 1 if any(not x.startswith("(not yet frozen)") for x in problems) else 0
    if a.cmd == "list":
        for r in PR.load_matrix():
            print(f"{r['order']:2d}  {r['run_name']}")
        return 0
    if a.cmd == "run":
        workers = preflight(freeze, a.workers, allow_unfrozen=False)
        out = run_matrix(PR.load_matrix(), freeze, a.results_dir, workers, only=a.only)
        print(json.dumps(out, indent=1))
        return 0 if all(v in ("done", "skipped") for v in out.values()) else 1
    if a.cmd == "manifest":
        reject_env()
        try:
            sha = make_manifest(a.results_dir, a.analysis_script, a.out or a.results_dir / "seal_manifest.json")
        except Exception as e:  # noqa: BLE001
            raise Refused(str(e))
        print(f"manifest written, sha256 {sha}")
        return 0
    if a.cmd == "final-eval":
        index = final_eval(a.manifest, a.results_dir, a.analysis_script, unseal=a.unseal)
        print(f"final evaluation written for {len(index)} runs (see final_eval_index.json); scores are not printed")
        return 0
    if a.cmd == "seal-eval":
        try:
            sha = make_evaluation_seal(a.results_dir, a.manifest, a.freeze_manifest)
        except Exception as e:  # noqa: BLE001
            raise Refused(str(e))
        print(f"evaluation seal written, sha256 {sha}")
        return 0
    if a.cmd == "freeze-manifest":
        from pacman_rl import seal

        try:
            obj = seal.build_freeze_manifest(ROOT, "docs/prereg/matrix.csv", "docs/prereg/frozen_config_v0.3.2.json", a.analysis_script,
                                             a.dependency_lock, a.extra_frozen)
        except Exception as e:  # noqa: BLE001
            raise Refused(str(e))
        a.out.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8")
        print(f"freeze manifest written for commit {obj['code_commit']}")
        return 0
    if a.cmd == "smoke":
        pairs = [(x.split(":")[0], int(x.split(":")[1]), int(x.split(":")[2])) for x in a.pairs] if a.pairs else None
        rep = smoke(a.profile, a.device, a.results_dir, a.steps, pairs, a.workers)
        print(json.dumps({k: v for k, v in rep.items() if k != "runs"}, indent=1))
        return 0 if all(r["outcome"] in ("done", "skipped") for r in rep["runs"].values()) else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
