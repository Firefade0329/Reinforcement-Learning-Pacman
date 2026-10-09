# Preregistered study: architecture x n-step (tooling)

This directory holds the **machine-readable part** of the preregistered study of n-step (1 vs 3) on three
convolutional architectures (cnn2, res4, res8) with five training seeds. The preregistration *document* itself
is not here yet: it is committed once, as a timestamped freeze commit, after the freeze checklist is complete.
Until then `freeze_config.json` has `"status": "draft"` and the formal runner refuses to start.

| file | role |
|---|---|
| `matrix_v0.3.1.csv` | the 30 runs, **byte-identical** to the registered file (SHA-256 `5cbd4e7b…59f0dfe`, pinned in `pacman_rl/prereg.py` and tested) |
| `freeze_config.json` | seeds, fixed hyper-parameters not carried by the CSV, final-evaluation settings and the fields to fill at the freeze (machine, workers, frozen commit, analysis-script hash, ...) |

**Run order.** The order of the runs is fixed by the `order` column of the matrix file and the runner dispatches in
that order. It is not generated from any scheduling seed. The tests check the file's hash and that every seed block
(rows 6k+1..6k+6) holds the six distinct (architecture, n-step) configurations of one training seed.

**Seed partitions** (`python/pacman_rl/evaluate.py`): checkpoint selection `prereg_val` 21000-21049; sealed final test
`prereg_test` 30000-30299; smoke validation `smoke_eval` 40000-40009; training episodes `1_000_000*(run_seed+1)+k`
with run seeds 100-104 (formal) and 900/901 (smoke); the legacy-fidelity range 20000-20299 and the old study's 5000-5049 /
10000-10299 are not used. `python/tests/test_seed_partition.py` checks that all of them are pairwise disjoint.

## Commands (run from the repository root)

```
python python/scripts/prereg.py check                  # matrix hash/shape, frozen configuration, open fields
python python/scripts/prereg.py list                   # the 30 runs in order
python python/scripts/prereg.py smoke --profile quick  --device cuda   # 12 short runs, seeds 900/901, all 6 configurations
python python/scripts/prereg.py smoke --profile load   --device cuda   # 2 res8 runs in parallel, replay buffer filled
python python/scripts/prereg.py run                    # formal runs (refused until the configuration is frozen)
```

Formal runs: no test evaluation, no resume (an unfinished run is moved to `attempts/<run>/attempt_<k>/` and logged in
`attempts.jsonl`, then trained again from scratch), every training setting is passed explicitly from the matrix row and the
frozen configuration, and `PACMAN_*` environment variables that could override a setting make the runner refuse to start.
Each run directory gets `code_version.json`, `environment.json` (GPU model, software versions, threads, determinism
switches only), the initial weight hash in `train_log.jsonl`, and `run_complete.json` after it passes its checks.

Smoke runs write to `results_prereg_smoke/` (never to the formal `results_prereg/`) and produce `smoke_report.json`:
wall time, updates, stored replay samples, env-steps/s, peak process memory (Windows: working set and commit) and CUDA peaks,
CPU evaluation time of last/best on the smoke seeds, equality of the n=1/n=3 initial hashes and an interrupt/resume check.
Smoke scores are for plumbing only; nothing is selected or tuned from them.

## Smoke runs on the formal machine (what to run and what to send back)

1. `python python/scripts/prereg.py smoke --profile quick --device cuda`: 12 short runs (seeds 900/901, all six
   configurations); checks the GPU path, save/load, last/best CPU evaluation, equality of the n=1/n=3 initial hashes and the
   interrupt/resume path.
2. `python python/scripts/prereg.py smoke --profile load --device cuda`: two res8 runs in parallel with the replay buffer
   filled (110000 steps); read peak working set / commit and `cuda_max_*` in the report; repeat with the intended worker count.
3. Send back `results_prereg_smoke/smoke_report.json` (it holds only allow-listed environment fields and no paths) and the
   observed wall time.  Do not commit `results_prereg_smoke/` (it is git-ignored) and do not use smoke scores for any decision.
