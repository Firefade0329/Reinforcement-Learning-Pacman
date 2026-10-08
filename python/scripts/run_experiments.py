#!/usr/bin/env python3
"""Run the experiment matrix of docs/PLAN.md section 5 with N parallel single-thread workers.

Resumable: a run whose results/runs/<name>/test_standard.json already exists is skipped.

  python scripts/run_experiments.py depth      # arch x seed
  python scripts/run_experiments.py algo       # ablate Double / Dueling / n-step on ResNet-4
  python scripts/run_experiments.py tabular    # tabular Q, 3 seeds
  python scripts/run_experiments.py baselines  # L0-L3 on val+test, standard+hard
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PY = Path(__file__).resolve().parents[1]
RESULTS = Path(os.environ.get("PACMAN_RESULTS_DIR") or PY.parent / "results")
SEEDS = (0, 1, 2)
ARCHS = ("mlp", "cnn2", "res2", "res4", "res8")
DEVICE = os.environ.get("PACMAN_DEVICE", "cpu")      # cpu | cuda | auto (conv nets only; the MLP stays on CPU)
WORKERS = int(os.environ.get("PACMAN_WORKERS", "4"))
EXTRA = shlex.split(os.environ.get("PACMAN_TRAIN_EXTRA", ""))  # e.g. "--n_step 1" appended to every train call
ABLATION_ARCH = "res4"  # fixed a priori (middle depth, affordable); see PLAN.md section 9, deviation 4
STEPS = int(os.environ.get("PACMAN_STEPS", "120000"))  # env transitions per run; see docs/PLAN.md section 9 for the budget rationale


def sh(args, log: Path | None = None):
    cmd = [sys.executable, "-m", "pacman_rl.cli", *map(str, args)]
    env = {**os.environ, "PYTHONPATH": str(PY), "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as f:
            return subprocess.run(cmd, cwd=PY, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    return subprocess.run(cmd, cwd=PY, env=env).returncode


def take_lock(run: Path) -> bool:
    """Atomic per-run lock holding the orchestrator's pid; a lock whose owner is gone (killed or
    suspended machine) is stale and is taken over, so interrupted runs resume automatically."""
    lock = run / ".lock"
    for _ in range(2):
        try:
            lock.mkdir()
            (lock / "pid").write_text(str(os.getpid()))
            return True
        except FileExistsError:
            pid_file = lock / "pid"
            pid = int(pid_file.read_text()) if pid_file.exists() and pid_file.read_text().strip().isdigit() else None
            if pid is not None and (Path(f"/proc/{pid}").exists() or not Path("/proc").exists()):
                return False  # owner alive (or cannot tell: be conservative)
            stale = run / f".lock.stale.{os.getpid()}"
            try:
                os.rename(lock, stale)
            except OSError:
                return False
            shutil.rmtree(stale, ignore_errors=True)
    return False


def run_one(name: str, train_args: list):
    run = RESULTS / "runs" / name
    if (run / "test_standard.json").exists():
        print(f"skip {name} (done)", flush=True)
        return
    run.mkdir(parents=True, exist_ok=True)
    if not take_lock(run):
        print(f"skip {name} (running elsewhere; remove {run / '.lock'} if stale)", flush=True)
        return
    log = run / "stdout.log"
    resuming = (run / "resume.pt").exists()
    if not resuming:
        log.unlink(missing_ok=True)
    print(f"{'resume' if resuming else 'start'} {name}", flush=True)
    dev = ["--device", DEVICE] if "mlp" not in map(str, train_args) else []
    rc = sh(["train", "--name", name, *train_args, *EXTRA, *dev], log)
    if rc == 0:
        # final evaluation: checkpoint selected on VAL, reported on TEST (never used for selection)
        rc = sh(["eval-model", "--ckpt", run / "best.pt", "--split", "test", "--scenarios", "standard", "hard", *dev], log)
    shutil.rmtree(run / ".lock", ignore_errors=True)
    print(f"{'done' if rc == 0 else 'FAILED'} {name}", flush=True)


def pool(jobs, workers=None):
    with ThreadPoolExecutor(workers or WORKERS) as ex:
        list(ex.map(lambda j: run_one(*j), jobs))


def depth_jobs():
    # cheap MLP runs first (quick sanity feedback), then longest-first so the pool stays busy
    order = ["mlp", "res8", "res4", "res2", "cnn2"]
    return [(f"{a}_s{s}", ["--arch", a, "--seed", s, "--total_env_steps", STEPS])
            for a in order for s in SEEDS]


def algo_jobs(arch: str = ABLATION_ARCH):
    variants = {"nodouble": ["--no-double"], "nodueling": ["--no-dueling"], "nstep1": ["--n_step", 1]}
    jobs = [(f"{arch}-{v}_s{s}", ["--arch", arch, "--seed", s, "--total_env_steps", STEPS, *extra])
            for v, extra in variants.items() for s in SEEDS]
    if arch != "mlp":
        # input-representation control: same net on the raw 5-plane grid (no BFS distance fields)
        jobs += [(f"{arch}raw_s{s}", ["--arch", arch, "--obs", "grid", "--seed", s, "--total_env_steps", STEPS]) for s in SEEDS]
    return jobs


def main():
    what = sys.argv[1]
    if what == "depth":
        pool(depth_jobs())
    elif what == "algo":
        pool(algo_jobs())
    elif what == "algo_mlp":  # cheap: same ablation on the MLP
        pool(algo_jobs("mlp"), workers=1)
    elif what == "tabular":
        for s in SEEDS:
            if not (RESULTS / "runs" / f"tabular_s{s}" / "test_hard.json").exists():
                sh(["tabular", "--seed", s, "--episodes", 3000, "--test"])
    elif what == "baselines":
        for ag in ("random", "greedy-bfs", "legacy", "safe-heuristic"):
            for scen in ("standard", "hard"):
                for split in ("val", "test"):
                    sh(["baseline", "--agent", ag, "--scenario", scen, "--split", split])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
