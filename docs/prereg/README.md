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

**Seed partitions** (`python/pacman_rl/evaluate.py`): checkpoint selection `prereg_val` 21000-21049; "sealed" final test
`prereg_test` 30000-30299; smoke validation `smoke_eval` 40000-40009; training episodes `1_000_000*(run_seed+1)+k`
with run seeds 100-104 (formal) and 900/901 (smoke); the legacy-fidelity range 20000-20299 and the old study's 5000-5049 /
10000-10299 are not used. `python/tests/test_seed_partition.py` checks that all of them are pairwise disjoint.

**What "sealed" guarantees.** The default formal entry (`prereg.py final-eval` with a verified manifest and `--unseal`) does not read the test seeds
without both, and the covered training / selection paths are tested not to evaluate that partition. It is a protocol, not a security boundary:
the low-level Python API (constructing a token, calling the evaluation functions), the public seed constants and edits of the source are not
prevented from reading the seeds. The protection against that is the frozen commit, the manifest hashes, the one-shot rule and the written log;
the seal must not be described as "only `final-eval` can read the seeds".

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

A completed smoke run is reused only if it was trained with exactly the configuration requested now (steps, device, buffer, learn_start,
seed, ... compared with the `train_config.json` the run wrote) and with the same `python/` tree. Otherwise the run is `refused`, nothing is
trained or overwritten, the report says why, and the command exits with status 1: use another `--results-dir`. The report of a run that was
reused says so (`reused: true`, `throughput_source: "original training run (reused)"`), keeps the `origin` of the numbers (completion time,
attempt, device, commit, `python/` tree hash, hash of the training configuration) and the `original_training_minutes`, and separates this
invocation's cost (`invocation_seconds` per run, `wall_seconds`, `workers`). The exit status is 0 only if every run is done or validly reused
and the interrupt/resume check passed (`ok` in the report).

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

Difference from the specification text, pending a specification revision: the sample variance / standard deviation is computed in exact
rational arithmetic (`fractions.Fraction`) from the integer sums and converted to float once, whereas the specification text says float64 with
`math.fsum`. The implementation was deliberately not changed; the two are expected to differ only at floating-point rounding level (not measured separately), and the spec text should be revised
to describe the exact path (or the code changed on request).

What the outputs contain beyond the statistics (ANALYSIS_SPEC section 7): for every endpoint the per-seed integer counts and sources
(run, file, SHA-256, 300 test seeds, integer sum) of the death / win / truncation rates and mean steps; model, rate and effect tables for
`best_standard` and, when enabled, `last_hard`; per run the optional resource fields of `summary.json` (minutes, memory peaks) with their
source field, or `null` with a reason; per run the archived failed attempts of the evaluation seal; and `deviations`, which lists only what a
record states: entries declared in the freeze manifest (optional `deviations` array of `{id, description, source}`, written with
`freeze-manifest --deviations-file`) and every archived failed attempt. The script never infers a deviation from the data. The report's
claim about number sources is limited to what the JSON actually keeps (statistic objects: metric/formula/parents/integer numerators;
resource numbers: the summary field; constants: `parameters`).

## Freeze identity: code commit C and freeze commit F

The frozen configuration records `code_commit` in a tracked file, so it cannot name the commit that contains it. The study therefore
uses two commits: **C**, the code commit named by `code_commit`, and **F**, the commit the runs are made from (`HEAD`), which is C or a
descendant that adds only freeze material (the frozen configuration, `freeze_manifest.json`, the preregistration / specification /
hand-over texts and the checklist). Procedure: commit the code (C); put C into `code_commit`, prepare the manifest and texts; commit them
(F). `prereg.py run` and the final evaluation require: C exists and is an ancestor of (or equal to) HEAD, the `python/` tree is identical at C
and HEAD, `matrix.csv` is unchanged, every file that differs between C and HEAD is freeze material, and the tracked working tree is clean.
Runs store C (`config.json`, evaluation `meta.code_commit`, `run_complete.json`) and F (`run_complete.json` `freeze_commit`, `code_version.json`
`git_sha`); the external freeze record keeps F. No field was added to the frozen configuration.

