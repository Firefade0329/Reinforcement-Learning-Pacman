# Freeze checklist: implementation evidence (maintained by the cloud implementer)

Status of the code-side items of the preregistered architecture x n-step study. It records WHERE the evidence comes from; it does
not approve anything. The preregistration document itself (v0.3.2) is not in the repository until the freeze commit. Items that
need a person are left open. Last updated for commit `09ea358` plus the documentation commits that follow it.

Legend: **done** = evidence exists and is reproducible from the repository; **partial** = mechanism verified, the number or the
machine-specific part is still to be produced at the freeze; **open** = not done / to be filled by a person.

## A. Verified by tests in the repository (implementer-reported; machine / command / log identification: see the commit messages)

| item | status | evidence |
|---|---|---|
| seed partitions (val 21000-21049, sealed test 30000-30299, smoke 40000-40009, run seeds 0-4 / 100-104 / 900,901 pairwise disjoint at k <= 300008); the v0.2 range is rejected; runtime episode-index guard | done | `tests/test_seed_partition.py` (`44ee39a`, spy fixed in `1635bc1`) |
| the covered training / selection paths do not evaluate the sealed partition | done (covered paths) | same file: dynamic spy on `evaluate_batched` during training with each selection set, and a static (AST) check that covers the `dqn` module only; other modules are not covered by the static check |
| sealed test: integrity manifest, explicit `--unseal`, one-shot, tamper detection; tests never read the real sealed seeds | **partial** | `tests/test_seal.py` (`af879de`, layout `fcc73c2`). Stays partial until the finding P1-02 of the conformance review is fixed (as reported by the GPT review of `09ea358`; its text is not in this repository and is not paraphrased here). The guard prevents accidents; it is not an unbypassable security boundary (code and seeds are public) |
| n-step target pipeline vs independent oracle (hand literals, exact fractions, planted bugs) | done (code); **human review open** | `tests/test_nstep_oracle.py`, `scripts/nstep_oracle_report.py` (`85758be`); implementer = verifier. The code contains **6** built-in variants (`plain_max_instead_of_double`, `truncation_not_bootstrapped`, `discount_exponent_n_instead_of_h`, `tail_not_flushed`, `queue_shared_across_envs`, `reset_observation_stored_as_next`), exercised in memory by `test_the_oracle_catches_each_planted_bug`, which is part of the full suite. The cloud implementer additionally reverted three pieces of the REAL source (target network choosing the action, post-reset observation stored, truncation not bootstrapped) and saw the tests turn red (numbers in the `85758be` message). The local executor independently made **4 own mutations** of the n-step target path and all were caught; the local side did **not** re-run each of the 6 built-in variants by editing the source. Do not read this as "all 6 verified locally". At the freeze, list the variant names, the commit and the actual pass record |
| refactor (`td_target`, `collect_step`, `greedy_actions`): identical final weights before/after for the specified tiny configurations | done (limited) | commit messages `85758be`, `ae5b668`: tiny CPU trainings (mlp and cnn2 with the default recipe; mlp n_step 1 / no-double, cnn2 n_step 1, mlp n_step 5 / no-dueling). This is evidence for THAT finite set only; it does not prove that all parameters, devices or boundary behaviours are unchanged |
| matrix.csv registered file, 30 rows, six distinct configurations per seed block; order fixed by the file | done | `tests/test_prereg.py` (`a256798`, `fcc73c2`) |
| CSV-external parameters (eps_start/end/frac, tau, grad_clip) passed explicitly, equal to code defaults; per-run effective config | done | `tests/test_prereg.py` (`fcc73c2`) |
| validation de-duplication (15 x 50 at 300000/20000), best selection unchanged | done | `tests/test_provenance.py` (`d598b8a`) |
| replay.size and actual_updates recorded in `summary.json` | done | `tests/test_prereg.py::test_completed_run_has_the_contract_files` (`fcc73c2`) |
| eval output: separate last/best, never overwritten, `truncated`, `prereg-eval-1`, CPU 1 thread | done | `tests/test_evalrun.py` (`6a0f197`), `tests/test_seal.py` (`fcc73c2`) |
| run records: `code_version.json`, `environment.json` allow-list (no CPU brand/host/user/path), initial weight hash | done | `tests/test_provenance.py` (`d598b8a`) |
| formal runner: no test evaluation, no resume, failed attempts archived, env-var guard, fixed dispatch order | done | `tests/test_prereg.py` (`a256798`) |
| tie rule of the greedy action, CPU | done | `tests/test_tie_break.py` (`ae5b668`), torch 2.14.1 CPU: `[0,2,2,1,0]`->1, all equal->0 |
| analysis script on synthetic studies (F1-F8, E1-E13, stream hash, quantile, t constants) | **partial**; human review open | `tests/test_prereg_analysis.py` (`9e46da1`); no real or old result was read. All fixture and error numbers are present, but for F2-F6 the per-configuration `m` values and the secondary endpoints (rates, steps) are not asserted one by one (F1 only partly), and a non-zero best-minus-last case is not covered (the synthetic best files copy last). Partial until those assertions are added |
| Windows peak-memory implementation | done | real Windows run of `c4bd147` (peak_memory() positive, `peak_memory_error` empty, working set about 508.9 MB, commit about 1500 MB), reported by the local executor |
| smoke profiles independent (run names, reports, resume-check directories) | done | `tests/test_prereg.py::test_quick_then_load...` (`22e0048`) |

