# Preregistered study: architecture x n-step (tooling)

This directory holds the **machine-readable part** of the preregistered study of n-step (1 vs 3) on three
convolutional architectures (cnn2, res4, res8) with five training seeds. The preregistration *document* itself
is not here yet: it is committed once, as a timestamped freeze commit, after the freeze checklist is complete.
Until then `frozen_config_v0.3.2.json` has `"status": "draft"` and the formal runner refuses to start.

| file | role |
|---|---|
| `matrix.csv` | the 30 runs, **byte-identical** to the registered file under its original name (SHA-256 `5cbd4e7b…59f0dfe`, pinned in `pacman_rl/prereg.py` and tested); never renamed or copied because of a document version |
| `frozen_config_v0.3.2.json` | field names of ANALYSIS_SPEC 2.1: the five hyper-parameters the CSV does not carry (`eps_start/eps_end/eps_frac/tau/grad_clip`), the explicit seed arrays (checked against the constants the code uses), final-evaluation device/threads, `hard_enabled`, and the fields to fill at the freeze (`machine_id`, `worker_count`, `code_commit`, analysis-script hash, ...) |
| `freeze_manifest.json` | written at the freeze by `prereg.py freeze-manifest` (clean tree, hashes of the frozen files; `project_root` is `"."`, resolved against an explicit root, so no machine path is committed) |

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

Smoke runs write to `results_prereg_smoke/` (never to the formal `results_prereg/`) and produce `smoke_report_<profile>.json`:
wall time, updates, stored replay samples, env-steps/s, peak process memory (Windows: working set and commit) and CUDA peaks,
CPU evaluation time of last/best on the smoke seeds, equality of the n=1/n=3 initial hashes and an interrupt/resume check.
Smoke scores are for plumbing only; nothing is selected or tuned from them.

## Smoke runs on the formal machine (what to run and what to send back)

The two profiles are independent: run names carry the profile (`runs/smoke_quick_<arch>_n<N>_s<seed>`, `runs/smoke_load_...`), each
writes its own `smoke_report_<profile>.json` and `interrupt_check_<profile>/` into the same `results_prereg_smoke/`, and either order
works. Running one profile again skips only its own completed runs and rewrites only its own report. (Before this was fixed the two
profiles shared run names, so `load` after `quick` skipped its runs and overwrote the report.)

1. `python python/scripts/prereg.py smoke --profile quick --device cuda`: 12 short runs (seeds 900/901, all six
   configurations, 2000 steps each, buffer 4000); checks the GPU path, save/load, last/best CPU evaluation, equality of the
   n=1/n=3 initial hashes (6 pairs here, 15 at the freeze) and the interrupt/resume path.
   Output: `results_prereg_smoke/smoke_report_quick.json`.
2. `python python/scripts/prereg.py smoke --profile load --device cuda`: two res8 runs in parallel with the replay buffer
   filled (110000 steps, buffer 100000); read peak working set / commit and `cuda_max_*` in the report; repeat with the intended
   worker count. Output: `results_prereg_smoke/smoke_report_load.json`.
3. Send back the report(s) (they hold only allow-listed environment fields and no paths) and the observed wall time.  Do not
   commit `results_prereg_smoke/` (it is git-ignored) and do not use smoke scores for any decision.

**Reading the memory numbers.** Every run is its own subprocess and the reported peaks are per process, not summed. On the
RTX A1000 laptop (Windows) a `quick` run peaks at about 1540 MB working set: that is the PyTorch + CUDA
process baseline (its 4000-sample buffer is only about 41 MB). The `load` runs peak at about 2.5 GB working set and 3.3 GB
commit, which is the same baseline plus the roughly 1.0 GB a 100000-sample uint8 replay buffer needs, so the two profiles agree.
Do not read the `quick` numbers as the memory need of a formal run.

**What the quick profile is.** The quick driver sets `learn_start=500`, `buffer=4000` and `eval_every=1000` explicitly, so within
its 2000 steps the runs DO perform gradient updates (`actual_updates` in each run's `summary.json` must be greater than 0; keep the
effective smoke configuration of every run with the report). It exercises a short pipeline only: it is not a filled replay buffer and
says nothing about stability over 300000 steps.

**How the load profile differs from the formal protocol.** It is not a scaled-down copy of it. Validation uses the `smoke_eval` seeds with
10 episodes per validation (formal: 15 validations x 50 episodes = 750), and `eps_frac=0.4` together with 110000 steps anneals epsilon over
44000 steps (formal: over 120000 steps). Treat its throughput, memory and the extrapolated durations (res8 300000 steps about 55 min; the
30 trainings about 11-16 h) as rough planning figures; they must be re-measured on the frozen candidate version before the freeze.

## Run directory layout (formal runs, `results_prereg/runs/<run_name>/`)

`config.json` (merged effective configuration: every CSV column, the five CSV-external settings, the frozen supplementary values,
`run_name`, `code_commit`, `frozen_config_sha256`; what `train()` itself wrote is kept as `train_config.json`), `summary.json`
(`run_name`, `total_env_steps`, `replay.size`, `actual_updates`, the 15 `validation_steps`, `validation_episodes_each`,
`initial_state_dict_sha256`, `checkpoints.last/best` with step and canonical weight hash, plus the earlier fields),
`last.pt`, `best.pt`, `train_log.jsonl`, `code_version.json`, `environment.json`, `run_complete.json`, and after the sealed final
evaluation `last/standard.json`, `best/standard.json` (and `last/hard.json` only if the frozen configuration enables hard) in the
`prereg-eval-1` format (`schema_version`, `meta`, `records` with the `truncated` field). `results_prereg/evaluation_seal.json`
(`prereg.py seal-eval`) lists the SHA-256 of every file the analysis reads. Tie-break of the greedy action: see `docs/PLAN.md`
deviation 9.

## Analysis script (ANALYSIS_SPEC_v0.3.2)

`python/scripts/prereg_analysis.py analyze --mode synthetic|formal --manifest ... --input-root ... --output-dir ... [--project-root ...]`
(numpy only; `prereg_analysis.requirements.txt` pins the NumPy version for which the contracted bootstrap index stream was checked).
It reads only the files named by the freeze manifest and the evaluation seal, validates every input before computing anything
(exit code 2 and a JSON error on stderr, no output directory left behind), and writes `REPORT.md`, `analysis.json`,
`bootstrap_replicates.csv`, `bootstrap_indices.sha256` and `input_manifest.json` atomically. Before the freeze it is run on
synthetic studies only (`python/tests/test_prereg_analysis.py`, fixtures F1-F8 and malformed inputs E1-E13 of the specification
section 8, with hand-derived expected values); no real or old result is ever read. The human sign-off fields (reviewer, date, what was
checked, freeze approval) are intentionally not filled in by the code or its author.
