# Preregistered architecture x n-step study: results record (protocol v0.3.2)

This page is a readable copy of `README_RESULTS.md` of the results release. The data, the official analysis outputs and the process receipts are in the two GitHub releases below; this repository page adds nothing to them and changes no frozen file.

**Summary.** One Pacman map, three convolutional architectures (cnn2, res4, res8) x n-step in {1, 3} x five paired training seeds = 30 runs of 300,000 environment transitions each, run once under a frozen protocol (freeze commit `92bf82eca0dae731f7396ed5b4e887e4f3b200e4`, code commit `65199dfa120db8c522522b452ede367bf2814b8b`). Primary endpoint: last checkpoint, standard scenario, 300 sealed test seeds (30000-30299). **H1 (the gain of n=1 over n=3 on Res4 is at least 10 points): supported** (mean +70.85, 97.5 % t interval 49.52 to 92.18, 5/5 seeds positive). **H2 (|gain(Res8) - gain(CNN2)| >= 10): uncertain** (mean +45.77, 97.5 % t interval -29.68 to 121.21). No deviations from the protocol, no failed attempts. Mechanisms were not tested.

## 1. Question and protocol identity

- Question: how does the n-step return length (n = 1 vs n = 3) affect a DQN agent, and does the effect depend on the network architecture (cnn2 / res4 / res8)?
- Freeze commit F = `92bf82eca0dae731f7396ed5b4e887e4f3b200e4`; code commit C = `65199dfa120db8c522522b452ede367bf2814b8b` (the parent of F; the `python/` tree object is identical in both).
- External freeze record: GitHub release `prereg-v0.3.2-r1-freeze-92bf82eca0da`, asset `FREEZE_RECORD.json`, server creation time 2026-10-11T10:27:55Z; the first training job started at 10:29:26Z.
- Run matrix `docs/prereg/matrix.csv`, SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`; the hard scenario was not evaluated (`hard_enabled=false`).
- Sequence: 30 trainings (2026-10-11T10:29:26Z to 17:35:18Z, two in parallel, no failures, no reruns) -> pre-unseal manifest -> one-shot CPU final evaluation (17:49:22Z to 18:22:17Z) -> evaluation seal -> one-shot formal analysis -> descriptive window-diagnostics summary.

## 2. Primary endpoint (last checkpoint, standard scenario; mean over 5 training seeds)

| architecture | n=1 | n=3 | d = n1 - n3 | 95 % t | 97.5 % t | positive seeds |
|---|---:|---:|---:|---|---|---:|
| cnn2 | 168.07 | 137.82 | +30.24 | [-12.33, 72.81] | [-23.35, 83.84] | 4/5 |
| res4 | 214.95 | 144.10 | +70.85 | [53.91, 87.79] | [49.52, 92.18] | 5/5 |
| res8 | 195.66 | 119.65 | +76.01 | [38.46, 113.56] | [28.74, 123.28] | 5/5 |

Interaction c = d.res8 - d.cnn2: mean +45.77, sd 48.26, 95 % t [-14.16, 105.69], 97.5 % t [-29.68, 121.21], 95 % cross-bootstrap [2.02, 80.75].

## 3. Preregistered decisions (produced by the analysis script)

| item | label |
|---|---|
| H1 (d.res4 >= 10; lower bound of the 97.5 % t interval > 10) | **supported** |
| H2 (abs(c) >= 10) | **uncertain** |
| direction signal cnn2 / res4 / res8 | insufficient_evidence / supported_signal / supported_signal |
| interaction signal | insufficient_evidence (the t and bootstrap intervals disagree about zero; the original label is kept) |
| Res4 one-sided exact sign test | N=5, K=5, p = 1/32 = 0.03125 (a direction test; it does not decide H1/H2) |

## 4. Reviews

- The local executor recomputed everything independently from the 60 raw evaluation files; the results equal the official outputs.
- GPT (author of the specification, read-only) recomputed the table by hand from the per-seed table of the report; it equals the official outputs. It found a one-directional warning field in the output (see section 5).
- DSH (independent blind recomputation and materials audit): 503/503 compared items bit-identical, 763 displayed numbers consistent, 43,200 window-diagnostics comparisons identical; the closest decision boundary is at distance 1.11 and 192 perturbation scenarios produced no label flip.
- These are model/executor reviews, **not an independent human audit**. The human review fields (oracle, analysis script, literature check) remain with the owner and the advisor.

## 5. Errata and wording limits

- In `analysis.json`, the top-level field `primary_decisions.interaction_signal_method_sensitive_zero` warns in one direction only ("t supports, bootstrap crosses zero"). For method sensitivity use `endpoints/last_standard/effects/c/sensitivity/method_sensitive_zero` (true here). The frozen code was not changed.
- `analysis.json` has no `last_hard` key or `not_run` marker (`REPORT.md` states that the hard scenario was not run) and no separate `df` entry in `parameters`.
- Death rates and similar ranges are configuration means: n=3 gives 99.87 % / 99.07 % / 100 % (cnn2 / res4 / res8), n=1 gives 96.2 % / 89.2 % / 95.4 %; individual runs are not all inside these ranges.
- B1/B2 `p_later_mismatch_hge2` (windows with at least two actions only): for res4 n=3 it is 92.6 % in the first 20,000 transitions (90.5 % when all windows are counted) and about 7.8 % once epsilon has reached 0.05. It measures "executed action differs from the argmax of the acting online network at collection time", not an exploration rate and not the size of any off-policy bias. About 25.6 % (pooled 25.5 %) of windows that start greedy and contain a death also contain a later deviation; this is a co-occurrence, not a cause.
- `last_file_sha256` / `best_file_sha256` in `run_complete.json` are the hashes of the checkpoint files `last.pt` / `best.pt` (not of the evaluation files); checkpoints are not part of this bundle.

## 6. What must not be read into these results

- H1 must not be generalised to "n=1 is better than n=3 in general", "deeper is better" or "holds for all tasks" (one map, five training seeds, privileged BFS distance-field input, a fixed 300,000-step budget, unequal compute at equal budget).
- "H2 uncertain" must not be read as "no architecture x n-step interaction".
- Neither exploration strength nor off-policy correction was manipulated, so the explanation "n=3 is worse because exploratory actions enter the return" was not tested; any mechanism proposed after seeing the results is post-hoc.
- The best checkpoint, rankings, the bootstrap and B1/B2 are secondary or exploratory; the primary endpoint is the last checkpoint.

## 7. Disclosures and known limits (recorded at freeze time)

- Before the freeze, rehearsal runs of the formal seed block 100 (res4, n=1), each of at most about 75 seconds, were started in a throw-away clone; one reached a first validation point on `prereg_val`. None is part of the 30 formal runs and none was used for any selection.
- Untracked files (for example `python/sitecustomize.py`) are not detected by the clean-tree checks; the formal analysis re-checks only the format of the dependency snapshot, not the installed NumPy version (the bootstrap index-stream hash check covers any drift that changes numbers); two hand-written git object readers raise an uncaught exception on a damaged object database; one new test uses a weak assertion. None of these changes any number.

## 8. Where the evidence is

| what | where |
|---|---|
| freeze record (made before any training run) | GitHub release `prereg-v0.3.2-r1-freeze-92bf82eca0da`, asset `FREEZE_RECORD.json` (id 630446051, SHA-256 `c088b74f8a703c6ec015d694fb5d5b9f5241a7c90b57e031110fcc17ea0e19b9`) |
| results bundle (official analysis outputs, evaluation seal, per-run configuration / summary / training log / 300-episode evaluation records for last and best, process receipts, `MANIFEST_SHA256.txt`) | GitHub release `prereg-v0.3.2-r1-results-92bf82eca0da`, asset `prereg_results_bundle_92bf82ec.zip` (id 631720282, SHA-256 `c86048d7824695ee893fd57bc90263d8f47f35a11e9d49cdd8f55d3bfd5475ea`) |
| the frozen protocol texts | `docs/prereg/` at commit `92bf82eca0dae731f7396ed5b4e887e4f3b200e4` (Chinese originals, which govern); English reading copies of the protocol and the analysis specification, a protocol summary and translation notes are in `docs/translations/` |
| analysis script | `python/scripts/prereg_analysis.py` at the freeze commit (SHA-256 `28484e4966e6ad579fdf095d53e7ba9dac9a406279c5c5067c3395b1bdb29d35`) |

The repository `main` may move beyond the freeze commit; the runs, the evaluation and the analysis were made at the freeze commit, and `docs/prereg/freeze_manifest.json` there lists the SHA-256 of every frozen file.