## B. Evidence from the A1000 smoke trial (2026-10-09, local executor; pipeline / throughput / memory only, no decision from scores)

| item | status | evidence and caveat |
|---|---|---|
| GPU training path usable (short pipeline) | done | quick profile: 12 runs (seeds 900/901, six configurations) completed on CUDA. The quick driver sets `learn_start=500`, `buffer=4000`, `eval_every=1000` explicitly, so gradient updates DO happen within the 2000 steps. At the freeze, keep each run's effective smoke configuration and `actual_updates` (must be > 0). It proves a short pipeline only -- not a filled replay buffer and not stability over 300000 steps |
| initial-weight hash on the real GPU machine | **partial** | the smoke's 6 (architecture, seed) pairs are NOT evidence for the formal 15 pairs (different seeds, possibly different dependencies). Needed: a construct-only check (no training) of the formal 15 pairs on the frozen machine with the frozen dependencies, **before the first formal training**, recording the hashes |
| interrupt / resume path | done | quick profile resume check passed (exploratory only; formal runs never resume) |
| tie rule on CUDA | done (smoke machine) | the CUDA cases of `tests/test_tie_break.py` pass on the A1000 machine; torch/CUDA/driver versions to be recorded at the freeze |
| throughput | **partial** | load profile: about 101 env steps/s per process (res8, two in parallel); cnn2 and res4 were not measured in load. **The load profile is not a scaled-down formal protocol:** validation uses `smoke_eval` with 10 episodes per validation (formal: 15 x 50 = 750 episodes) and `eps_frac=0.4` with 110000 steps anneals epsilon over 44000 steps (formal: 120000) |
| full-replay memory, per process | done (res8) | peak working set about 2.5 GB, peak commit about 3.3 GB, replay filled to 100000; quick runs about 1540 MB are the PyTorch + CUDA baseline (buffer about 41 MB), load = baseline + about 1.0 GB replay |
| two-worker stability | done (res8 pair, 18.5 min) | system commit headroom about 2.2 GB with two processes, GPU utilisation 96-99 %, no errors, weights finite, 0 non-finite losses; the formal 30-run campaign length is not tested. **Before the freeze:** check, on the frozen candidate version, the load while checkpoints are being written, with a filled replay buffer and (if adopted) the added log version |
| GPU memory (VRAM) peak | **partial** | values supplied by the local executor; the original reports and a re-check on the final version are still to be added. torch allocated / reserved (MiB): res8 about 34 / 46 (quick and load agree), res4 about 21 / 46, cnn2 about 10 / 24. `nvidia-smi` showed about 354 MiB, which includes the CUDA context and cannot be added to the torch numbers. Source: the `summary.json` of the runs of the local A1000 smoke |
| CPU evaluation time | done (smoke) | about 1-4 s per 10 episodes with 1 thread, depends on episode length; 300 episodes x 60 checkpoints must be re-estimated on the frozen machine |
| duration estimate | partial | res8 300000 steps about 55 min is a rough extrapolation from a profile that differs from the formal protocol (see throughput); 30 trainings about 11-16 h **must be re-measured on the frozen candidate version** |

## C. Open items (nothing below is filled in or approved by the cloud implementer)

Fields of the frozen configuration / freeze manifest: `machine_id`, `worker_count`, `code_commit`, `hard_enabled`, all frozen-file hashes
(matrix, frozen config, preregistration and analysis specification, analysis script), dependency-lock hash, driver and operating-system
note, power / sleep settings confirmation.

