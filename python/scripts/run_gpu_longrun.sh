#!/usr/bin/env bash
# Longer, GPU-accelerated repeat of the experiment matrix.  Everything goes to its own results
# directory (default ../results_gpu) so it never mixes with the CPU matrix in ../results.
#
#   bash python/scripts/run_gpu_longrun.sh                       # 300k steps, cuda, 3 workers
#   PACMAN_STEPS=500000 PACMAN_WORKERS=2 bash python/scripts/run_gpu_longrun.sh
#
# Resumable: finished runs are skipped.  Conv nets run on the GPU, the MLP stays on the CPU.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
export PACMAN_RESULTS_DIR="${PACMAN_RESULTS_DIR:-$PWD/../results_gpu}"
export PACMAN_DEVICE="${PACMAN_DEVICE:-cuda}"
export PACMAN_STEPS="${PACMAN_STEPS:-300000}"
export PACMAN_WORKERS="${PACMAN_WORKERS:-3}"
PY=${PYTHON:-python3}

$PY -m pacman_rl.cli bench --device "$PACMAN_DEVICE"        # prints ms/update per architecture
mkdir -p "$PACMAN_RESULTS_DIR/reference"
cp ../results/reference/java_legacy.json "$PACMAN_RESULTS_DIR/reference/"
$PY scripts/run_experiments.py baselines
$PY scripts/run_experiments.py tabular
$PY scripts/run_experiments.py depth
$PY scripts/run_experiments.py algo_mlp
$PY scripts/run_experiments.py algo
$PY scripts/make_report.py                                   # -> $PACMAN_RESULTS_DIR/RESULTS.md
$PY scripts/check_acceptance.py
