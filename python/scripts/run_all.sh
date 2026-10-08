#!/usr/bin/env bash
# Full reproduction of every number in docs/RESULTS.md (several hours on 4 CPU cores).
# Resumable: finished runs are skipped.  Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
PY=${PYTHON:-python3}
$PY -m pytest tests -q
$PY scripts/run_experiments.py baselines
$PY scripts/run_experiments.py tabular
$PY scripts/run_experiments.py depth
$PY scripts/run_experiments.py algo
$PY scripts/make_report.py
$PY scripts/check_acceptance.py --run-tests
