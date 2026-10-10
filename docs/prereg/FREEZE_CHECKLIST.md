# Freeze checklist: implementation evidence (maintained by the cloud implementer)

Status of the code-side items of the preregistered architecture x n-step study. It records WHERE the evidence comes from; it does
not approve anything. The preregistration document itself (v0.3.2) is not in the repository until the freeze commit. Items that
need a person are left open. Last updated for commit `405c59f` plus this file.

Legend: **done** = evidence exists and is reproducible from the repository; **partial** = mechanism verified, the number or the
machine-specific part is still to be produced at the freeze; **open** = not done / to be filled by a person.

## A. Verified by tests in the repository (cloud, Linux CPU, clean-worktree runs of every commit)

| item | status | evidence |
|---|---|---|
| seed partitions (val 21000-21049, sealed test 30000-30299, smoke 40000-40009, run seeds 0-4 / 100-104 / 900,901 pairwise disjoint at k <= 300008); the v0.2 range is rejected; runtime episode-index guard | done | `tests/test_seed_partition.py` (`44ee39a`, spy fixed in `1635bc1`) |
| training / selection never reads the sealed test seeds | done | same file (dynamic spy + static source check) |
| sealed test: integrity manifest, explicit `--unseal`, one-shot, tamper detection; tests never read the real sealed seeds | done | `tests/test_seal.py` (`af879de`, layout `fcc73c2`) |
| n-step target pipeline vs independent oracle (hand literals, exact fractions, 6 planted bugs) | done (code); **human review open** | `tests/test_nstep_oracle.py`, `scripts/nstep_oracle_report.py` (`85758be`); implementer = verifier |
| refactor behaviour-preserving | done | identical tiny-training weights before/after (commit messages `85758be`, `ae5b668`) |
| matrix.csv registered file, 30 rows, six distinct configurations per seed block; order fixed by the file | done | `tests/test_prereg.py` (`a256798`, `fcc73c2`) |
| CSV-external parameters (eps_start/end/frac, tau, grad_clip) passed explicitly, equal to code defaults; per-run effective config | done | `tests/test_prereg.py` (`fcc73c2`) |
| validation de-duplication (15 x 50 at 300000/20000), best selection unchanged | done | `tests/test_provenance.py` (`d598b8a`) |
| replay.size and actual_updates recorded in `summary.json` | done | `tests/test_prereg.py::test_completed_run_has_the_contract_files` (`fcc73c2`) |
| eval output: separate last/best, never overwritten, `truncated`, `prereg-eval-1`, CPU 1 thread | done | `tests/test_evalrun.py` (`6a0f197`), `tests/test_seal.py` (`fcc73c2`) |
| run records: `code_version.json`, `environment.json` allow-list (no CPU brand/host/user/path), initial weight hash | done | `tests/test_provenance.py` (`d598b8a`) |
| formal runner: no test evaluation, no resume, failed attempts archived, env-var guard, fixed dispatch order | done | `tests/test_prereg.py` (`a256798`) |
| tie rule of the greedy action, CPU | done | `tests/test_tie_break.py` (`ae5b668`), torch 2.14.1 CPU: `[0,2,2,1,0]`->1, all equal->0 |
| analysis script on synthetic studies (F1-F8, E1-E13, stream hash, quantile, t constants) | done (code); **human review open** | `tests/test_prereg_analysis.py` (`9e46da1`); no real or old result was read |
| Windows peak-memory implementation | done | real Windows run of `c4bd147` (peak_memory() positive, `peak_memory_error` empty, working set about 508.9 MB, commit about 1500 MB), reported by the local executor |
| smoke profiles independent (run names, reports, resume-check directories) | done | `tests/test_prereg.py::test_quick_then_load...` (`22e0048`) |

## B. Evidence from the A1000 smoke trial (2026-10-09, local executor; pipeline / throughput / memory only, no decision from scores)

| item | status | evidence and caveat |
|---|---|---|
| GPU training path usable | done | quick profile: 12 runs (seeds 900/901, six configurations) completed on CUDA |
| initial-weight hash mechanism on the real GPU machine | **partial** | 6 (architecture, seed) pairs equal in the smoke; the **15 pairs of the formal matrix must be run at the freeze** on the frozen machine and recorded |
| interrupt / resume path | done | quick profile resume check passed (exploratory only; formal runs never resume) |
| tie rule on CUDA | done (smoke machine) | the CUDA cases of `tests/test_tie_break.py` pass on the A1000 machine; torch/CUDA/driver versions to be recorded at the freeze |
| throughput | **partial** | load profile: about 101 env steps/s per process (res8, two in parallel); cnn2 and res4 were not measured in load |
| full-replay memory, per process | done (res8) | peak working set about 2.5 GB, peak commit about 3.3 GB, replay filled to 100000; quick runs about 1540 MB are the PyTorch + CUDA baseline (buffer about 41 MB), load = baseline + about 1.0 GB replay |
| two-worker stability | done (res8 pair, 18.5 min) | system commit headroom about 2.2 GB with two processes, GPU utilisation 96-99 %, no errors, weights finite, 0 non-finite losses; the formal 30-run campaign length is not tested |
| GPU memory (VRAM) peak | **partial** | the report has `cuda_max_allocated_mb` / `cuda_max_reserved_mb`; the values were not relayed to the cloud side -- to be sent back |
| CPU evaluation time | done (smoke) | about 1-4 s per 10 episodes with 1 thread, depends on episode length; 300 episodes x 60 checkpoints must be re-estimated on the frozen machine |
| duration estimate | partial | res8 300000 steps about 55 min extrapolated; 30 trainings about 11-16 h (rough; re-check with the frozen version) |

## C. Still open (not filled in by the cloud implementer)

`machine_id`, `worker_count`, `code_commit`, `hard_enabled`, all frozen-file hashes (matrix, frozen config, preregistration and analysis
specification, analysis script), dependency-lock hash, driver and operating-system note, power / sleep settings confirmation, the
15 initial-hash pairs on the frozen machine, the VRAM numbers, the freeze approval record, and every human review field:

```
implementer (n-step oracle, analysis script, tooling): the cloud AI (same party as the test author)
human reviewer:        ____
review date:           ____
what was checked:      ____
freeze approval:       ____
```