## Freeze material is enforced, not just listed

* `freeze-manifest` always puts the preregistration text and the analysis specification (`PREREG_ARCH_NSTEP_v0.3.2.md`,
  `ANALYSIS_SPEC_v0.3.2.md`) into `frozen_files`, whatever `--extra-frozen` says, and refuses to write a manifest if either is missing.
* In `--mode formal` the analysis script requires both texts in the manifest, requires the frozen configuration to carry `status: "frozen"`
  (`"synthetic"` for synthetic mode; a draft cannot pass as either), and compares the bytes of the script that is actually running with the hash
  the manifest locked for `analysis_script_path`.
* `final-eval` repeats the training gate before it reads the sealed seeds: no `PACMAN_*` overrides, a frozen configuration, a legitimate
  freeze state (see above), a clean tracked tree, and `HEAD` equal to the freeze commit F that every run recorded. It then saves the machine
  and environment of the evaluation (device, software versions, thread count, code version, the gate's result) in
  `results_prereg/final_eval_environment.json`, once, as a separate file; the evaluation files' `meta` contract is unchanged.

## Window record B1 / B2 (descriptive, secondary)

For the n-step windows that enter the replay, the optional record states how often the LATER actions of a window deviate from the greedy
action that was selected when they were taken (B1), and how often a window that contains an actual death (`info["died"]`, read before the
reset) also contains such a deviation after a greedy start (B2, a descriptive co-occurrence). Definition details:

* `U = 1[executed action != the argmax the trainer used for that collection batch]` (`action_mismatch_to_selected_greedy`); it is the mismatch with
  the SELECTED greedy action, ties are not treated specially; a random branch that hits the greedy action is `U = 0`. The start action is recorded
  separately and is not part of `L` (later deviation). The bootstrap action at the end is not a window action.
* A window is counted once, when it enters the replay (not per gradient sample); windows are attributed to the 20000-transition bin of their START
  (batch start + environment index + 1); a short window flushed at a termination or truncation has its own `h`; nothing crosses a reset; tails still
  queued when the budget ends are reported as pending (nothing is flushed for the record). Death comes from `info["died"]`, never from the reward or
  from `terminated`; the known death-penalty component is `-10 * gamma^j`.
* Output per run: `runs/<run_name>/window_diagnostics.json` (schema `window-diagnostics-1`: per bin and `h` the [G][L][D] counts, J / P counts, end-kind
  counts, start-epsilon sum / min / max, pending per start bin, independent death-event counts, all rates with numerator / denominator, `null` +
  `no_eligible_windows` at a zero denominator, no NaN) and, during the run, `window_diagnostics.partial.json` (replaced at each validation, removed at the end).
  Neither name falls under the forbidden prefixes of the integrity check.
* Switch: `prereg.py run|smoke --window-diagnostics` / `cli train --window-diagnostics` / `train(..., window_diagnostics=True)`. It is NOT part of the
  configuration: `TrainConfig`, `config.json`, the effective configuration and the frozen configuration are unchanged, and the record's presence or
  absence changes no integrity check and no H1 / H2 number (tests). A resumed run writes no record.
* The recorder uses only arrays the training loop already has; it calls no model, draws no random number and adds nothing to the replay. The wiring is
  tested for exact equality of the run with and without it on the CPU; the cost on the GPU machine is NOT estimated here and must be measured
  (acceptance: median wall-clock overhead <= 5 %, extra main memory <= 16 MiB per process; see `FREEZE_CHECKLIST.md`).
* After the 30 runs: `python python/scripts/window_diagnostics_summary.py seal` (separate `window_diagnostics_seal.json`; it is not part of the
  evaluation seal or the analysis input), then `summarize --out-dir ...` for the central description: per configuration the five per-run rates, mean and
  sd (ddof=1) over the runs with a defined rate (k of 5) and the pooled ratio as a separate quantity, per `h` and over the 15 start bins. No tests,
  intervals or rankings; findings suggested by it are post-hoc explanations.

## Freeze binding check (before any formal run and before the final evaluation)

Both formal entries (`prereg.py run` and `prereg.py final-eval`) run the same check before they create a training task, a model, a subprocess,
an environment step, an unseal permission or any evaluation (`pacman_rl/freeze_binding.py`, standard library only). It reads only
`docs/prereg/frozen_config_v0.3.2.json` and `docs/prereg/freeze_manifest.json` under the project root and refuses (exit status non-zero, nothing
started) unless: the manifest exists, is valid JSON without duplicate keys, has `synthetic: false` and `complete: true`; its `code_commit` equals the
configuration's `code_commit` (C); every entry of `frozen_files` is a relative path inside the project whose file exists and whose raw working-tree
SHA-256 equals the recorded value (all entries, extra-frozen ones included), the registered matrix hash is the matrix entry, and the required files
(matrix, configuration, preregistration text, analysis specification, the analysis script and the dependency lock named by the manifest) are listed;
and the three configuration fields `to_fill_at_freeze.analysis_script_sha256 / preregistration_document_sha256 / dependency_lock_sha256` equal the
manifest entries of those files (all zeros is not a binding). A success leaves `checked_utc`, HEAD (F), C, the manifest hash and the number of files
checked in `results_prereg/preflight_log.jsonl` (training) and in the final-evaluation environment evidence. The manifest generator
(`freeze-manifest`) applies the same rules to the manifest it is about to write and does not need an older manifest. The manifest does not list itself;
its own hash belongs in the external freeze record. A manifest regenerated after F is a different freeze (F'), not F.

## Byte contract: `-text` for every frozen file

The only hashed object is a file's raw working-tree bytes (SHA-256; no newline normalisation, no BOM stripping, JSON not re-serialised). `.gitattributes`
(committed with the code commit C, hashed itself, not one of the six files F may add or change) sets `-text` for `.gitattributes`, `docs/prereg/**`,
`python/**/*.py` and the requirement files, so a fresh checkout returns the committed bytes whatever `core.autocrlf` is (the rehearsal found 3 of 7
hashes changed on a Windows clone with `autocrlf=true`). `matrix.csv` keeps its registered CRLF bytes (`5cbd4e7b…0dfe`); the repository is NOT
renormalised and no hash expectation was redefined. An existing working tree is not repaired by `-text`: the formal machine verifies a FRESH clone of
F (every frozen file's bytes and hash, the manifest's own hash, the effective `text` attribute, `core.autocrlf` state; no absolute paths in the record).
Any extra-frozen path must be covered by a rule before the freeze: the manifest generator refuses a frozen path without `-text`
(`git check-attr text` must say `unset`). Tests: `tests/test_gitattributes.py` (temporary repositories, `core.autocrlf` true and false, the real matrix
bytes, a control without the attributes that reproduces the rehearsal's finding).

## Dependency snapshot (`docs/prereg/dependency_lock.txt`)

The complete runtime snapshot has ONE fixed name, `docs/prereg/dependency_lock.txt`. It is generated by the local executor with the accepted
interpreter's `python -m pip freeze --all` (the cloud implementer neither generates nor edits its content; the repository's tests use clearly fake
fixtures), committed with the code commit C, and is NOT one of the six files that F may add or change. Format (checked by the generator and by
both formal entries): UTF-8 without BOM, LF only, one `name==exact_version` per line (local suffixes like `+cu126` kept), sorted by lower-cased name
(the order of `pip freeze`), no blank, comment, option, URL, editable or range line, unique names, one final newline, at least numpy, torch, matplotlib
and pytest. `manifest.dependency_lock_path` must be this path, `to_fill_at_freeze.dependency_lock_sha256` is its hash, and it must exist in C's tree (a file
that first appears in F, or differs in F, is refused). `python/scripts/prereg_analysis.requirements.txt` (the analysis NumPy pin) is frozen
separately as another required file and can never stand in for the snapshot, nor can `python/requirements.txt` (lower bounds only). The format check cannot
show that the snapshot is complete; the per-package comparison with the accepted environment is the local executor's record.