| item | status | what is needed |
|---|---|---|
| freeze identity | open (mechanism implemented) | the code commit C in `code_commit` and the freeze commit F = HEAD (see `docs/prereg/README.md`); the external freeze record keeps F; a clean tree, hashes of the frozen documents / matrix / configuration / analysis script / dependency lock, written into a timestamped freeze record that cannot be modified silently; a change after the freeze needs a stated reason and time |
| re-check before unsealing | open | all 30 runs complete (exactly 300000 steps each), checkpoints and configurations re-verified against the freeze, the 15 initial-hash pairs on record, the evaluation seal and analysis hashes matching -- immediately before the sealed seeds are read |
| 15 initial-hash pairs, before the first formal training | open | see section B (construct-only check on the frozen machine and dependencies, not a result of the 30 trainings) |
| software and command record | open | Python, torch / CUDA, NumPy and the analysis dependencies locked; devices and thread counts for training, validation and the final evaluation; determinism / TF32 and related switches; the exact commands, the effective configuration and the worker count; nothing may rely on an unrecorded default |
| environment / recipe change list | open | what changed against the earlier phase and what did not: validation de-duplication applies to every new training path, seed injection (`val_set`), output and terminal-state fields (`truncated`, summary fields). The code version of each OLD run is not claimed to be known item by item |
| counting consistency | open | per run exactly 300000 environment steps, 15 x 50 validation, the note on pending tail items (n=3 with 8 environments: up to 16 not yet emitted), actual updates and `replay.size`, non-finite weights / losses, the re-run rule |
| final evaluation and hard scenario | open | `hard_enabled` decided before unsealing; the final CPU machine with 1 thread and the measured evaluation parallelism recorded; the sealing / unsealing order; all 30 runs and the 15 pairs proven; no model selection back from test results; the final evaluation also runs on the frozen machine and the machine / environment evidence of that moment is saved |
| management of runs after the freeze | open | no stopping and no re-running because of scores; objective infrastructure failure versus algorithmic failure (NaN, non-convergence) kept apart; a core defect forces one unified revision and re-run of the matrix; the frozen draft is not edited silently; unsealing only after all 30 trainings are complete |
| one-shot formal analysis | open | the single formal run of the frozen analysis, its record, and the recovery rule for objective file or evaluation failures (same weights, same protocol, attempts logged) |
| literature check (section 9 of the preregistration) | open, **human** | the owner or the advisor reads the original papers / chapter; record who, when, the version, the location in the source, the exact statement and the level of what could not be verified. The AI does not sign this |
| B1 / B2 window record (descriptive, secondary) -- implementation | implemented in the repository; adoption pending the overhead acceptance below | B1 = share of windows whose later actions deviate from the greedy action selected at their time; B2 = co-occurrence of an actual death (`info["died"]`) with such a deviation (a descriptive co-occurrence metric, not a design change, not a bias or attribution measure). Definition, recorder, tests: `pacman_rl/window_diag.py`, `tests/test_window_diag*.py`; switch `--window-diagnostics` (not a configuration field); summary and its own seal: `scripts/window_diagnostics_summary.py`. Implementer and test author are the same AI model; hand-computed expectations are not an independent audit. Does not enter H1 / H2 and changes no training parameter |
| B1 / B2 window record -- on / off consistency | done (CPU, in the test suite) | `tests/test_window_diag_wiring.py`: identical actions, RNG states, stored windows and their order, updates, losses, online / target / optimizer state, best step and weights; no extra model call, torch random, training-rng call, `.item()` / `.cpu()` |
| B1 / B2 window record -- overhead on the A1000 | **open (local executor)** | quick (all 6 configurations) off / on pairs and load (2 res8 runs, buffer filled) off / on, at least two pairs in alternating order, separate output directories; thresholds: median wall-clock overhead <= 5 %, extra main-memory peak <= 16 MiB per process; no estimate is a measurement. If not met, B1 / B2 is postponed and no training parameter changes |
| B1 / B2 window record -- freeze decision | open, **human** | whether the 30 formal runs use `--window-diagnostics` (recorded in the freeze record; a frozen-configuration field for it has NOT been added: it would need an owner decision), the hash of `window_diag.py` / the summary script in the freeze manifest, and `window_diagnostics_seal.json` after the 30 runs |

```
implementer (n-step oracle, analysis script, tooling): the cloud AI (same party as the test author)
human reviewer:        ____
review date:           ____
what was checked:      ____
freeze approval:       ____
```
