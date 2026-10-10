#!/usr/bin/env bash
# One-command acceptance.
#   bash python/scripts/acceptance.sh --quick   smoke run (about 1-10 min, uses a throw-away results dir)
#   bash python/scripts/acceptance.sh           check the committed full results (results/)
set -euo pipefail
cd "$(dirname "$0")/.."            # python/
export PYTHONPATH="$PWD"
# Interpreter: $PYTHON if set, else the first of python3 / python that can run `--version` (on Windows `python3` may be the Microsoft Store
# alias, which exists but fails).
if [[ -n "${PYTHON:-}" ]]; then
  PY=$PYTHON
else
  PY=""
  for cand in python3 python; do
    if "$cand" --version >/dev/null 2>&1; then PY=$cand; break; fi
  done
  [[ -n "$PY" ]] || { echo "no working Python found (tried python3, python); set PYTHON=/path/to/python" >&2; exit 1; }
fi

if [[ "${1:-}" == "--quick" ]]; then
  TMP=$(mktemp -d); export PACMAN_RESULTS_DIR="$TMP"
  echo "== [1/5] unit + integration tests"
  $PY -m pytest tests -q
  echo "== [2/5] baselines on the validation split"
  for a in random greedy-bfs legacy safe-heuristic; do $PY -m pacman_rl.cli baseline --agent $a --split val; done
  echo "== [3/5] tabular Q (short)"
  $PY -m pacman_rl.cli tabular --episodes 300 --seed 0
  echo "== [4/5] tiny DQN runs (MLP + CNN) and checkpoint round-trip"
  for a in mlp cnn2; do
    $PY -m pacman_rl.cli train --name smoke_$a --arch $a --total_env_steps 4000 --learn_start 500 --eval_every 4000 --buffer 5000 --n_envs 4
  done
  echo "== [5/5] reproducibility: same checkpoint evaluated twice must give identical results"
  for a in mlp cnn2; do
    $PY -m pacman_rl.cli eval-model --ckpt "$TMP/runs/smoke_$a/best.pt" --split val
    cp "$TMP/runs/smoke_$a/val_standard.json" "$TMP/first_$a.json"
    $PY -m pacman_rl.cli eval-model --ckpt "$TMP/runs/smoke_$a/best.pt" --split val
    # NOT `cmp ... && echo`: a failing command in a non-final position of an AND list does not trigger `set -e`
    cmp "$TMP/first_$a.json" "$TMP/runs/smoke_$a/val_standard.json" || { echo "$a: two evaluations of the same checkpoint DIFFER"; exit 1; }
    echo "$a: identical"
  done
  rm -rf "$TMP"
  echo "QUICK ACCEPTANCE PASSED"
else
  $PY scripts/check_acceptance.py --run-tests
fi
