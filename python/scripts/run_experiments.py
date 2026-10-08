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
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PY = Path(__file__).resolve().parents[1]
RESULTS = Path(os.environ.get("PACMAN_RESULTS_DIR") or PY.parent / "results")
SEEDS = (0, 1, 2)
ARCHS = ("mlp", "cnn2", "res2", "res4", "res8")
ABLATION_ARCH = "res4"  # fixed a priori (middle depth, affordable); see PLAN.md section 9, deviation 4
STEPS = 120_000  # env transitions per run; see docs/PLAN.md section 9 for the budget rationale


def sh(args, log: Path | None = None):
    cmd = [sys.executable, "-m", "pacman_rl.cli", *map(str, args)]
    env = {**os.environ, "PYTHONPATH": str(PY), "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as f:
            return subprocess.run(cmd, cwd=PY, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    return subprocess.run(cmd, cwd=PY, env=env).returncode


def run_one(name: str, train_args: list):
    run = RESULTS / "runs" / name
    if (run / "test_standard.json").exists():
        print(f"skip {name} (done)", flush=True)
        return
    log = run / "stdout.log"
    log.unlink(missing_ok=True)
    print(f"start {name}", flush=True)
    rc = sh(["train", "--name", name, *train_args], log)
    if rc == 0:
        # final evaluation: checkpoint selected on VAL, reported on TEST (never used for selection)
        rc = sh(["eval-model", "--ckpt", run / "best.pt", "--split", "test", "--scenarios", "standard", "hard"], log)
    print(f"{'done' if rc == 0 else 'FAILED'} {name}", flush=True)


def pool(jobs, workers=4):
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda j: run_one(*j), jobs))


def depth_jobs():
    # cheap MLP runs first (quick sanity feedback), then longest-first so the pool stays busy
    order = ["mlp", "res8", "res4", "res2", "cnn2"]
    return [(f"{a}_s{s}", ["--arch", a, "--seed", s, "--total_env_steps", STEPS])
            for a in order for s in SEEDS]


def algo_jobs():
    arch = ABLATION_ARCH
    variants = {"nodouble": ["--no-double"], "nodueling": ["--no-dueling"], "nstep1": ["--n_step", 1]}
    jobs = [(f"{arch}-{v}_s{s}", ["--arch", arch, "--seed", s, "--total_env_steps", STEPS, *extra])
            for v, extra in variants.items() for s in SEEDS]
    # input-representation control: same net on the raw 5-plane grid (no BFS distance fields)
    jobs += [(f"{arch}raw_s{s}", ["--arch", arch, "--obs", "grid", "--seed", s, "--total_env_steps", STEPS]) for s in SEEDS]
    return jobs


def main():
    what = sys.argv[1]
    if what == "depth":
        pool(depth_jobs())
    elif what == "algo":
        pool(algo_jobs())
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
