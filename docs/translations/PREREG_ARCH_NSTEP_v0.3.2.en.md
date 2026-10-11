> This is a translation for readers. The Chinese original (SHA-256 3030e3eee70eca95ecf03d70ea94d97e2bf0163c4bf07f5bc0dc70ad2c362dcc) is the frozen, authoritative text; in case of any difference the original governs. Frozen commit F: `92bf82eca0dae731f7396ed5b4e887e4f3b200e4`.

# Architecture × n-step: complete preregistration protocol v0.3.2 (Revision 1 + Rehearsal Addendum A + DSH Literal Corrections)

Date: 2026-10-10. The protocol version and repository filenames remain v0.3.2; “Revision 1 + Rehearsal Addendum A + DSH Literal Corrections” identifies this integration. **Awaiting freeze, not freeze approval; GPT has not run repository training, tests, or analysis, or published an external record. Historical rehearsal starts and early validation are disclosed in §7.4.**

## Changes relative to the original v0.3.2

The “design” column distinguishes the core confirmatory design from additional secondary recording; the code column identifies work still needed relative to 6023b1a. Already implemented content need not be rewritten.

| Change | Does it change the design? | Further code/test changes required? | Location |
|---|---|---|---|
| Use code commit C+freeze commit F; configuration still records C; restrict C→F file differences | No core change; clarification of freeze procedure | Runner implemented; analysis must additionally verify F and Git relationships | §7.1; specification §1.2 |
| Allow project_root="."; analysis explicitly passes --project-root; public materials omit absolute local paths | No | No; accepted by the current implementation | §7.1; specification §1.1 |
| Use exact fractions for variance, then convert to float64 for the square root; withdraw the math.fsum path | No; implementation convention for the same statistic | No; retain implementation and supplement documentation | §5; specification §3 |
| Specify global checks 1–4 and per-run/file checks 5–7; finite noninteger score is E_SCORE_RANGE | No | No change to order or error codes; a priority regression test may be added | specification §2.3/8.6 |
| Action ties follow the frozen argmax; validation deduplication applies to all train paths | No | No; verification on the final machine is acceptance testing | §4/6 |
| Integrate B1/B2, adopted by the owner, with recording enabled for 30 formal runs | No core change; additional secondary descriptive metrics | Recorder implemented; add independent seal identity/code-hash verification and death-component contract tests | §11; specification §9 |
| B1/B2 use meta.git_sha=F and U=A≠g; no diagnostics for resumed training; switch recorded in freeze record, without new configuration fields | No core change; auxiliary interface specified | No training-algorithm/configuration changes; recording and auxiliary verification as above | §11.5; specification §9.1 |
| Executor has reported A1000 on/off overhead; formal resource estimates remain subject to remeasurement on the freeze candidate | No | No new algorithm code; local acceptance remains pending | §2/6/11.6 |
| A1000,2worker this round; smoke-test 5070 Ti next stage; separate historical 39 runs | No | No | §2 |
| Integrate literature by recorded verification level; do not promote abstract/secondary sources to full-text reading | No | No; human checking of originals remains pending | §9 |
| Integrate A1–A7,20-seed starting point and power limitations; none enters this round's matrix | No | Not this round; register/implement separately later | §12 |
| Sealing is a protocol guardrail; distinguish code evidence, executor reports, GPT static review, personal execution, and human sign-off | No | Documentation update | §3/7.3 |
| Add machine_id to independent final-evaluation environment file and bind it through seal hash; evaluation meta unchanged | No | Yes, minimal provenance completion | §7.2; specification §1.2/7 |
| Freeze hard choice with configuration before the first formal training; complete frozen-file hashes and command records | No core change; clarification of freeze timing | Required-hash verification needs supplementation; hard configuration gate exists | §7.1/7.4; specification §1.2 |
| Update obsolete freeze-checklist statuses; add missing and still-open items | No | Documentation update; no sign-off on others' behalf | §7.4; handoff §4 |
| Retain fixed filenames and spec_version=0.3.2; unique outer delivery package avoids duplicate download names | No | No | §10 |

### Rehearsal additions and integration changes relative to the “Revision 1” integrated version

| Change | Does it change the core design? | Further code/test changes required? | Location |
|---|---|---|---|
| R1: complete freeze binding and rejection timing at both entry points | No | Yes, C5 | protocol §7.1.1/7.2; specification §1.2.1/8.6.1 |
| R2: raw working-tree bytes, -text, and fresh-checkout acceptance on the freeze machine | No | Yes, C6 | protocol §7.1.3/7.4; specification §1.1.1–1.1.2/8.6.2 |
| R3: fixed complete runtime dependency snapshot, committed in C, and unique field mapping | No | Yes, C7 | protocol §7.1.4; specification §1.1.3/2.1 |
| External freeze record, third-party receipt, and actual launch sequence | No | C5 recording integration; D2 procedure/checklist | protocol §7.2.1; specification §1.2.2/7 |
| Disclose short seed100/res4/n1 rehearsals and one early prereg_val validation | No | No algorithm changes; D2 documentation/archiving | protocol §7.4; handoff §4/5 |
| matrix blob retains the previously fixed bytes; -text covers it and expected hash is not redefined | No | Covered by C6; no additional item | protocol §7.1.3/10; specification §1.1.1 |
| Fix freeze-day handoffs by role and timing | No | Covered by D2; no additional item | protocol §7.5; handoff §5; operation-order sheet |

This version incorporates rehearsal R1–R3; execution does not require reading an additional patch. These clauses take effect directly in the corresponding sections below.

This document is self-contained; the previous incremental updates need not be assembled again. H1/H2, the 3×2×5 matrix,300000 transition,last@300k, statistical methods, seed partitions, and matrix.csv bytes are unchanged. The accompanying analysis specification is a complete revision under the same filename, and the handoff is replaced by a complete version; this delivery creates files outside the repository and does not modify the public repository.

### Sources and scope of this verification

This final integration only handles previously delivered texts, rehearsal records, and the owner's new disclosures; it has not reread or confirmed current public main, or run repository code. The following main/source check records the previous Revision 1 reading at 6023b1a; it does not confirm C5–C7 are implemented in the current candidate. The latest disclosure in §7.4 governs historical early-validation information.

Public Git objects were read using a fresh clone without a working tree, confirming origin/main at the time of reading as **6023b1a95c339f1b8af3f98cf533af80eeaba9aa**. matrix.csv was independently read and its SHA-256 checked; static inspection confirmed no path differences in matrix, frozen configuration, results/, or results_gpu/ between 09ea358→6023b1a. Repository code, pytest, acceptance, smoke, oracle, and the analyzer were not run, and real experimental scores were not read to revise the design.

The third-batch attachments report 415 passed and 4 skipped on Windows+A1000, acceptance --quick exit 0, and M1–M7 PASS for two historical datasets; these are **records provided by the local executor**, not GPT execution results. The 4 skips are acceptance stub tests for POSIX path layouts; one cannot claim all 415+4 tests actually passed. B1/B2 overhead attachments are local short-smoke records, not formal training results at 30 units of ten thousand steps. The presence and static paths of new interfaces can be checked; actual execution, the 15 formal initialization pairs, human sign-offs, and freeze approval require separate acceptance.

**Layout:** approved protocol, specification, handoff, matrix.csv, frozen configuration, and manifests go in docs/prereg/; runs in results_prereg/runs/<run_name>/; core analysis in results_prereg/analysis/<analysis_id>/; independent B1/B2 summaries in results_prereg/window_diagnostics_summary/. Source references use function names; locations are determined by final C/F.

## 1. Question, scope, and existing evidence

**Research question:** on a fixed map, with the same BFS distance-field input and environment-step budget, how does changing n-step from 3 to 1 affect CNN-2, ResNet-4, and ResNet-8 scores? Does that effect vary with architecture?

In the previous round, ResNet-4 n=1 outperformed n=3 under both budgets. These data have already been seen and serve only as a source of hypotheses. They do not enter this round's means, confidence intervals, or significance calculations. This round uses new training, validation, and test seeds.

This round manipulates only **architecture and n-step**. Raw-grid input, MLP, PPO, learning-rate searches, and multiple maps are not added; they belong to the next round. CNN-2/Res4/Res8 comparisons simultaneously change structure, parameter count, and computation, so this is an “architecture effect,” not an identified causal effect of depth alone. Res8's receptive-field side length 35 does not imply visibility of the entire map from every map location.

### Predefined research objectives

- **Primary objective (effect estimation):** estimate each architecture's n=1−n=3 score difference and the change in that difference for Res8 relative to CNN-2. The latter is a prespecified architecture×n-step interaction contrast.
- **Prespecified directional replication:** does Res4 n=1 consistently outperform n=3 in direction on new training seeds? Existing findings motivate the direction; this is not treated as an entirely new discovery.
- **Secondary objectives:** compare the validation-selected best checkpoint with the fixed-endpoint last checkpoint, assess whether selection changes the results, and record death rate, win rate, steps, and resource costs.
- **Not directly answerable this round:** general superiority/inferiority of deeper networks, mechanisms of n-step effects, generalization across maps, statistical equivalence to strong heuristics, and rankings across all depths after recipe correction.

### Prespecified, falsifiable hypotheses

These predictions are made before this round's results. H1 is inspired by previously seen Res4 data and is a replication on new seeds; H2 is a new prespecified contrast for this round. The primary interaction remains `C=Δres8−Δcnn2`, defined below, and will not be replaced by a different architecture contrast after seeing results.

| Hypothesis | Prespecified quantitative prediction | What supports it? | What refutes it? | What remains uncertain? |
|---|---|---|---|---|
| H1: the Res4 gain replicates under new conditions | At the fixed endpoint and 300 k budget, `Δres4 = mean(score_n1−score_n3) ≥ 10` pellets | Corresponding interval lower bound>10 | Upper bound<10 refutes “at least 10 points”; if upper bound<0, even a positive gain is refuted | Interval covers 10; a point estimate below 10 alone is not strong counterevidence |
| H2: a practically sized n-step effect difference exists between the shallow/deep endpoints | `\|C\| ≥ 10`, with `C=Δres8−Δcnn2`; no prespecified sign | C interval entirely>10 or entirely<−10 | C interval entirely inside(−10,+10), refuting the prespecified magnitude of the endpoint difference | Other positions, including wide intervals spanning 0 |

“Interval” in this hypothesis table means the **97.5% two-sided training-seed t interval** (α=.025 per item; Bonferroni allocation of total α=.05 across the two), with critical value `t(0.9875,4) ≈ 3.4954059325164377`. The 95% intervals and cross-bootstrap sensitivity results specified below are also reported. Small-sample, t-distribution, and fixed-model-test-set conditional limitations still apply. An uncertain item cannot be called supported/refuted by choosing another interval; disagreement between bootstrap and t decisions must be explicitly marked as method sensitivity.

With only 5 training seeds, H1 support requires `mean(d)>10+[3.4954059325164377/√5]·sd(d)`, approximately `10+1.5631930548·sd(d)`. The required mean effect depends on between-seed standard deviation;10 points alone is not the support threshold. Even with zero standard deviation, the mean must be strictly greater than 10.

H2 concerns only the prespecified CNN-2 versus Res8 contrast. If Res4 differs from other architectures while C is near 0, another architecture interaction may still exist; report auxiliary contrasts, but do not substitute them for H2. Refuting “at least 10 points” does not prove the complete absence of an effect. With only 5 seeds, an inconclusive result is quite possible and is legitimate.

**Prespecified exploratory questions (not presented as directional confirmatory hypotheses):** does n=1 also benefit the other two architectures? Does the absolute Res8 versus CNN-2 score ranking change under n=1? Does best selection change effect direction relative to last? Report all results, without selecting success criteria after seeing data.

**Ideas that can only serve as mechanistic explanations:** exploration actions entering multistep targets, target variance, bootstrapping error, and the relationship between receptive fields and distance-field input might explain the observations. This round does not manipulate exploration strength, off-policy correction, input representation, or environment randomness; even if H1/H2 hold, it cannot confirm any mechanism. New explanations proposed after seeing data must be labeled “post-hoc explanation” and tested in independent next-round experiments.

## 2. Formal matrix and fixed conditions

| Architecture | n-step | Training seeds | Number of runs |
|---|---|---|---:|
| cnn2 | 1, 3 | 100, 101, 102, 103, 104 | 10 |
| res4 | 1, 3 | As above | 10 |
| res8 | 1, 3 | As above | 10 |
| Total | | | 30 |

Res4 replicates an existing finding; CNN-2 and Res8 span the architecture endpoints. Res2 is omitted this time; no complete depth trend is claimed. Matching numbers denote paired training-random-seed blocks; sampled trajectories diverge across architectures/n-step, so they are not identical training trajectories.

| Condition | Fixed value / rule |
|---|---|
| Training budget per run | **300,000 environment transition**;9,000,000 across 30 runs, excluding trials and evaluation |
| Input | 7-channel fields: raw state planes+pellet/ghost BFS distance fields |
| Scenario | standard; fixed existing map and verified ghost rules; maximum 1000 steps |
| Reward | Pellet +1, actual death −10, win +10, each step −0.01 |
| width | 16 |
| Double / Dueling | Both enabled |
| γ / τ | 0.99 / 0.01 |
| Learning rate / optimizer | 0.0005 / Adam; other Adam parameters recorded with frozen code, without architecture-specific adjustment |
| batch / replay capacity | 32 / 100000 |
| Replay format | Uniform uint8 encoding for all convolutional runs; identical restoration rules |
| learn_start | 4000 samples already stored in replay |
| n_envs / steps_per_update | 8 / 4 |
| ε | Linear from 1.0 to 0.05; annealing ends at 120000 environment transition, then remains 0.05 |
| Gradient clipping | Global norm cap 10 |
| Validation frequency | Every 20000 transition,50 episodes;15 validations from 20000 to 300000; deduplicate the end-of-training validation with identical weights;300000 is the fixed endpoint |
| Training device | Same machine, device type, and dependencies for all 30 runs; by default the same GPU |
| Validation device | Use the training device uniformly during training; disclose GPU validation scores when selecting best |
| Final test device | Uniform CPU,1 torch thread for every formal test; no architecture-specific device mixing |
| Parallel training | A1000 fixed at 2 training processes; remeasure the freeze candidate; no third process this round; machine B does not participate |
| checkpoint | Save last and validation-score-selected best; primary uses last |

300k is this round's fixed budget, not a causal comparison with the previous 120k. If the freeze candidate cannot complete the protocol on A1000, pause the freeze. If an overall switch to CPU is necessary, issue an explicit revision before the first formal training and repeat all resource acceptance checks; do not change devices or lower budgets for selected architectures. If 300 k is unaffordable, publish a new version before formal launch, uniformly change the full matrix budget, and retain 30 runs.

Equal budget means equal environment transition counts, not equal FLOPs or training time. n-step changes replay insertion timing and sample structure; identical update counts at every step are not guaranteed. Every run must record final `replay.size` and actual gradient-update count `actual_updates`; do not artificially make up updates and change the algorithm. For n=3, each active environment can end with up to n−1=2 un-emitted tail items, at most 16 across 8 environments; actual termination/truncation flush follows the accepted protocol. Un-emitted tails do not imply fewer executed transitions. At capacity 100000, `replay.size` is occupancy, not cumulative transitions or insertions; cumulative insertions/pending tails, if recorded, require separate fields.

**Frozen parameters outside the CSV must be passed explicitly:** `eps_start=1.0`, `eps_end=0.05`, `eps_frac=0.4`, `tau=0.01`, `grad_clip=10`. These five values are locked in `docs/prereg/frozen_config_v0.3.2.json`; save and check effective configuration per run. Do not add matrix.csv columns or rely on implicit defaults. The 50 validation episodes, seed partitions, machine/worker count, and evaluation device are likewise specified by frozen configuration.

### RTX A1000 (6GB): resources, overhead, and formal machine

Resource sources are updated to the local executor's smoke_results_for_gpt.md record: A1000 6GB, Windows,16GB RAM, smoke code c4bd147; subsequent profile-isolation fix at 22e0048. **GPT has not remeasured these; the third batch adds B1/B2 short-load overhead, but freeze-candidate remeasurement still governs this round.**

| Item | Revised value and evidence limits |
|---|---|
| quick | 6 configurations×900/901=12 short runs of 2000 steps, about 2 minutes; driver explicitly overrides learn_start=500,buffer=4000,eval_every=1000, so gradient updates occur and collection/save/evaluation paths are covered;6 initialization-pair hashes equal (formal runs still do not resume). These smoke parameters differ from formal parameters, but quick cannot be said to perform no updates |
| load | 2 concurrent res8 runs,110000 steps each, replay filled to 100000, about 18.5 minutes; throughput about 101 steps/second/process (including validation) |
| res8 300k | Pure arithmetic at 101 steps/second gives 49.5 minutes;18.5×300/110≈50.5 minutes; plan around 55 minutes/concurrent process, range 50–65: an estimate with margin, not a complete 300 k measurement |
| cnn2 / res4 300k | Not measured by load; provisional estimates 23/39 minutes from historical relative speeds, not measurements this time |
| Formal training | 10×(23+39+55)=1170 process-minutes; ideal two-process parallel time 9.75 hours; plan 11–16 hours for scheduling/load/long-term stability/version changes. Includes 15×50 training validations; do not add 22500 episodes again |
| CPU final evaluation | 60 checkpoints×300 episodes=18000 model episodes;10 episodes about 1.0–4.2 seconds, linear extrapolation about 30–126 minutes. Plan 1–2-hour order of magnitude; loading/episode lengths/CPU concurrency require separate measurement, not an upper bound; optional hard 9000 episodes extra |
| Reruns | Failed attempts and complete reruns extra; never rerun based on scores. Historical 15-hour/86-minute records retained as sources, not new point predictions |

Current res8's 55 minutes differs from historical 86 minutes by about 1.56-fold, with unexplained cause. The same GPU model does not justify attributing this to a fix or claiming 1.56-fold code speedup. Algorithm resource comparisons in formal results must use this round's measured per-run wall time/updates, not mix historical timings.

**load is not a strictly scaled-down formal protocol.** Its source uses val_set=smoke_eval and 10 validation episodes each;110000 steps and eval_every=20000 produce 5 periodic validations plus one final validation at 110000, hence 6×10=60 episodes, versus formal 15×50=750. load also retains eps_frac=.4 but has total budget 110000, giving annealing length 44000 rather than formal 120000; trajectories, episode lengths, and throughput can differ. The 50-minute arithmetic and 55-minute plan are only rough extrapolations;11–16 hours still needs calibration on the final version. “Including validation” does not establish coverage of formal validation workload. smoke_report total wall_seconds also includes report-side CPU evaluation/interruption checks; without original JSON one cannot assert which field the attachment's 18.5 minutes represents exactly.

Memory and concurrency conditions:

- Peak working set per res8 process about 2.5GB, commit about 3.3GB; quick's approximately 1540 MB is a process baseline, with load adding about 1 GB replay. This is not a driver cumulative-peak defect; do not add working set and commit.
- Two processes increase system commit about 7.6GB above baseline, leaving about 2.2GB commit headroom; minimum available physical RAM 0.89GB. Sums of per-process peaks need not equal simultaneous system peak; low VRAM use does not imply ample RAM.
- torch peak allocated/reserved: res8 about 34/46,res4 about 21/46,cnn2 about 10/24. Although fields are named mb, calculation divides by 2^20: interpret as MiB. nvidia-smi about 354 MiB includes contexts and other overhead; these statistics cannot replace or be added to torch allocator figures.
- GPU utilization 96–99%; two concurrent processes nearly saturate it. **This round fixes 2 worker;3worker is inadvisable:** untested, no expected throughput gain, and limited RAM commit headroom. This does not prove 3 worker is slower on every similar machine.
- The 18.5-minute load had no errors, finite weights, and 0 nonfinite-loss updates; it validates that segment, not the full 11–16-hour campaign, concurrent checkpoint writes, or new logging version. Before formal runs, verify quick/load, CPU evaluation, power/no sleep/cooling, and peaks on the freeze candidate.
- Final-version quick checks record actual_updates>0 and effective smoke configuration for each run; learn_start=500 causes updates. Preserve new measurements in separate smoke output directories, without overwriting old reports or tuning parameters using scores. CNN2/Res4 full-replay load throughput remains unmeasured; short quick speed is not a complete 300 k timing.
- Prefer concentrated CPU final testing after training, still 1 torch thread/model. Measure/record evaluation concurrency and worker count before freezing; do not overlap with GPU training and assume no effect with 0.89GB headroom.

**Use A1000, already tested under short load, and 2 worker this round; reserve machine B (Core Ultra 9 275H, RTX 5070 Ti,32GB) for the next stage after full smoke.** This is methodologically reasonable provided core comparisons within each round use uniform hardware/dependencies and identified code, without changing machines selectively by architecture/n. Choose A by executability/throughput/memory, not smoke score; the owner finally fills machine_id and freezes it.

Distinguish three data groups:

| Data group | Permitted comparisons | Must avoid |
|---|---|---|
| Historical 39 machine-A runs | Descriptions/hypothesis sources from already-seen data; recalculation at the same snapshot | Pooling with this round's new seeds/validation/test/implementation as a confirmatory sample; historical runs lack per-run code-version records, so shared machine A does not establish complete comparability |
| This round's 30 machine-A runs | Estimate n-step effects and primary interaction within one frozen protocol, compare training by transition budget, and evaluate finally on the same CPU/1 thread | Pooling with historical 39 for CI/power or choosing current parameters from old tests |
| Next-stage machine-B runs | New controlled comparisons uniformly within B; replication across hardware conditions after confirmation with new independent seeds/holdout | Attributing mean A/B differences directly to budget/capacity/architecture, or using different A/B configurations and completely confounding factors with machines |

The same hardware is not sufficient for identical conditions, and different hardware does not automatically invalidate research. Training randomness, CUDA operators/TF32/precision/determinism switches, and torch/CUDA/driver/OS versions affect training/evaluation; record before freezing and keep uniform within each round. Reevaluating old models on a new CPU checks evaluation-device differences, not the absence of training-device effects.

For next-stage comparability, include the current 300 k recipe as a reference arm on B and compare new budget/capacity arms within B; this is clearer than using current A results as controls for new factors. To study the machine itself, separately register a small A/B bridging training set with identical algorithms/hyperparameters, paired seeds, and uniform evaluation; disclose its limited sample. Do not call bridging bitwise equivalence or pool it into the current 30 runs.

Future cross-stage comparisons should use uniform final CPU evaluation or specify how reference checkpoints are reevaluated. Once used,30000–30299 can only serve as a disclosed comparison set later; next-round confirmatory conclusions need new holdout. B speed/concurrency remain unknown;32GB does not justify promising 3worker. Test GPU/CPU full load first.

The third-batch B1/B2 load attachment adds two off/on pairs of res8 110k batches in off/on/on/off order. Median process-training-time overhead about −0.6%; independent arithmetic on batch wall times gives off median 1104.25 seconds, on median 1098.30 seconds, (1098.30/1104.25−1)×100≈−0.54%. This is within noise, not a speedup finding. Median aggregate per-process peak working set about 2367.1→2368.6 MB, an increase of 1.5 MB; reported 4 groups of last/best weight hashes, best steps, and actual_updates agree. This record meets engineering thresholds≤5% wall time and≤16MiB/process, and the owner has decided to adopt B1/B2. GPT has not run verification.

machine_id uses an alias without hostname/username; A1000 is already selected rather than still choosing between A/B. **Before formal runs, remeasure full-replay throughput and formal 300000-step,15×50 validation workload for cnn2/res4/res8 on the final code candidate**, preserving effective configuration and original reports; existing 110 k/10-episode-validation load is no substitute. The full 30-run 11–16 hours remains a planning range, not a completion record. Remeasurement, CPU final evaluation, and failure reruns are extra. B speed/concurrency remain unknown; do the same smoke next stage.


## 3. New data partitions and sealed tests

- Network initialization/exploration seeds: 100–104.
- Training-environment episode seeds: `1_000_000 × (run_seed + 1) + episode_index`. Each formal run starts at episode index 0 and records the episode counter and seed range; this round starts at 101000000, completely separate from the validation/test ranges.
- Validation: **21000–21049**, a total of 50 environment seeds. The 20000–20049 range in v0.2 conflicts with the repository's EQUIV_SEEDS and is discontinued for validation in this round.
- Final test: **30000–30299**, a total of 300 environment seeds.
- The existing 5000–5049 and 10000–10299 ranges are not used for checkpoint selection or primary results in this round.
- The same test seed provides the same initial state to all configurations; subsequent ghost behavior depends on the agent's actions, so these are not described as “completely identical full-episode trajectories.”
- Exclusively for legacy fidelity: **EQUIV_SEEDS=20000–20299**; used only for fidelity checks of non-learning agents, not model selection or final scores in this round.
- Smoke validation: **40000–40009**; smoke-training run_seed values are **900/901**, separate from the formal 100–104.

**Automatic seed-isolation acceptance:** assert pairwise disjointness between new val, new test, smoke evaluation, EQUIV, old val (5000–5049), old test (10000–10299), and the training-episode streams of different run_seed values. Training streams include old run_seed 0–4, new 100–104, and smoke 900/901, generated using the repository's `train_seed(run_seed,k)`. Prespecify **0≤k≤300008 (inclusive)** as a conservative bound: a fresh run has at most 300000 transitions, each reset requires an initial environment or a preceding transition, and the initial resets of 8 environments are included in the allowance; also assert at runtime that actual episode indices stay within this bound, and check it first if the smoke budget differs. Isolation can be checked using intersections of closed intervals, avoiding sets with millions of entries.

Different architectures/n values with the same run_seed **intentionally share** initialization seeds and training-episode seed streams. Thus “pairwise disjoint” applies to different data partitions and different run_seed values, not this paired reuse; same-seed reruns after objective failures also intentionally reuse seeds. Do not change the paired design merely to pass a test. The existing auxiliary file `seed_partition_check_v0.3.py` (delivered in v0.3, not reissued here) demonstrates isolation assertions and detects the old 20000–20049 conflict; automated tests in the frozen code must read the actual injected ranges, EQUIV/old constants, and actual `train_seed`. Passing this standalone example alone cannot establish acceptance of the code.


**Sealing rule:** conduct one centralized formal test only after all 30 training runs are complete, configuration and checkpoint integrity checks have passed, and the analysis script is frozen. Do not run these 300 test seeds during training or use test scores to decide on reruns, additional seeds, increased budgets, or parameter changes. Seal the complete matrix of test outputs before summarizing and interpreting it; do not inspect individual test results and then adjust subsequent configurations.

Existing unit tests in the formal code may include other test seeds; this is code verification and does not automatically constitute training leakage. However, any code check that feeds this round's sealed seeds back into the training design must instead use independent smoke seeds.

## 4. Endpoints, model selection, and metrics

### Primary endpoint

**Mean standard-test pellet score of the last checkpoint at 300000 transitions**. Rationale: a fixed endpoint avoids incorporating “which architecture is more likely to be selected by validation” into the primary conclusion. Do not select the highest test score over training or change the endpoint based on the final validation results.

### Secondary endpoints

Best checkpoint: evaluate on the fixed validation set every 20000 steps and select the strictly highest mean validation pellet score; retain the earlier checkpoint in a tie. The current implementation may perform another final validation at training end; all train paths deduplicate final validations at 300000 with identical weights, seeds, and evaluation settings, yielding 15 validations and 15×50=750 episodes. **Identical weights, identical scores, and updating only on strict improvement mean deduplication does not change model selection**; freeze acceptance checks identical duplicate scores, candidate steps, and best-weight hashes, and must not skip a candidate with different weights or evaluation settings. Report the best test score and selected training step, retaining last as well; do not change the primary endpoint after seeing results.

**Device dependence:** the attachment reports 142.8 for CUDA evaluation and 144.6 for CPU evaluation of the same checkpoint; this is an example independently reproduced by the user, not rerun here, and cannot estimate a general device bias. Per-episode outcomes may diverge because of numerical device differences. Use GPU validation consistently during training to select best, and CPU,1-thread testing consistently at the end. Best is only a secondary endpoint; reports must disclose the different selection/test devices and this dependence, and must not reselect best using CPU tests.


The new prereg evaluation path retains these fields for each model's episodes: `seed, score, steps, died, won, truncated`; explicitly record the reason for termination/time truncation. The old evaluation path, old format, and old data remain unchanged; see §2 of ANALYSIS_SPEC_v0.3.2.md for the new wrapper/metadata and integrity checks. Statistical score is the pellet count 0–377, separate from training reward. Death rate, win rate, survival steps, and best/last differences are secondary results and cannot replace the primary score endpoint in publicity.

Required standard-test volume:30 models × 2 checkpoints × 300 episodes=**18000 model-test episodes**. If best and last have identical weights, evaluation may be performed once and the identical results reused, with evidence of identical weight hashes recorded.

The hard scenario (chase probability 0.7) is a **predeclared optional secondary evaluation**, evaluating only last with the same 300 initial-state seeds. Whether to run it must be frozen and recorded with hard_enabled before the first formal training run; if omitted, mark it “not run,” without changing the primary endpoint. It tests only changed chase intensity on the same map, not multi-map generalization.

Store each model evaluation and checkpoint separately; best/last JSON files must not overwrite one another. If testing fails, retain generated outputs; after repairing evaluation infrastructure, retrying with the same weights/protocol is allowed, but the reason and hashes must be recorded. Retraining to select a better model is prohibited.

## 5. Analysis: training seeds are the statistical units

Let `Y[a,n,s,e]` denote the score for architecture a, n-step n, training seed s, and test initial state e.

1. Primary result for each trained model: `m[a,n,s] = mean_e Y[a,n,s,e]`.
2. The n-step effect for each architecture: `d[a,s] = m[a,1,s] − m[a,3,s]`; report the 5 raw differences, mean, sample standard deviation, and number of positive seeds.
3. **Primary interaction contrast:** `c[s] = d[res8,s] − d[cnn2,s]`; report its mean and 5 raw values. A positive value means the gain from n=1 is larger in Res8, and a negative value means it is larger in CNN-2. This does not imply that Res8 necessarily scores higher than CNN-2 under n=1, nor does it represent all depth levels.
4. Predeclared auxiliary interactions: `d[res4]−d[cnn2]` and `d[res8]−d[res4]`, descriptive only; do not select whichever is significant as the primary finding.

### Reporting uncertainty

- **Primary intervals:** provide 95% paired t intervals for the 5 training-seed differences in `d[a,s]` and `c[s]`, `mean ± t(0.975,4) × sample_std/sqrt(5)`, with critical value `2.7764451051977944`. These reflect training randomness conditional on the fixed test set and assume independent seed blocks and approximately normally distributed differences;5 observations cannot reliably check the latter assumption, which must be explicitly disclosed.
- **Sensitivity intervals:** apply a crossed bootstrap to the entire paired score tensor,10000 replicates, bootstrap RNG seed=271828: explicitly use `numpy.random.Generator(numpy.random.PCG64(271828))`; in each replicate first call `integers(0,5,size=5,dtype=np.int64,endpoint=False)`, then `integers(0,300,size=300,dtype=np.int64,endpoint=False)`, independently resampling training-seed blocks and test seeds with replacement. All configurations and endpoints share that replicate's indices, then the same effects are calculated. Percentiles use `np.quantile(...,method="linear")`; see §4 of the analysis specification for random-stream check values and hashes. Provide percentile 95% CIs, interpreted as finite-sample estimates of sampling variation in training seeds and test initial states; these may also be unstable with 5 training seeds.
- Do not treat 1500 model×episode records as 1500 independent training runs. The previous CI approach of “average over models first, then bootstrap only test episodes” may be shown additionally, but must be explicitly labeled a conditional CI and not used for algorithm-level conclusions.
- If the interval methods imply different conclusions, report both and label the finding “sensitive to interval method”; do not choose the narrower or more favorable interval.

### Significance and boundaries of conclusions

This round primarily concerns **preplanned effect estimation**; p<0.05 is not the primary interaction's acceptance criterion. With 5 paired seeds, a complete two-sided sign-flip test has only 32 patterns and a minimum conventional two-sided p value of approximately 0.0625; do not circumvent this limitation by selecting a one-sided direction or resampling only test episodes. A sign-flip test of the mean also requires the corresponding symmetry assumption and must not be called unconditionally exact.

The Res4 direction check may additionally report the prespecified **one-sided exact sign test**: under the null, the probability that n=1 beats n=3 on a new training seed, conditional on a nonzero difference, is≤0.5; under the alternative it is>0.5. For 5/5 positive differences, p=1/32=0.03125; for 4/5, p=6/32=0.1875. Exclude zero differences from the sign test's effective sample and report them; calculate p using the actual effective count. This tests directional probability, **not a zero mean difference**, and does not establish effect magnitude, mechanism, or significance across all architectures. Test only this prespecified direction; do not introduce significance thresholds for other contrasts.

The signal interpretations below do not replace the strict magnitude predictions in H1/H2 above. Prespecify a **mean difference of 10 pellets** as a practical magnitude warranting further study in this round (approximately 2.65% of the maximum score, a researcher-defined value rather than an established field standard):

- Mean gain≥10, primary-interval lower bound>0, and at least 4/5 positive seeds: describe as “a gain signal worth further validation under this budget,” report the actual sign-test result, and do not automatically call it generally significant.
- Absolute primary-interaction mean≥10 and primary interval excluding 0: describe as “an estimated architecture-dependent signal,” retaining the t assumptions and small-sample limitations; if bootstrap spans 0, mark sensitivity.
- Wide interval or interval spanning 0: describe as “insufficient evidence”; not “no effect,” “equivalent architectures,” or “no benefit from depth.”
- Also provide raw numbers. The 10-point threshold does not replace a CI and is not used to discard results post hoc.

These signals use 95% t intervals, whereas formal H1/H2 decisions use 97.5% t intervals; do not confuse them. Strict boundaries, exact zero differences, bootstrap-sensitivity flags, machine rules for all exploratory questions, and source tracing are specified in §§3–7 of ANALYSIS_SPEC_v0.3.2.md. Direction/interaction signals have only “supported signal/insufficient evidence,” without additional refutation criteria; H1/H2 use “supported/refuted/uncertain.” Output the 5 raw differences, ddof=1 standard deviation, positive count, and effective sign-test sample size.

Do not tune the next round on this round's public test set and continue treating it as an independent holdout. Next-stage confirmatory research requires new test data and more training seeds, rather than merely additional test episodes for the current models.

The unique numerical path for §5: retain integer pellet numerators through paired/interaction construction; use exact rational fractions for means and sample variances, convert variance to float64, then apply math.sqrt, and calculate se and t intervals under specification §§3/4. The float64+math.fsum path is no longer an available branch. All F1–F8 literal expectations, labels, and test tolerances remain unchanged; implementation paths cannot be switched after scores appear.

Sealing is **protocol-based**: the default formal CLI and covered training/selection call paths have safeguards against misuse; lower-level Python APIs, public seed constants, and source edits can bypass them, so do not claim “only final-eval can read them.” Any training/selection access to sealed partitions is prohibited; recheck all current materials before unsealing, rather than trusting cached completion flags. The count of formal analysis runs also requires execution records; refusing directory overwrites does not prevent rerunning in another directory. See §7 and specification §1.2 for the sequence.

## 6. Trial runs, failures, and resumption

Resource trials before formal launch use independent seeds **900, 901** and independent smoke-validation seeds **40000–40009**, do not access this round's val/test, and do not produce formal comparison tables. At minimum cover n=1/3 for every architecture, forward/update operations, saving/loading last/best, separate evaluation outputs, and interruption/resumption paths. Smoke scores are not used to select algorithms, hypotheses, or hyperparameters; pipeline/throughput/memory measurements may support engineering acceptance of hardware and scheduling.

Dispatch formal training to at most 2 workers in the fixed row order of `matrix.csv`; each training-seed block contains 6 distinct configurations, with order fixed by the CSV itself and its SHA-256. **Remove the claim of dependence on a scheduling RNG and scheduling seed=271828; no reconstruction of the CSV from a shuffle algorithm is required.** Scheduling acceptance checks only the file hash and 6 distinct configurations per training-seed block; do not change order based on scores. Parallel tasks may finish in a different order; record dispatch and start/end times. Bootstrap's 271828 is an independent analysis convention, not the scheduling source. This round has selected 2 workers; if repeat testing of the freeze candidate finds insufficient resources, pause freezing and explicitly revise engineering arrangements, rather than silently changing the worker count during formal execution. Do not change scheduling based on scores during formal execution. Record each run's wall time, final replay.size, actual updates, peak CPU/GPU memory, full parameters, and logs. Resource checks must consider memory after replay is filled, not estimate peaks solely from initially unused buffers. Record GPU nondeterminism if it cannot be eliminated; do not bypass checks or disable tests.

**Stopping rule:** stop only at 300000 transitions, without early stopping based on training/validation/test scores; retain runs even when scores are near random. If the implementation advances only at n_envs batch boundaries,300000 is divisible by 8 and the exact budget should be reached.

**Recovery rule (default):** formal analysis includes only the 30 prespecified runs executed completely from scratch. After infrastructure interruption/OOM/disk corruption, retain the failed attempt and rerun that run from scratch with the same frozen code, configuration, and seed. Low scores do not justify reruns. If the existing implementation supports only resumption that discards environment state/n-step queues, it may be used for resource exploration, but not mixed unmarked into formal runs.

Even same-seed reruns may differ because of GPU nondeterminism; decisions to rerun must therefore rely on objective failure records, occur before formal test scores are inspected, and report attempt counts. Do not select the highest-scoring successful attempt. NaN/nonconvergence may be algorithmic failures: retain and diagnose them first rather than automatically classifying them as infrastructure incidents.

If a code bug requires changing the algorithm/environment, pause the matrix, record the affected scope, and upgrade the code and preregistration version. If the core comparison is affected, rerun the entire formal matrix under one new version; do not concatenate favorable old runs. If the budget is insufficient, mark the study incomplete rather than shrinking the matrix and claiming complete passage.

**Rerun cost and power supply:** current short load measurements roughly estimate 50–65 minutes per full res8 run; the older 86-minute record remains only a historical reference. Neither is a hard future upper bound. Failed attempts and full reruns are additional. Before launch the executor must confirm power, cooling, and disabled sleep; this document does not replace evidence of local settings.

### Requirements and acceptance evidence for the frozen implementation

References below retain filenames and function/configuration names rather than easily outdated line numbers; locations, call paths, and behavior are determined by the frozen commit and must be rechecked at freeze. These are normative requirements;6023b1a contains the main implementation, but code existence does not mean GPT ran acceptance checks in this round. Remaining code work is listed only in the accompanying code-impact checklist.

1. **Seed injection.** Check `VAL_SEEDS`, `TEST_SEEDS`, `EQUIV_SEEDS`, and `train_seed` in `python/pacman_rl/evaluate.py`, and training-validation call paths in `dqn.py`, against the frozen commit. Add recordable, reproducible configuration/CLI injection; training in this round reads only 21000–21049, formal evaluation only 30000–30299, and smoke only 40000–40009. Retain legacy defaults and the EQUIV purpose; do not globally replace EQUIV. Automated tests cover the actual listed call paths and §3 isolation assertions; enumerate coverage rather than claiming every repository path is impossible to bypass, and verify training/selection does not call sealed test.
2. **Independent evaluation output directories.** `eval-model` in `python/pacman_rl/cli.py` uses an independent output-directory interface and explicit checkpoint-identity/weight-hash metadata; save last and best separately as `last/standard.json` and `best/standard.json`. The new path includes `truncated`; test that two calls do not overwrite outputs and that 300 test seeds/fields are complete. Old paths/data remain unchanged; follow analysis specification §2 for format.
3. **Matrix task set.** `python/scripts/prereg.py` implements `prereg_<arch>_n<N>_s<seed>` tasks; check all 30 row names, parameters, and scheduling order against `matrix.csv`. Include training/evaluation seed injection, output paths, frozen machine settings, and the five parameters outside the CSV in actual configuration; prohibit implicit default overrides. Store preregistration files in docs/prereg/ and results in results_prereg/.
4. **Devices and selection.** Enforce CPU and 1 torch thread for final evaluation, logging actual device/thread count; use GPU consistently for training validation. Acceptance reports confirm that best is secondary, disclose device dependence, and do not reselect using CPU tests.
5. **Initial-weight hashes.** Check the order of `torch.manual_seed(cfg.seed)` and online-model construction in the initialization path of `python/pacman_rl/dqn.py`, at locations determined by the frozen commit; call order alone does not prove identical initialization. Inspect intermediate paths and all preconstruction RNG consumption. For n=1/3 with the same architecture and run_seed, hash the initial `state_dict` before the first update using fixed key order, dtype, shape, and raw tensor bytes (do not directly compare checkpoint-file hashes containing serialization metadata). The 30 runs contain **15 initial-weight comparisons between n=1 and n=3 for (architecture, training seed) pairs**. Each pair's canonical hashes must match and be recorded; diagnose and uniformly correct mismatches, rather than accept assumptions. Also check target-initialization relationships.

6. **Independent hand-calculated small-MDP oracle (new; must pass before the first formal training run).** Construct a deterministic chain unrelated to Pacman scores, manually defining transitions, rewards, and known online/target Q tables; independently write expected targets without calling tested replay/trainer helpers to generate “correct answers.” The following γ=1/2 is only for analytically tractable diagnostic fixtures; **formal training γ remains 0.99**.

   | Diagnostic case | Hand-calculated expectation | Error to detect |
   |---|---|---|
   | Nonterminal chain S0→S1→S2→S3, rewards 1, 2, 4; online chooses a0 at the endpoint; target a0=6 at S1 and a0=10 at S3 | From S0: n=1 target `1+0.5×6=4`; n=3 target `1+0.5×2+0.25×4+0.125×10=4.25` | Actual bootstrap state, reward alignment, discount γ^h, and replay horizon; do not treat the n=1 target as n=3 |
   | Online's terminal greedy action is a0, but target is higher for another action a1 (20 at S1,30 at S3) | Still 4 and 4.25; incorrectly taking max target directly yields 11 and 6.75 | Double's “online selection, target evaluation,” and network/state locations |
   | Two-step short chain with rewards 1, 2, truly terminating at the second step | Flush even though n=3 is incomplete: S0 target 2, final-step S1 n=1 target 2, both bootstrap discounts 0 | Do not bootstrap terminal states; insert all short-horizon tail samples |
   | Same two-step chain, but the second step is only time-truncated; actual S2 target-action value 8, reset-state value separately set to 100 | S0 n=3 short-horizon target `1+0.5×2+0.25×8=4`; final-step n=1 target `2+0.5×8=6` | Truncation still bootstraps the actual final observation; use actual h=2/1 discounts, not reset observations or fixed γ^3 |

Fixed Q tables must specify unambiguous online rankings selecting a0; numbers only check definitions and do not evaluate architecture quality. Use the independent oracle to check **actual replay production→ret/disc/next_obs→actual TD-target construction**, rather than just a separately written formula. Also test n=1/3 insertion counts/timing, tail flush at termination/truncation, interleaved inputs from at least two environments without queue mixing, and no cross-episode return concatenation after reset; record expected timing/update-count differences without requiring inherently different algorithms to match stepwise.

Retain the independent expectation table, actual reward sequence, h, ret, disc, terminal state and actual target for each sample, and test code/version/results. Oracle expectations must be derived independently of the tested code; **the cloud agent is both implementer and test author, so this cannot be described as a completed audit by an independent person**. Acceptance records retain “implementer, test author, human reviewer, human review date, checked content/frozen commit/result”; the researcher or another human reviewer fills the reviewer/date fields, and AI must not sign for them. Human review remains open; actual tests distinguish executor reports from raw outputs, and GPT's static reading does not automatically become an executed check; **do not read this round's real training, val, or sealed test results**. Diagnose, uniformly repair, and document failures; do not start the formal matrix. Source provides the oracle/harness and tests; reported executor passes and local 4-source-path mutation records are stored separately, while human hand-calculation review remains pending. Valid hand calculations do not imply GPT ran the repository. Passing excludes only covered implementation errors, not the category A mechanisms in §9.

7. **Final-validation deduplication.** Cover the duplicate same-weight path between 300000 periodic validation and training-end validation; exactly 15 on the formal path. Deduplication applies to all train paths; non-validation-boundary budgets still get final validation,750 episodes, while strict `>` and earlier-checkpoint tie handling remain unchanged. Retain evidence of candidate steps, weights, and identical duplicate scores.
8. **Action ties.** Tie handling follows `torch.argmax` in the frozen implementation; add CPU cases through the actual action-selection path (e.g., Q=[0,2,2,1,0] returns index 1; all-equal Q returns index 0; check the frozen PyTorch interface), without changing the behavior policy. **We disagree with directly assuming an actual zero tie probability**: finite-precision Q values can tie. “Unique greedy action/ignoring ties” is only a conditional assumption for the rough window-probability illustration in §9, not an observed fact. Distinguish whether all tied optimal actions belong to target support from the actual argmax rule.
9. **Analysis interface and synthetic acceptance.** Implement complete input verification, paired differences/interactions, df=4 intervals, fixed-PCG64 crossed bootstrap, exact sign test, fixed labels, and Markdown/JSON source tracing according to ANALYSIS_SPEC_v0.3.2.md. Before freeze, pass all acceptance cases using only simulated data and no real results; after freeze, perform one centralized formal analysis.

CSV has no val/test ranges or machine-name fields, nor eps_start, eps_end, eps_frac, tau, or grad_clip. The existing 30 rows' parameters/names satisfy this round's requirements; retain the filename `matrix.csv`, with content **byte-for-byte identical** to v0.3 and SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`. Frozen configuration expresses seed injection and machine locking. Any necessary CSV-structure change must be separately recorded before formal training; do not silently modify the matrix.

Separate mutation evidence: code includes 6 small-MDP variant types; the attachment reports 4 source-path mutations independently performed by the local executor; the third batch separately reports 2 freeze/unseal safeguard mutations. Do not add these counts and call them one independently validated group, or infer that every source-reversion experiment was reproduced locally merely because tests exist. Precheck all 15 formal initialization pairs by construction only on the frozen machine/dependencies;6 smoke pairs are not substitutes, and formal training must record them again.

Validation deduplication covers all train paths: skip same-weight duplicate final validation when the budget falls on a validation boundary; otherwise still validate at the end. Under strict “>” and earlier-first handling, selection is unchanged conditional on identical weights/settings and actual identical duplicate scores. Finite CPU fixtures do not prove CUDA duplicate validation is always identical; retain actual evidence from the frozen machine. Do not rewrite existing experiment files; rerunning old recipes may change log counts/timing, so enumerate environment/recipe differences.

## 7. Freeze identity, final evaluation, and launch checklist

### 7.1 Code commit C and freeze commit F: a non-self-referential process

C is the full 40-character commit after code acceptance. Set configuration code_commit to C, generate actual file hashes and freeze_manifest, then commit only permitted freeze materials to obtain F. The full SHA of F and SHA-256 of freeze_manifest itself are retained in an **external, timestamped freeze record predating the first formal training run**; F is not written into configuration/manifest contained in F, so no freeze_commit configuration field is added. run_complete.json can already record code_commit=C and freeze_commit=F; code_version.git_sha and diagnostic meta.git_sha record actual HEAD=F. Evaluation meta.code_commit remains C.

Check C→F using final-tree differences between the two endpoints; intermediate commits need not be free of temporary changes later reverted. Frozen execution identity is the unique F; do not automatically treat later descendants “changing only documentation” as the original frozen identity. C=F can formally pass, although preparation usually creates distinct commits.

The permitted set is exactly these 6 files (all prefixed docs/prereg/): frozen_config_v0.3.2.json, freeze_manifest.json, PREREG_ARCH_NSTEP_v0.3.2.md, ANALYSIS_SPEC_v0.3.2.md, CLAUDE_HANDOFF_v0.3.2.md, FREEZE_CHECKLIST.md. matrix.csv, Python code, dependency lock, README/RESEARCH_LOG/PLAN, and all other files are outside the set. Diagnostic-code hashes go directly into manifest.frozen_files, without a separate new freeze document. This set satisfies the freeze intent: F binds the predetermined design and acceptance records to C, without permitting hypotheses/statistics to change through permitted documents after scores appear. Protocol/specification/handoff/checklist each receive actual hashes; final materials are determined by the F object and external record.

Training prechecks verify: C is a repository commit, C is an ancestor of HEAD=F, C/F have identical python tree objects, endpoint differences contain only the above 6 files, matrix hash is correct, tracked working tree is clean, frozen configuration is complete/parameters match, no PACMAN environment overrides exist, and machine/devices/2 workers are uniform. Uncommitted freeze materials are allowed only during manifest preparation; dirty freeze materials are prohibited for formal training/final evaluation/formal analysis. All 30 runs must record the same C, F, and Python-tree identity.

project_root may be “.”; running/analysis explicitly use a project-root argument or a determined root object. Analysis must pass --project-root, not infer from cwd; committed materials must not save absolute local paths. Results/temporary files may be in untracked directories; untracked results do not permit dirty tracked source.

#### 7.1.1 Binding freeze records to files before training and final evaluation (R1)

Retain C/F relationships, the permitted 6 files, clean working tree, fixed parameters/machine/workers, environment-variable checks, and matrix checks; **additionally, both before training and before final evaluation call the same “frozen-file binding check.”** Final evaluation rechecks common F across 30 runs and current training materials; other unsealing gates remain unchanged.

Do not defer binding checks to manifest/analysis after training. Formal run completes them before creating training tasks/models, starting training subprocesses, or collecting environment transitions; final-eval completes them before obtaining permission to use sealed tests or performing any actual evaluation. Any failure exits nonzero through the runner's Refused path, providing relative path, field, expected/actual, or missing-item reason; do not continue training/evaluation or generate success receipts.

The sole data sources are docs/prereg/frozen_config_v0.3.2.json and docs/prereg/freeze_manifest.json under the explicit project root; do not guess other manifests, generate them automatically, or repair them. Check:

1. freeze_manifest.json exists, is valid JSON without duplicate keys; schema/spec_version are correct, synthetic is false, and complete is strictly true. complete means only structural/machine checks are complete, not human sign-off.
2. manifest.code_commit equals current frozen configuration code_commit, i.e., code commit C; manifest.config_path/matrix_path reference this protocol's configuration/matrix. Verify existing formal-mode identity conditions; this paragraph adds no manifest.status or other fields.
3. frozen_files is an object mapping “project-relative path→64-character lowercase SHA-256,” containing every required file in accompanying analysis specification §§1.1/1.2 (including .gitattributes and the complete runtime-dependency snapshot); omitted protocol/specification/configuration/dependencies or other required entries cannot bypass verification.
4. Every frozen_files entry exists and its current **raw working-tree bytes** have the recorded SHA-256. Paths must be relative, not absolute or resolved outside the project root. Check all listed files, including extra-frozen entries, not just three main files.
5. Each of the three configuration fields below equals the corresponding file's hash in the manifest; actual file hashes have already been checked in item 4. Nonempty/64-character format checks alone are insufficient; all-zero values do not constitute valid binding.

| Configuration field (all in to_fill_at_freeze) | Required corresponding manifest.frozen_files entry |
|---|---|
| analysis_script_sha256 | Actual frozen analysis script referenced by manifest.analysis_script_path |
| preregistration_document_sha256 | docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md |
| dependency_lock_sha256 | manifest.dependency_lock_path, fixed as docs/prereg/dependency_lock.txt |

The manifest must bind actual bytes of **the current configuration file itself**; fill the three fields before calculating the configuration hash and generating the manifest. Do not include freeze_manifest itself in its frozen_files, avoiding self-reference; the external freeze record binds its own SHA-256.

Successful checks record checked_utc, actual HEAD/F, C, freeze_manifest_sha256, and binding-check passage for launch logs/final-evaluation evidence. Record identity/integrity only, without reading scores or adding training RNG/forward/per-step operations. Formal analysis still performs file-hash and C/F checks under accompanying specification §1.2, without skipping them because training prechecks passed.

#### 7.1.2 Separate manifest generation from formal execution to avoid self-reference

freeze-manifest is a **materials-preparation generator**, not formal run: it may generate a new manifest while permitted freeze materials remain uncommitted and cannot require an existing valid old manifest to generate itself. The generator checks actual files, required entries, and correspondence of the three fields, then writes the manifest; formal run/final-eval only read the manifest committed in F and never refresh hashes automatically.

After a valid F, document/configuration changes within the C→F permitted set are not thereby authorized changes to the original freeze. Files no longer matching the manifest must be rejected before training begins. Regenerating the manifest as well to obtain F′ constitutes only an explicit, newly approved freeze revision; do not misrepresent F′ as the F in the external record. **Checking external-record F and manifest hash remains a prelaunch protocol gate**; do not claim C→HEAD permitted differences alone identify every post-hoc refreeze.

#### 7.1.3 Unique hash object, -text, and fresh-clone acceptance (R2)

**This round hashes only raw working-tree file bytes, using SHA-256.** Read binary bytes, without normalizing LF, stripping BOM, reserializing JSON, or ignoring trailing newlines/spaces; identical content with different line endings constitutes different files. Apply this to freeze_manifest itself, dependency snapshots, all documents/scripts/matrix. Git object IDs are not the SHA-256 meant here.

Set **-text** in repository .gitattributes for files bound by frozen hashes, preventing Git text-line-ending cleaning/checkout conversion. Commit it with code C, outside the 6 permitted F files; include its actual bytes in manifest.frozen_files. The formal machine need not set personal global core.autocrlf to false to pass.

The following project rules may cover current files; any new extra-frozen path must also have a confirmed -text rule before freeze:

~~~gitattributes
/.gitattributes -text
/docs/prereg/** -text
/python/**/*.py -text
/python/*requirements*.txt -text
/python/scripts/*requirements*.txt -text
~~~

Rules cover the fixed matrix, configuration, manifest, protocol/specification/handoff/checklist, docs/prereg/dependency_lock.txt, actual analysis/diagnostic scripts, and existing requirements files. This does not reprocess all repository experiment data; existing bytes in results/, results_gpu/, and matrix.csv remain unchanged. -text is not the binary alias; ordinary text remains reviewable.

**Rationale:** the protocol already fixes matrix.csv's CRLF bytes/hash; enforcing LF globally or git add --renormalize could change the matrix and violate invariance. -text preserves direct consistency of “actual bytes→hash→checkout identical bytes,” matching the current implementation's working-tree reads. Uniform LF is possible in principle but requires preserving matrix bytes separately and recalculating other materials, adding migration; this round does not offer two schemes for post-hoc selection.

-text controls subsequent Git conversion and **does not automatically restore an old working tree already checked out as CRLF**. Before C, check intended committed bytes against the expected blob; do not globally normalize matrix. In F, each frozen file's raw Git-blob SHA-256 must match its recorded working-tree SHA-256, confirming cross-platform checkout of the same F yields identical bytes. This is byte-consistency acceptance, not a switch to runtime blob hashing.

**Unique byte identity of matrix.csv:** the Git blob of `docs/prereg/matrix.csv` in F must be the agreed original bytes with SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe` (including existing CRLF endings). This is a fixed input, not a matrix regenerated or redefined on freeze day. `/docs/prereg/** -text` covers matrix.csv; accept an effective `unset` result from `git check-attr text -- docs/prereg/matrix.csv`. Git does not convert this file's text line endings; checked-out working-tree bytes must exactly match the blob in the same F. Do not rewrite CSV, change ordering/encoding/line endings, or renormalize it; do not redefine another recalculated value as the “new expected hash.” Freeze/run/analysis may and must recalculate the **actual** SHA-256 to verify equality with the fixed value above; this is integrity verification, not recalculation/revision of the protocol's matrix hash. On mismatch, stop and restore the fixed blob rather than accept a new value.

After F is formed but before external-record approval and the first formal run, **fresh-clone F and check out the exact F** on the formal A1000/Windows machine. Do not manually adjust line endings in an old tree and call that fresh-clone acceptance. Recalculate every frozen_files SHA-256 against the manifest, then recalculate manifest's own SHA-256 against the preparation record. Record F, anonymous machine_id, Git version, core.autocrlf state, effective text attributes of controlled paths, each file's expected/actual, and overall passage; omit absolute clone paths.

Any mismatch halts freeze; do not automatically “update to the current hash” on site. Diagnose byte differences, repair the C candidate, regenerate F/manifest, and repeat fresh-clone acceptance. Do not skip other files just because matrix happens to match.

Additional automated acceptance: put literal LF document/script/dependency fixtures and a CRLF matrix fixture in a temporary Git repository, set -text, and commit. Fresh-checkout with core.autocrlf=true and false respectively; each file must match committed blob/manifest bytes exactly. Matrix expected values use original literal CRLF bytes, not a “normalized” oracle. Linux Git settings can simulate the conversion, but **the local executor must still actually perform fresh-clone acceptance on formal Windows**; GPT has not run it in this round.

#### 7.1.4 Responsibility, commit, and fields for the complete runtime-dependency snapshot (R3)

The exact-version snapshot of the complete Python training/validation/final-evaluation environment is fixed as:

~~~text
docs/prereg/dependency_lock.txt
~~~

Generated by the **local executor** on formal A1000 using the Python training/final-evaluation environment accepted through candidate smoke/resource checks; cloud implementer checks format/field wiring and includes it with code/.gitattributes in **code commit C**. Human researchers check environment provenance/acceptance records; AI does not sign for them. Generate before final C; F neither adds nor updates this file. It is not added to FREEZE_MATERIALS; the permitted set remains 6 files.

Generate it using python -m pip freeze --all in that environment; the chosen interpreter must belong to the accepted environment. Do not generate the A1000 snapshot from another cloud CPU environment. Record the generation command (without absolute local paths), UTC, Python/pip versions, anonymous machine_id, and candidate-code SHA. Do not implicitly upgrade software just to fill the lock file; environment changes require renewed acceptance and a regenerated lock/new C.

Commit a UTF-8, no-BOM, LF snapshot of fixed-order name==exact_version entries, retaining local build suffixes (e.g., +cu…). Final SHA hashes actual committed bytes, not unsorted original stdout. Resolve and record sources for any editable entry, local file URL, private repository/token, or uncertain version before freeze; do not publish them directly or silently delete actual dependencies. **Only the repository project's own editable entry may be excluded**, because C/F already bind its code; record excluded package name/reason in the generation record, without extending exclusion to other local dependencies. The executor may privately retain generation records/raw stdout; committed snapshots and external records omit local paths/credentials.

This snapshot fixes exact versions of installed Python packages, **not a complete cross-platform resolution lock with all wheel hashes/download sources**. Record Python interpreter, CUDA runtime/driver, OS, hardware, and numerical switches separately as environment evidence; pip freeze does not establish cross-machine bitwise reproducibility. Rebuilding/checking a candidate environment against the snapshot still requires acceptance. Retain currently accepted software in this round; do not select “newer” versions because of specification wording.

| Material / field | Bound object |
|---|---|
| manifest.dependency_lock_path | Fixed docs/prereg/dependency_lock.txt |
| manifest.frozen_files[this path] | Actual SHA-256 of complete runtime-dependency snapshot |
| frozen_config.to_fill_at_freeze.dependency_lock_sha256 | Same as preceding entry, not the NumPy-only file |
| manifest.frozen_files[python/scripts/prereg_analysis.requirements.txt] | Separate actual SHA-256 of existing analysis dependency file |

>= in python/requirements.txt specifies installation requirements, not the runtime-dependency snapshot. python/scripts/prereg_analysis.requirements.txt retains its existing pinned NumPy version and analysis purpose, fixed with C and included as an additional required frozen file; **do not use it for the complete runtime-dependency snapshot field**. The two files have distinct purposes, without a second new configuration hash field. If formal analysis uses a separate environment, prepare and verify the specified NumPy version/random stream before C and record Python/pip versions and purpose; do not select the analysis environment after running.

The freeze generator/run/final-evaluation binding checks reject incorrect dependency_lock_path; verify the snapshot already exists in C's Git tree, its blob is unchanged in F, and working-tree hash matches the manifest. Exact entries must at least cover numpy, torch, matplotlib, and pytest in current installation requirements; reject missing top-level dependencies or nonexact entries such as>=. This minimum check does not replace package-by-package completeness checking against the accepted environment. The dependency lock cannot be added only in F, even within docs/prereg/, because it is outside the 6 permitted files. Analysis still reads files through the manifest mapping; statistical methods remain unchanged.

Acceptance: a snapshot committed in C with F changing only permitted files passes; adding/modifying the snapshot only in F is rejected; an >= installation file or NumPy-only file masquerading as the complete snapshot is rejected. Format checks may reject nonexact entries, but filename/few pinned versions alone cannot prove “complete”; package-by-package correspondence with the accepted environment's pip freeze is supported by local generation/check records.

### 7.2 Separate checks for unsealing, final evaluation, and analysis

Final evaluation must repeat the full §7.1.1 binding check before permission issuance/any test access; passing during training does not replace current verification.

Before unsealing: all 30 runs complete; reread current config, summary, train_log, checkpoint, and run_complete, checking exact 300 k,15×50, no formal resume, best step/first strict maximum, resources/update/replay counts,15 initial-hash pairs, and current weight/file hashes against sealed completion materials. Analysis script/dependencies/documents are frozen. Do not trust only cached summaries or two true booleans.

Final-evaluation prechecks additionally verify current HEAD is the F common to all 30 runs and C/F tree relationships/clean state remain valid; use the frozen machine's CPU with 1 torch thread per model. Save actual evidence separately as results_prereg/final_eval_environment.json, without changing the prereg-eval-1 meta-field contract. At minimum record anonymous machine_id, UTC, CPU device, actual threads/software/numerical switches, code_version, and preflight C/F; anonymous machine_id must match frozen configuration. Local executor separately retains frozen environment descriptions such as OS/driver/power/CPU model; identical aliases do not automatically authenticate hardware.

The core files set in final evaluation_seal remains exactly the 30 sets of config/summary/last/standard/best/standard plus declared hard. Add top-level protocol_evidence recording C, F, and relative path/actual SHA-256 of the separate environment file. This is provenance metadata only; B1/B2 are not added to core inputs. The seal producer must recheck consistency of 30-run C/F with current prechecks/environment file. Analysis rechecks seal fields, environment hash, machine_id, CPU/1 thread, F/current HEAD, C ancestry/permitted-tree differences, frozen files/actual script hash. **Analysis should check both C and F**; checking C alone is insufficient. 6023b1a lacks analysis F verification and environment machine_id/hash binding; these are remaining small prefreeze revisions.

Training complete→current-materials pre-unseal checklist→explicit --unseal→centralized full-matrix evaluation→evaluation-file sealing→one core analysis, with separate B1/B2 sealing/descriptive summaries. Do not adjust subsequent tasks after viewing per-run formal test scores. Freeze manifest complete=true records structural/machine checking and **does not automatically mean human gates are signed off**; approval depends on external records/human fields. Program output nonoverwrite controls and operator one-execution records serve separate purposes; lower-level APIs/source are not an unbypassable security boundary.

#### 7.2.1 External freeze record, storage location, and timing evidence

##### 7.2.1.1 Two stages, avoiding self-reference and backfilling

**Prelaunch records** contain C/F, manifest/all frozen-file hashes, machine/software sources, approval, and commands; at that point only candidate/frozen environment evidence and planned final CPU settings can be retained. Actual final_eval_environment.json arises only during final evaluation and cannot be inserted into a record claimed to predate launch.

**Post-final-evaluation receipts** separately retain actual final_eval_environment/evaluation_seal paths/hashes, C/F, and prelaunch-record SHA. Preserve previous record bytes without overwriting/backdating; core evaluation_seal.protocol_evidence still binds the actual environment file under the original integrated version.

##### 7.2.1.2 Minimum prelaunch FREEZE_RECORD.json fields

| Field | Minimum requirement |
|---|---|
| schema_version / spec_version / document_revision | prereg-external-freeze-1 / 0.3.2 / 修订1+彩排追加A+DSH 字面修正 |
| repository | Public repository URL; no local path |
| code_commit / freeze_commit | Full 40-character SHAs of C and F |
| freeze_manifest | {path:"docs/prereg/freeze_manifest.json", sha256: actual 64-character hash} |
| frozen_files | Copy manifest mapping; matrix hash must be the fixed 5cbd4e7b…0dfe |
| checkout_verification | Relative identifier/hash, passage status, and date of fresh-F-clone acceptance on formal machine |
| dependency_snapshot | path/hash of docs/prereg/dependency_lock.txt, anonymous machine, generation/check-record identifier, Python/pip versions; analysis dependency-file identity separately listed |
| environment_evidence | Relative identifier/hash of frozen environment description; OS/driver/software/numerical switches, anonymous machine_id, train/validation_device; no username/hostname/absolute path |
| execution_plan | worker_count=2, actual formal launch command without absolute paths, window_diagnostics enabled 30/30, hard_enabled decided, final CPU/1-thread settings |
| human_approval | Identifier/hash of human approval record, approved_utc, and approved scope; do not fabricate approved if not yet approved |
| prepared_utc | Executor-reported UTC; not independent timing proof |

Use the full matrix value, not the table's abbreviation, in JSON:

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

Do not put the record's own hash inside itself; retain uploaded SHA-256/third-party timestamp in a separate publication/storage receipt. Original human sign-off may be retained separately; public records reference identifier/hash without requiring personal information to be published.

##### 7.2.1.3 Fixed storage location

Default storage in this round is a **GitHub Releases asset** for the repository, with entry/tag prereg-v0.3.2-r1-freeze-<first 12 characters of F>, tag pointing to full F, and asset FREEZE_RECORD.json. Release may initially remain draft; this is third-party timestamped storage evidence, not a requirement for additional public registration. When later publishing, retain original asset ID/bytes; do not delete/reupload and misrepresent the original time. This recommendation is procedural only; **delivery of this file does not create a Release/tag or upload anything; these actions belong to the owner**.

The executor retains relative location freeze_records/<full F SHA>/ in research materials outside the repository working tree, containing FREEZE_RECORD.json, FREEZE_PUBLICATION_RECEIPT.json, launch records, and later FINAL_EVAL_RECEIPT.json. Records use only relative identifiers/public URLs, not this directory's absolute local address; the directory is outside F's permitted set and does not create F self-reference.

FREEZE_PUBLICATION_RECEIPT minimally retains repository/Release/tag URLs or IDs, full F, GitHub asset ID, asset created_at (third-party UTC), actual download URL, downloaded-file SHA-256, and manifest SHA-256. Verify using actual GitHub API/asset downloads, not just a self-declared JSON. If Release.published_at follows training, it indicates only later publication; evidence that “bytes were stored by a third party” uses original asset created_at/download hash, without claiming they were public at that time. Independent review requires the same asset identity and original server metadata.

##### 7.2.1.4 Checking “record first, formally launch afterwards”

1. After F is formed and fresh-clone acceptance on the formal machine passes, obtain human approval, generate/store FREEZE_RECORD and third-party receipt, and check current HEAD=external F and manifest raw-byte hash=external value.
2. **Only afterwards** invoke the first formal run. Prelaunch logs retain actual C/F, manifest SHA, FREEZE_RECORD SHA, third-party asset ID/time, precheck passage time, and first training-task submission time (UTC), plus original CLI output. A local executor's launch recorder may retain this; no training-algorithm network access/new configuration field is required.
3. Later verify downloaded bytes/hash for the same asset ID, C/F/manifest mapping, and third-party created_at before first formal task launch; calibrate local clock and record timezone/offset. Archive receipts/launch records as research evidence without changing the core analysis files set.

**Evidence boundary:** self-entered UTC, file mtime, and Git author dates are mutable and alone do not independently prove ordering. Third-party asset time/download hash show these bytes were stored no later than that time; actual first-training timing still depends on launch/execution records, and public source safeguards cannot prove there were never unrecorded runs. This is a traceable research protocol, not purportedly unforgeable security certification.

### 7.3 Evidence levels

| Level | Permitted claim | What it must not be expanded into |
|---|---|---|
| done(code) | Implementation/tests/fixed expectations exist, with maintainer/scope identified | GPT executed them this round; all parameters/devices accepted |
| Executor report | Actual execution records on specified machine/commit/command in attachments | GPT measured them; unprovided raw-log items independently confirmed |
| GPT static review | Objects/source paths/hashes/text read this round are consistent | A minimal counterexample was executed or pytest passed |
| GPT execution | Only checks actually executed by GPT; none for repository code this round | Arithmetic checking of attachment numbers described as GPU measurements |
| Human sign-off | Review/approval with human name/date/content/commit specified | AI signing for a human; mathematical oracle independence equated to personnel independence |

Tiny-configuration weight equality covers only those fixtures; short-smoke throughput/stability does not establish all-architecture full-replay performance, an entire 11–16-hour round, or cross-machine bitwise equivalence. Core “protocol-based sealing” wording in README/RESEARCH_LOG/PLAN agrees with this section (GPT static reading); remaining old B1/B2-overhead/adoption statuses and Fraction “awaiting specification decision” wording should be updated under this revision.

### 7.4 Complete freeze checklist (sources for each item; human fields left blank)

**Disclosed prefreeze rehearsal facts (provided by the owner; not independently executed/verified by GPT this round):** the local executor actually started formal training-seed block 100's `res4, n=1` several times during procedural rehearsals in disposable clones, each lasting at most approximately 75 seconds; one reached the first validation point and performed one early model validation on `prereg_val`. Outputs were in disposable directories, are not included in this round's 30 formal runs, and their weights/checkpoints/logs are not reused or used to select algorithms, hyperparameters, models, machines, or formal attempts. “Formal runs” here means only runs after this section's freeze gates and owner approval; no claim is made that these seeds had never previously been started. That validation used prereg_val, a partition available for model selection, and does not imply access to the sealed test set; GPT has also not verified the sealed test's complete access history this round. Archive rehearsal counts, commands, start/end times, known steps, and validation details according to available records, marking unknowns unknown; do not fabricate logs or describe deleted disposable outputs as still reviewable. This disclosure must not alter matrix/seeds/H1/H2; future safeguard rehearsals use synthetic materials/call spies, avoiding further actual formal-seed starts as smoke.


- [ ] Complete the final code-impact checklist and accept all code/tests at final C. 6023b1a is this reading baseline, not automatically final C.
- [ ] Complete C/F process, external F/manifest hash/timestamp; F changes only 6 permitted files, with unchanged Python tree/matrix; actual analysis checks C/F too.
- [ ] Fill frozen configuration with A1000, anonymous machine_id, CUDA training/validation,2 workers, and final CPU/1-thread evaluation on the same machine. Lock hard_enabled before first formal training, not at unsealing.
- [ ] Record Python/torch/NumPy/CUDA/driver/OS/dependency lock, precision/TF32/determinism switches, actual commands/full effective configuration; include dependencies/configuration/protocol/specification/handoff/checklist/analysis/both diagnostic-code files in frozen hashes. Local records supply TF32 details not automatically collected; AI must not fill them for humans.
- [ ] Verify new val 21000–21049, test 30000–30299, smoke 40000–40009, formal 100–104, smoke 900/901, legacy partitions/EQUIV purposes/episode guard using actual constants, except intentionally paired shared streams; enumerate covered paths and prohibit training/selection test access.
- [ ] Accept original matrix byte hash,30 rows/6-configuration seed blocks, fixed dispatch order, and explicit CSV-external five values 1/.05/.4/.01/10; do not reconstruct a scheduling RNG.
- [ ] Accept targets/replay/uint8 encoding/budget/checkpoint round trips; actual small-MDP chain covers n1/n3, Double endpoint, termination/time truncation,γ^h, insertion/flush, environment/episode isolation. Separately identify/version/report 6 code variants,4 local mutations, and third-batch 2 safeguard mutations; do not combine counts.
- [ ] Human checks small-MDP expected calculations and actual reward/h/ret/disc/next_obs/target samples, recording human reviewer/date; disclose cloud agent as both implementer/test author.
- [ ] Construct only 30 models on formal machine/frozen dependencies for 15 n1/n3 canonical initial-hash pairs; target exactly copies online; record again during formal runs. 6 smoke pairs are not substitutes.
- [ ] Best uses strict>, earlier tie handling, exactly 15×50 formally; document all-train-path deduplication scope and actual CPU/CUDA argmax-tie cases/specified repeated-validation evidence; do not assume zero ties.
- [ ] eval-model outputs are independent/nonoverwriting and new path includes truncated; old experiment files not rewritten; record deduplication-related changes to future logs/timing for old recipes.
- [ ] Analysis uses synthetic data only; accept F1–F8/E1–E13, nonzero best−last, rate/steps/resource sources, random stream/t/type 7/labels, and new identity/order tests; human mathematical/source reviews signed separately.
- [ ] Final-candidate quick covers all 6 configurations with actual updates>0; accept profile isolation/cache provenance/error exits; load and formal-budget 15×50 burden cover cnn2/res4/res8, measuring 2-worker full replay/simultaneous-disk peak and CPU-evaluation throughput; locally confirm power/cooling/no sleep. Timing is governed by remeasurement on that version.
- [ ] Owner has adopted B1/B2 and --window-diagnostics for all 30; freeze recorder/summary code and pass raw-count/emission/no-side-effect/zero-denominator/death-constant tests; retain third-batch A1000 overhead report link/hash/commit and specify whether final code changes require remeasurement.
- [ ] B1/B2 auxiliary sealing verifies F/frozen diagnostic-code hashes; diagnostics do not determine training/stopping/reruns/selection/core decisions. Report failures separately, without changing core files contract.
- [ ] Owner/advisor personally reads original citations and checks bibliographic details/claims/locations/limits with sign-off; retain abstract/secondary levels without automatically upgrading to full-text.
- [ ] No score-based early stopping/reruns; distinguish objective interruptions from algorithmic NaN/nonconvergence; archive failures and rerun from scratch with same C/F/parameters/seed, without formal resumption or choosing successful attempts; core code defects require uniform revision/reruns.
- [ ] Launch approval precedes first formal training; all 9 empty configuration fields/human gates complete. Before unsealing recheck all 30 current materials,15 pairs, frozen/sealed hashes; retain independent final-evaluation environment evidence/hash binding; retain single formal-analysis execution records/objective-failure recovery rules.

- [ ] formal run and final-eval reuse full freeze-binding checks before training/test-permission issuance; reject missing manifest, document drift, each of three configuration hashes set to all zeros, wrong complete/C, missing required entries, and extra-frozen drift; counterexamples make 0 training/permission/test calls.
- [ ] `.gitattributes` is committed in C/hash-bound; all frozen paths effectively use `-text`; matrix blob/working tree retain fixed bytes, without repository-wide LF normalization.
- [ ] `docs/prereg/dependency_lock.txt` is generated from the accepted formal A1000 environment and committed in C; exact versions/source/Python/pip/package correspondence recorded; three configuration hashes point consistently into the manifest.
- [ ] Fresh-clone F on formal Windows/A1000; all frozen_files working-tree/blob/hash identities match manifest, retain manifest's own hash; do not silently rewrite hashes on failure.
- [ ] Owner retains external FREEZE_RECORD/original asset ID/third-party created_at/download-hash receipt and approves; local executor checks F/manifest hash/launch order; self-entered UTC is not independent timing proof.
- [ ] Disclose/isolate historical formal seed100/res4/n1 short rehearsals and one prereg_val validation; outputs are excluded from formal results/all selection; do not claim nonexistent original evidence was retained.
- [ ] Separately retain actual final-evaluation environment/seal receipt, referencing prelaunch records without backfilling/overwriting them. See protocol §7.5 and handoff §5 for responsibilities.

The 9 empty fields at the 6023b1a baseline are hard_enabled, code_commit, machine_id, worker_count, and to_fill_at_freeze's analysis_script_sha256, preregistration_document_sha256, dependency_lock_sha256, driver_and_os_note, power_and_sleep_settings_confirmed; status remains draft. All appear above; human oracle/analysis/literature sign-off and approval are additional open gates. Old FREEZE_CHECKLIST statuses such as section A's “P1-02 awaiting repair” and insufficient analysis F2–F6 assertions must be updated against latest code/execution evidence; B1/B2 “overhead unmeasured/adoption undecided” becomes “local report passed/owner adopted; final-version remeasurement/freeze pending.” Do not call these updates a completed freeze.

### 7.5 Responsibilities and sequence on freeze day

This is a one-page division of work, **not an executed receipt or launch approval**. Roles: cloud agent=implementer/test author; local executor=A1000 operator; owner=responsible researcher/freeze approver/external-record custodian. Actual people claim roles; do not assume another AI signs for them or any step is already complete. If prior acceptance spans multiple days, follow the sequence rather than skip steps to finish “that day.”

| Order / timing | Responsible role | Action and evidence handed to next role |
|---|---|---|
| 1, before C | Cloud agent | Complete C1–C7/T1–T2/D1–D2 code/tests/ordinary documentation; set/accept -text and preserve original matrix blob; use synthetic data only for analysis/safeguard acceptance. Deliver candidate SHA, test commands/raw outputs, and diff list. |
| 2, after candidate acceptance, before final C | Local executor | Accept candidate resources,15 initialization pairs, saving/loading, and CPU evaluation on A1000/2 workers; record all architectures/formal-budget burden under the protocol, without sealed-test access or score-based recipe selection. Generate exact `docs/prereg/dependency_lock.txt` using accepted interpreter; deliver command, Python/pip, anonymous machine, candidate SHA, package checks/resource records; omit local paths from lock. |
| 3, after dependency-snapshot handoff | Cloud agent | Integrate snapshot/.gitattributes/code/tests/README etc. into final C; check snapshot exists in C and matrix is unchanged; determine whether final changes require repeating step 2. Deliver full C/received evidence to owner/executor; do not generate the GPU environment lock for the local executor. |
| 4, before preparing F | Owner+local executor | Owner checks design, human oracle/mathematical/literature review statuses, and rehearsal disclosure; executor fills actual machine/software/power details. Lock hard,2 workers,30/30 diagnostic commands, CPU/1 thread, and evaluation parallelism. Missing human sign-off remains open, not AI-filled. |
| 5, after C is fixed | Local executor prepares; cloud agent may check | Fill C/three actual hashes; finalize three integrated texts/checklist before hashing configuration/generating complete manifest. Avoid manifest-hash self-reference. Commit only 6 permitted materials to obtain F; do not add/change snapshot/attributes only in F. Deliver full C/F/manifest/file hashes; training is still prohibited. |
| 6, after F | Local executor | **Fresh-clone exact F** on formal Windows/A1000; verify clean/C→F, effective -text, every frozen file's blob/working-tree/hash, manifest's own hash, three configuration hashes, and both entry-point precheck wiring. Prechecks only, no training. Deliver path-free per-file acceptance; failures return to candidate repair, without on-site hash changes to pass. |
| 7, after fresh-clone passage, before launch | Owner | Review/approve C/F; store FREEZE_RECORD as agreed original GitHub Release asset (possibly draft), verify tag→F, obtain server created_at/original asset ID/download-byte-hash receipt, and archive outside repository at `freeze_records/<F>/`. Deliver approval/external F/manifest hash/receipt to executor. Do not assume completion if nobody uploads or no actual receipt exists. |
| 8, after approval/receipt | Local executor | Recheck HEAD=external F, manifest/record hashes, clock, and all prechecks; retain first-task launch UTC, asset ID, original CLI output. Launch 30 fresh runs in fixed matrix order with 2 workers and diagnostics on throughout; do not reuse rehearsal outputs. Store first, launch afterwards; program need not access network. |
| 9, after all 30 runs finish | Local executor | Reread integrity materials/pass unsealing gates; final-eval repeats binding prechecks and performs centralized CPU/1-thread evaluation; save actual environment file, core/auxiliary seals, separate FINAL_EVAL_RECEIPT. Run frozen analysis once centrally, retain failure/recovery records, and do not overwrite prelaunch external records. |

At each handoff the recipient checks commit/file hashes, evidence scope, and incomplete items; unperformed steps cannot be assumed complete. Any missing prerequisite halts launch. Standalone `FREEZE_DAY_ORDER_v0.3.2_r1_REHEARSAL_A_20261010.md` is a portable copy of this section; execution of the specification does not depend on it.

## 8. Output and reporting template

Each run retains at least configuration, initial-weight hash, code version, training-seed range, train/val logs, last/best weights/hashes, selected step, failed-attempt list, and costs (including replay.size/actual_updates); evaluation saves independent `last/standard.json`, `best/standard.json`, and optional `last/hard.json`.

See ANALYSIS_SPEC_v0.3.2.md for input/output/field contracts; each input has exactly 300 episodes and seed set 30000–30299, without duplicates and with complete finite values. Any failure terminates analysis without silent skipping. All data numbers/intervals/labels have file-hash/formula provenance. Generate final report as both Markdown/JSON, retaining 5 raw differences/bootstrap sampling estimates.

Final report order:

1. All planned/completed/failed/rerun/not-run items and preregistration deviations.
2. Per-model episode integrity, seed matching, final-state fields, and summary-number checks.
3. Raw scores for 5 training seeds in 6 configurations, mean±seed std; not only the best seed.
4. Each architecture's n-step effect,5 differences, both CIs, and directional counts.
5. Prespecified primary interaction C; auxiliary interactions labeled separately, without reselecting the primary contrast.
6. Effective seed count, p, and accurate interpretation of Res4's one-sided sign test.
7. Best/last and resource costs; explicitly mark optional hard if not run.
8. Limitations of small sample, one map, privileged input, equal budget/different compute, model selection, and GPU nondeterminism.

**Permitted conclusion example:** “On this fixed map under a 300 k budget, the estimated gain from n=1 for an architecture is X, with Y of five training seeds agreeing in direction; the between-architecture difference in gain is C, with interval…”.

**Prohibited extrapolation examples:** “proves depth is useless,” “proves n=1 is better for all convolutional networks,” “has explained the n-step mechanism,” “MLP/heuristics are equivalent,” “more test episodes solve insufficient training seeds.”

Include separate complete B1/B2 JSON/raw-count provenance/descriptive reports, C/F/final-environment hash, all prespecified exploratory questions, and explicit deviations. Core analysis does not read diagnostic files; diagnostic failure does not change H1/H2 numbers/labels.

## 9. Literature basis for n-step returns and unresolved matters

### Verification status: reading records separate from GPT independent checks

This section integrates previous owner/local-executor joint-reading records and related_work_notes.md, retaining verification levels/calibrations. The second part of the attachment corrects the earlier “textbook not yet checked” status/window-probability statements; final supplements govern. **Providing reading records, GPT verifying public implementations, and human researchers completing prefreeze citation acceptance are three different activities.**

| Source/content | Reading-check records provided by owner/local executor | Content independently verified by GPT | Limitations still requiring explicit disclosure this round |
|---|---|---|---|
| Rainbow, Hessel et al., AAAI 2018, arXiv:1710.02298 | Reported reading full ar5iv web text; records six components, Table 1 n=3, choice of n=1/3/5, multi-step ablation, exploration settings/target form | Prior-round checks of public implementation citations/bibliographic information, Dopamine TF configuration, and DQN Zoo default 3-step setting; original paper not reread this round | **53/57, ablation ranking, formula/Table locations, and Noisy Nets/ε details not independently verified by GPT this round**; web full-text reading is not page-by-page PDF study |
| Retrace, Munos et al., NeurIPS 2016, arXiv:1606.02647 | Reported reading full ar5iv text, checking trace coefficients, Table 1, and policy-mismatch discussion | Prior-round check that TRFL implements `λ min(1,π/μ)` and cites the paper | **Paper tables, theorem conditions, and formula locations not independently verified by GPT this round**; implementation cannot replace checking original conditions |
| Sutton & Barto, 2 nd edition, MIT Press 2018, Chapter 7 | Final supplement reports local executor read PDF-extracted text; locations approximately PDF pages 163–180/book pages 141–158, sections 7.1–7.5/7.7, equations 7.1/7.4/7.9–7.11 | Prior-round checks of companion implementation README bibliographic link/Figure 7.2 entry; no independent full-text reading | **Chapter details/equation numbers/page locations are supplied reading-record locations, not independently verified by GPT this round**; actual edition governs page numbers; textbook no longer described as “nobody checked online” |
| Dopamine, DQN Zoo, TRFL implementations | Reported checks of Dopamine TF/JAX `update_horizon=3`, DQN Zoo `n_steps=3`, and TRFL coefficients | Prior independent checks of corresponding Dopamine **TF**, DQN Zoo, and TRFL content | JAX confirmation comes from supplied records; configurations not downloaded again this round, so not all versions are GPT-verified |

**Access/acceptance limitations:** prior 403 responses from arXiv/textbook sites are historical, not evidence of current environment permissions or owners' inability to read. Original sources were not reread for this integration; do not treat GPT's prior 403 as proof owner/executor could not read or label this round's paraphrases GPT source verification. Owner has provided joint-reading records; researcher/advisor must still fill reviewer/date/actual source locations/accurate wording for each item. This prefreeze task remains; GPT must not automatically mark it complete for humans.

### Target form and differences from textbook algorithms

For nonterminal transitions, constant γ, and this protocol's fixed Double DQN recipe, the target is:

`G_t^(n) = Σ_(i=1..n) γ^(i−1) r_(t+i) + γ^n Q_target(S_(t+n), argmax_a Q_online(S_(t+n),a))`。

If true termination occurs before n steps, accumulate only through termination and **do not bootstrap**; time truncation is not MDP termination. Under this protocol accumulate actual h rewards and bootstrap from actual truncated observation with discount `γ^h`, not the post-reset observation. n=1/3 are only this round's factor levels, not a complete search over n.

According to supplied reading records, Rainbow also uses a truncated reward sum plus terminal Double-style greedy bootstrap, without off-policy correction for intermediate actions; it includes distributional value representations and other components, so it is not the same complete algorithm as this project.

Textbook Chapter 7 connects one-step TD and Monte Carlo; random-walk examples suggest an intermediate degree of bootstrapping can be advantageous. **Optimal n depends on task, returns, and learning conditions; the textbook provides no universal “3 beats 1” conclusion**. Its error-reduction property for expected n-step returns (contraction factor γ^n) assumes a fixed target policy, on-policy prediction, and corresponding estimation conditions; it cannot be applied directly to DQN control with neural networks, replay, nonstationary targets, and distinct behavior/target policies.

The importance-ratio range depends on the algorithm. Counts below concern complete n-step action-value updates without early termination; after true termination count only relevant actions that actually exist:

| Endpoint treatment | Action-ratio range ordinarily considered | Relationship to this project |
|---|---|---|
| n-step Sarsa: sampled terminal action `A_(t+n)` | `A_(t+1)` through `A_(t+n)`, n factors; excludes conditioned-on evaluated action `A_t` | Terminal sampled action also requires correction; textbook n factors cannot be transferred directly to DQN window counts |
| n-step Expected Sarsa: target-policy expectation at endpoint | Intermediate `A_(t+1)` through `A_(t+n−1)`, one fewer terminal sampled factor, n−1 total | Terminal expectation does not automatically correct intermediate behavior actions |
| This project's Double DQN: online greedy endpoint selection, target-network evaluation | Endpoint is a greedy action value, closer at the endpoint to expectation under a greedy target policy; n−1 intermediate behavior actions remain | Current target multiplies none of these importance ratios and has no corresponding trace-cutting correction; intermediate off-policy effects remain a candidate factor |

Actual action selection/Double endpoint ties follow frozen `torch.argmax`; CPU tie cases verify behavior. Actual zero tie probability is not assumed. Unique-greedy/ignore-ties probability examples below are conditional assumptions only.

Under a deterministic greedy target policy, a nongreedy action has target probability 0 and corresponding importance ratio 0; with multiple greedy actions first define target-policy tie probabilities, rather than arbitrarily treating a tied optimal action as nongreedy.

The textbook also discusses per-decision control variates, Tree Backup, and its relationship to Q-learning. This project's “reward accumulation+greedy bootstrap” lacks those intermediate corrections and cannot be described as already implementing textbook off-policy correction. Equations 7.1/7.4 are supplied reading-record entry points for hand-calculated definitions, but action-value/Double endpoints/time truncation are separately defined here; textbook episodic termination does not replace this project's truncation protocol.

### Comparing directions in Rainbow and this project

**Literature results (paraphrased from supplied reading records, not reread/verified by GPT this round):** Rainbow combines Double Q, prioritized replay, Dueling, multi-step learning, distributional RL, and Noisy Nets. Table 1 uses n=3; authors treat n as sensitive and compare n=1, 3, 5, with records stating 3 was selected. Removing multi-step learning substantially lowers median performance; full Rainbow outperforms that ablation on 53 of 57 Atari games. Reading records accordingly summarize multi-step learning/prioritized replay as key components; this is limited to that paper's experiments, not a universal cross-task component ranking. Exact numbers/comparison metrics still require source-location acceptance.

**Old project data (hypothesis sources only):** changing ResNet-4 from n=3 to 1 increased scores by approximately **62.7, 72.5 pellets** in two old 120 k/300k conditions respectively; MLP effect directions were inconsistent. This is opposite to Rainbow's overall benefit from 3 steps, **not a logical contradiction under identical conditions or evidence of a discovered bug**. Atari contains multiple tasks, not uniformly one sparse-reward problem; maps/returns/budgets/networks/exploration/other Rainbow components differ. Frequent Pacman pellet rewards, death penalties relative to a pellet, and some shorter episodes are candidate task properties to quantify.

**Exploration-mechanism comparison (from supplied reading records):** with Noisy Nets Rainbow has ε=0, explores through network noise, and acts greedily with respect to the noisy network; this **does not mean consistency with the learning target policy**. Related variants without Noisy Nets use ε-greedy; records state annealing to 0.01 during the first 25 units of ten thousand frames. This project's formal recipe anneals ε from 1.0 to 0.05 over 120000 environment transitions, then retains 0.05. This compares exploration mechanisms only; Atari frames are not equivalent to project transitions, and **ε magnitude or ε=0 does not determine which has more severe policy mismatch**.

### Two categories of candidate explanation, neither confirmed

**A: Genuine task/recipe dependence.** Off-policy effects of intermediate behavior actions, target variance, bootstrap error, episode/death-penalty properties, and interactions with BFS distance-field input may affect n's influence. This round does not manipulate them or rank any as a known principal cause.

A specific candidate mechanism: window-start `A_t` is the action being learned; subsequent random nongreedy actions near ghosts may cause death, whose **−10 reward component** (possibly alongside power-pellet/step-cost components) is discounted into the multi-step target for the starting greedy action. Few events in critical states may produce large target changes propagated through repeated learning. This is a **preproposed, unverified mechanistic conjecture**, not an observed causal chain; it does not imply every negative multi-step return is erroneous credit assignment or should be removed.

Rough scale only: with 5 actions, a **unique greedy action**, an ε-greedy random branch uniformly sampling all actions, and approximately constant ε within a window, per-step random-branch nongreedy probability is `p=ε×4/5`. For n=3 the uncorrected target involves **n−1=2 intermediate actions** after the start; conditional on these assumptions:

- ε=0.05: `1−(1−0.05×4/5)^2 = 1−0.96^2 = 0.0784`, approximately **7.8%**.
- ε=0.5: `1−(1−0.5×4/5)^2 = 1−0.6^2 = 0.64`, approximately **64%**.

These are **rough magnitudes conditional on assumptions**, not measured replay fractions, bias fractions, or error rates. If g tied optimal actions all belong to greedy target support, per-step nongreedy probability falls to `ε×(5−g)/5`, and window probability is lower; if target tie handling supports only one, redefine under that rule. Early termination/changing ε also require actual trajectory counting.

**The proportion of affected windows does not measure impact magnitude.** This revision withdraws “approximately 8% cannot readily explain a large score difference” and “effects more likely occur only in the first 40% of training”; without phase interventions/state-time diagnostics,ε/window frequency does not establish either conclusion.

**B: Implementation/definition problems.** Termination/truncation bootstrap, discount exponents, endpoint states/Double action selection, queue flush, cross-episode/environment mixing, n=1/3 insertion timing, and actual update counts may contain implementation issues. Existing unit tests/report consistency/general cloud checks do not independently verify these targets. §§6/7 add analytically tractable small-MDP hand-oracle acceptance; passage excludes covered errors only, neither all implementation factors nor confirmation of A.

### Lessons from Retrace and applicability limits

Reading records describe Retrace's `c_s=λ min(1,π/μ)` as balancing high-variance importance sampling against Tree Backup's excessive truncation near on-policy behavior. Recorded Table 1 uses π/μ for importance sampling,λ for Qπ(λ) with guarantees depending on policy proximity,λπ for Tree Backup, and λmin(1,π/μ) for Retrace. This illustrates alternative off-policy multi-step treatments, not a universal claim that “using n=3 requires a particular correction.”

Safety/convergence guarantees under different π/μ must be read with the paper's specific finite/tabular operators, policies, sampling coverage, and other conditions, not reduced to “convergence guaranteed for arbitrary neural networks, replay, and nonstationary control.” Current fixed-n DQN is not directly equivalent to these λ-return algorithms. Policy mismatch is a reasonable candidate, but Retrace has not shown it caused this project's existing score loss.

### Actual references and source-location tasks

- Richard S. Sutton and Andrew G. Barto. **Reinforcement Learning: An Introduction**, 2nd edition, MIT Press, 2018, Chapter 7: n-step Bootstrapping. [Author's book page](http://incompleteideas.net/book/the-book-2nd.html); [public companion implementation](https://github.com/ShangtongZhang/reinforcement-learning-an-introduction). See this section's verification table for PDF/book pages and equations supplied by reading records, not independently verified by GPT this round.
- Matteo Hessel et al. **Rainbow: Combining Improvements in Deep Reinforcement Learning**, AAAI 2018, arXiv:1710.02298. [Paper entry](https://arxiv.org/abs/1710.02298); [ar5iv text](https://ar5iv.labs.arxiv.org/html/1710.02298); [Dopamine TF configuration](https://github.com/google/dopamine/blob/master/dopamine/tf/agents/rainbow/configs/rainbow.gin); [DQN Zoo implementation](https://github.com/google-deepmind/dqn_zoo/blob/master/dqn_zoo/rainbow/run_atari.py). The ar5iv entry locates supplied reading records, not a claim that GPT successfully accessed it this round.
- Rémi Munos, Tom Stepleton, Anna Harutyunyan and Marc G. Bellemare. **Safe and Efficient Off-Policy Reinforcement Learning**, NeurIPS 2016, arXiv:1606.02647. [Paper entry](https://arxiv.org/abs/1606.02647); [ar5iv text](https://ar5iv.labs.arxiv.org/html/1606.02647); [TRFL implementation](https://github.com/google-deepmind/trfl/blob/master/trfl/retrace_ops.py). Human researchers complete acceptance of precise theorem conditions/formula locations.

### Explicit uncertainties this round

- The old Res4 n=1 advantage opposes Rainbow's overall 3-step preference; causes may include genuine task/recipe dependence or implementation/definition issues. This matrix estimates effects/prespecified architecture interactions, **not specific A/B mechanisms or universal laws**.
- Contributions of off-policy effects, target variance, bootstrap, exploration, penalties, and input are unknown; window probabilities neither measure resulting score losses nor locate their training phases.
- Generalization of Res4 to CNN-2/Res8 is unknown, as are n=2, 5/other n, different maps/rewards/budgets/representations/full Rainbow recipes.
- Small-MDP passage does not guarantee every real training path is correct or completely exclude project implementation defects.
- No power analysis guarantees 5 seeds detect a 10-point effect; this round prioritizes estimation and allows wide intervals/inconclusive outcomes.

### Extended literature-verification table and withdrawn claims

The extended table below retains preceding definitions/calibrations. Levels describe **reading records provided by owner/local executor**, not GPT's reading level.

| Literature/entry | Supplied verification level | Limited permissible statement | Conclusions not yet permissible / GPT verification this round |
|---|---|---|---|
| Hessel et al., Rainbow, AAAI 2018, [1710.02298](https://arxiv.org/abs/1710.02298) | Full text | Records state n=1/3/5 compared and 3 adopted, with poorer multi-step ablation; limited to paper tasks/recipes/aggregate metrics. Retain original 53/57 source-location task | Not “n3 best on every Atari game” or universally “3 beats 1”; GPT did not reread full text/check ablation numbers this round |
| Munos et al., Retrace, NeurIPS 2016, [1606.02647](https://arxiv.org/abs/1606.02647) | Full text | Supplied c=λmin(1,π/μ)/off-policy discussion as theoretical background; attach original operator/policy/coverage conditions to guarantees | Reject generalization that “all uncorrected n-step methods have convergence guarantees only for close policies”; specific Qπ(λ) conditions are not all-algorithm theorems. GPT did not reread full text this round |
| Sutton & Barto, 2 nd edition Chapter 7, [author's book page](http://incompleteideas.net/book/the-book-2nd.html) | Full chapter/PDF, supplied pages 163–180 | Optimal n depends on task/estimation conditions; distinguish importance-ratio ranges/Tree Backup by definitions; pages vary by edition | Not “all off-policy methods require explicit importance sampling”; Tree Backup is a different treatment. GPT did not check original page numbers this round |
| Hernandez-Garcia & Sutton,2019, [1901.07510](https://arxiv.org/abs/1901.07510) | Abstract | Abstract notes report larger n beneficial under tested Mountain Car multi-step methods/conditions, and tested Sarsa/Q(σ) off-policy corrections possibly detrimental; suggests task/method dependence | Full recipe/n range/curves/significance/all conditions unchecked; not “increasing n always improves performance” or an exact reproduction protocol. GPT received 403 in that earlier batch; no rereading/independent verification this round |
| Fedus et al., Revisiting Fundamentals of Experience Replay, ICML 2020, [2007.06700](https://arxiv.org/abs/2007.06700) | Abstract; “lower target variance” is secondary | Records report uncorrected n-step particularly beneficial with larger replay capacity; capacity×n is a future candidate factor. Specific full-text interaction/causal explanations still pending | “Fedus found n-step harmful with small buffers” withdrawn; “large capacity lowers n-step target variance” only an unverified secondary lead. All current runs use capacity 10 units of ten thousand; capacity not manipulated, so not a Fedus reproduction. GPT received 403 in the earlier batch; did not reread this round |
| Elastic Step DQN,2022, [2210.03325](https://arxiv.org/abs/2210.03325) | Abstract | Records state poorly chosen fixed multi-step horizons may underperform single-step, suggesting horizon-selection sensitivity | Full method/tasks/baselines unchecked; no project mechanism/universal ranking inferred; author names/formal title require original bibliographic checking. GPT received 403 in earlier batch; no rereading this round |
| Mixture of Step Returns in Bootstrapped DQN,2020, [2007.08229](https://arxiv.org/abs/2007.08229) | Abstract | Records associate it with return length, bias/variance, exploration, and mixed returns; a search entry point | Full text unchecked, including claims “some result not reported”; absence from an abstract cannot prove absence from full study; formal bibliographic checking pending. GPT received 403 in earlier batch; no rereading this round |
| AI Safety Gridworlds,2017, [1711.09883](https://arxiv.org/abs/1711.09883) | Secondary | Retain only “a paraphrase associated n1 with conservative behavior/danger avoidance” as a source-tracing lead | Do not treat paraphrased n1 recipe/author attribution/avoidance mechanism as fact; attachment authorship/specific wording need source locations. GPT received 403 in earlier batch; no rereading this round |
| Daley & Amato, Reconciling λ-Returns with Experience Replay, NeurIPS 2019, [1810.09967](https://arxiv.org/abs/1810.09967) | Secondary | Retain as a search entry for replay with multi-step/λ returns | Cannot report implementation properties/experimental conclusions or equate λ returns with this fixed-n target. GPT received 403 in earlier batch; no rereading this round |

During the earlier incremental revision, attempts to access the six added arXiv abstract entries (1901.07510, 2007.06700, 2210.03325, 2007.08229, 1711.09883, 1810.09967) returned proxy 403. These are historical access records, not claims the sites still return 403. No original sources were reread this round; new titles/authors/abstract claims retain supplied-record levels, and links do not mean GPT read full texts. Separate prior implementation checks of the original three papers/textbook from owner full-text records.

**Retain prefreeze task: owner/advisor personally reads original sources used in paper arguments, recording reviewer/date/actual edition/source location/accurate statement; AI does not sign for humans.** Full-text records do not automatically constitute human sign-off. Untraced secondary content remains an unverified lead, not findings/theoretical guarantees. Related work may expand, without changing H1/H2/statistical thresholds through literature revisions.

Approximately 8 earlier web searches and limited abstract reading cannot establish novelty or summarize the field as “mainstream results oppose ours.” It is permissible to say “several retrieved studies benefit from multi-step under their conditions, while other work suggests fixed horizons may be unsuitable; the old Res4 observation warrants controlled review.” No retrieved Pacman interaction study≠no prior research. Next perform citation tracing, record search queries/dates, and ask an advisor to check coverage; multiple AI reviews are not scientific contributions.

## 10. Revisions, naming, and invariants

Internal marker v0.3.2 (Revision 1 + Rehearsal Addendum A + DSH Literal Corrections), with code spec_version/three fixed filenames remaining 0.3.2. This revision fully replaces old files rather than leaving implementers to infer priority from old documents/multiple deltas; actual-byte SHA-256/F establish freeze integrity. Retained version does not mean unchanged text hashes. A uniquely named outer folder/ZIP avoids overwriting prior downloads; internal names stay fixed for integration. This naming follows the owner's explicit current choice, taking priority over the earlier general “rename only when content changes” rule.

matrix.csv content is unchanged and always retains its filename matrix.csv; §7.1.3 defines blob bytes and -text preserves original CRLF, without redefining the following fixed SHA-256:

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

This package creates no additional matrix copy and does not rename frozen configuration. Treatment of all 11 earlier requirements is retained:

| Original requirement | Current specification |
|---|---|
| 1 Scheduling | CSV order/hash,6 configurations per seed block; no scheduling RNG;271828 only for bootstrap |
| 2 Validation count | Identical-weight strict> rule,15×50 after 300 k deduplication; all-train-path scope disclosed |
| 3 Replay/updates | Record replay.size/actual_updates; n3 at most 16 pending, not missing transitions |
| 4 Ties | Implementation argmax/CPU-CUDA tests on frozen version; reject assuming zero actual ties |
| 5 Truncation | New evaluation includes truncated; old files unchanged |
| 6 CSV-external parameters | Explicitly inject 1.0, 0.05, 0.4, 0.01, 10 from frozen configuration; no CSV columns added |
| 7 Initialization | Canonical n1/n3 hashes for 15 (architecture,seed) pairs, not 30 |
| 8 References | Function names/frozen commit, not outdated source line numbers |
| 9 Sign-off | Cloud agent is implementer/test author; humans fill human fields |
| 10 Layout | docs/prereg/ and results_prereg/ |
| 11 Core invariance | H1/H2,30 runs,last@300k,statistics/all seed partitions unchanged |

This revision is allowed before freeze; postfreeze specification/implementation changes must disclose timing/impact/version/rerun decisions, without silently replacing files under unchanged names/versions. New explanations after data viewing are labeled “post hoc”; new confirmatory studies use separate holdouts.

## 11. Adopted B1/B2: secondary, observational, noninterventional

Owner has decided to enable --window-diagnostics for all 30 formal runs. B1 measures subsequent-action mismatch against the selected greedy action at collection; B2 records co-occurrence of death/subsequent mismatch. They do not identify off-policy bias/causal mechanisms, are not “contamination rates” or “misattribution rates,” and do not enter H1/H2/selection/stopping/reruns. No new confirmatory hypotheses, p values, regression selection, or CIs.

### 11.1 Precise definition of “nongreedy”

#### 11.1.1 Use the online network at the actual decision, without retrospective recomputation

For every environment/action collection:

~~~text
g_t = the actual argmax action on the current input of the online network used for action collection at that time
A_t = the action actually executed after the original trainer's ε-greedy sampling
U_t = 1[A_t != g_t]
G_t = 1 − U_t
~~~

g_t directly reuses the training loop's existing greedy_actions(online,obs,device) return array. This function computes greedy actions in no_grad/eval mode, then restores train mode; parameters are the online parameters before updating in that 8-environment collection batch. The “network at that time” may differ between batches. **Do not use target/last/best networks, reassess at target updates, or add model forwards.**

U_t means “mismatch with the greedy action actually selected by the frozen implementation,” not “Q strictly below all optimal actions.” Another equal-valued tied action may satisfy A_t!=g_t; this is action mismatch relative to deterministic argmax, without setting tie probability to zero. Schema uses action_mismatch_to_selected_greedy to disclose this meaning. Studying “below maximum Q” later requires separately predefined value comparisons/tie metrics; do not silently replace this metric.

If the ε-greedy random branch selects g_t, U_t=0; explore_mask=true is not a substitute for U_t. Attempting a wall move and staying in the same cell is judged by executed action ID, not whether the next state changed.

All environments in a collection batch reuse actual trainer eps. Current code computes eps before env_steps increases; do not reinterpolate inside the action loop. Logs may retain original explore_mask for count verification, without additional random draws. Preserve current rng.integers call order/count for the full batch, even for environments outside the random branch; recording must not optimize away existing draws.

#### 11.1.2 What this does not measure

This measures mismatch “relative to the greedy action at collection time.” Networks may have changed by replay update; it measures neither update-time behavior/target importance ratios nor Q error, TD error, or bias. Death depends jointly on agent, ghost randomness, and prior state; co-occurring U/death does not identify which action caused death.

### 11.2 Window units, boundaries, and temporal assignment

**Count each n-step sample actually inserted into replay once, not again every time it is sampled for an update.** These are inserted-window fractions, not fractions of repeated gradient-update usage; diagnostic fields need not be added to 100000-capacity replay.

Each sample contains an actual action sequence within the same environment/episode:

~~~text
W_t = [(A_t,r_(t+1)), …, (A_(t+h−1),r_(t+h))]
h ∈ {1,…,n}
Starting action = A_t
Subsequent actions = A_(t+1),…,A_(t+h−1)     # h−1 actions
L_t = 1[at least one of these subsequent actions has U=1]
~~~

Record starting U_t separately, not in L_t. A complete n=3 window has two subsequent actions; n=1/h=1 tails have none, and L_t=0 by the empty-set definition. Endpoint bootstrap's greedy action is not an executed window action and is excluded from L_t.

Boundaries follow actual NStepReplay.add rules:

- Neither terminated nor truncated: emit the earliest window when n entries accumulate, retaining the last n−1 pending; windows may overlap, but each start counts once.
- True termination (death/win): flush all short windows under the original algorithm; each tail has its own h, not universally h=n; bootstrap discount 0.
- Time truncation: flush similarly without crossing reset; bootstrap actual truncated observation using γ^h. Truncation itself is not death.
- Training-budget stop: **no additional diagnostic flush**. Report not-yet-inserted tails as pending/unemitted, excluded from window denominators; do not extend training/create samples. For n=3/eight environments, at most 16 pending; n=1 has 0.
- Post-reset observations/actions cannot enter old-episode windows; environment queues remain strictly separate.

Freeze 15 start-transition bins: [1,20000], [20001,40000], …, [280001,300000].8-environment batches use batch_start_env_steps+i+1 (i=0..7); labels order collection records only, not 8 network updates within a batch. Assign windows by **start** bin, not emission time. Cross-bin windows belong to start bins; later emission backfills their counts, without prematurely closing bins. Report final pending separately by start bin.

Each bin/actual h also reports starting-eps sum/min/max/start count. The ε boundary 120000 aligns with bins, but cross-boundary windows may vary; do not treat “before 120000/after 120000” as a proven main-effect phase. Curves may use fixed bins, without additional phase tests or H1/H2 changes based on curves.

### 11.3 B1 metrics and denominators

For each run/bin b/actual h, N_bh is the inserted-window count. Maintain 8 integer cells C_bh[G,L,D], where D indicates actual death within the window; see B2.

Required outputs:

| Name | Formula/denominator | Interpretation |
|---|---|---|
| p_later_mismatch | sum(C[G,1,D])/N_bh | Fraction with subsequent mismatch among all windows of this h |
| p_greedy_start | sum(C[1,L,D])/N_bh | Fraction starting with the then-selected greedy action |
| p_later_mismatch_given_greedy_start | sum(C[1,1,D])/sum(C[1,L,D]) | Subsequent-mismatch fraction among greedy-start windows |
| p_later_mismatch_hge2 | sum_(h≥2,G,D) C[G,1,D] / sum_(h≥2) N_h | All windows with subsequent actions; exclude h=1 from denominator |
| p_later_mismatch_given_greedy_start_hge2 | sum_(h≥2,D) C[1,1,D] / sum_(h≥2,L,D) C[1,L,D] | Windows with subsequent actions/greedy starts; different denominator from preceding metric |
| full_horizon_fraction | N_(h=n)/sum_h N_h | Composition of full/short windows |

Give h=1, 2, 3 separately first (do not fabricate impossible h records), then all-h/h≥2 summaries. n=1 all-window p_later_mismatch may be 0; h≥2 denominator is 0 and must output numerator=0, denominator=0, rate=null, status="no_eligible_windows", not 0 implying observations. Apply the same zero-denominator rule to all conditional proportions.

7.8%/64% remain examples conditional on 5 actions, unique greedy action, uniform random branch, and approximately constant window ε. Observed complete h=3 windows cannot be equated directly with short/all-h mixtures; episode-end filtering/network-state changes mean conditional observations need not satisfy the simple independent-window formula either.

### 11.4 B2 metrics: death, subsequent mismatch, and greedy-start co-occurrence

#### 11.4.1 Death comes from environment info, not inferred from total reward

D_t=1 when actual info["died"]=true for a window transition; read PacmanEnv.step returns before reset. True termination may be a win and truncated may be a time limit; neither substitutes for died. A death transition may also collect a pellet, yielding r=−9.01 rather than −10; r==−10/r<0/term are not death criteria.

Within an episode death occurs at most once, at the window's last step, with action offset j_D=h−1. Record distinct events:

~~~text
T = D AND G_start AND L
J = D AND G_start AND 1[j_D≥1 AND U_(t+j_D)=1]
P = D AND G_start AND 1[there exists 1≤j<j_D with U_(t+j)=1]
~~~

T: “greedy start, subsequent mismatch, death within window”;
J: “after a greedy start, the action on the death step mismatches”;
P: “after a greedy start, an action mismatched before the death step.”

J/P may overlap and cannot be added as T; T equals J OR P. With h=1, T/J/P are all 0 even if the starting action leads to death that step. Strictly “before death” is P; “death on or after a subsequent mismatching action” is T. Report both to avoid confusing these temporal meanings.

#### 11.4.2 Required proportions

Give raw counts per bin/h and whole run:

| Name | Numerator / denominator |
|---|---|
| death_window_fraction | N_D / N |
| greedy_start_death_window_fraction | N_(G AND D) / N |
| cooccurrence_given_greedy_start_death | N_T / N_(G AND D) |
| cooccurrence_given_any_death | N_T / N_D |
| cooccurrence_of_all_windows | N_T / N |
| death_step_mismatch_given_greedy_start_death | N_J / N_(G AND D) |
| earlier_mismatch_given_greedy_start_death | N_P / N_(G AND D) |
| death_given_later_mismatch_greedy_start | N_T / N_(G AND L) |
| death_given_no_later_mismatch_greedy_start | N_(G AND NOT L AND D) / N_(G AND NOT L) |

The last two are descriptive conditional co-occurrence frequencies, not risk ratios of random actions causing death; state/survival filtering may confound them. Use null for every denominator of 0. Report short tails separately; one death appearing in overlapping windows is not multiple death events. Record independent death-transition counts for consistency checking.

Also record the **known component** of death penalties in window reward sums:

~~~text
Z_t = −10 × γ^j_D, when D=1; otherwise 0
~~~

This is the death-reward component calculated under reward accumulation, not total ret/TD target or an invertible decomposition of stored float32 ret;γ stays 0.99. Store sum(Z) per[G,L,D] cell; summarize its mean in N_(G AND D) windows and in T windows. A nonzero-death-component absolute-value fraction may be sum(|Z|·1_T)/sum(|Z|·1_D), with denominator explicitly all death-window components; still descriptive, not “wrong-credit fraction.” With no deaths denominator 0; no correlations/regressions/tests.

Do not additionally read online/target Q for counterfactuals or remove mismatch samples. “−10 enters the greedy-start multi-step return” is observable arithmetic under the target definition; whether inappropriate or explanatory requires next-round intervention.

### 11.5 Implementation interface, storage, and aggregation

The following is the frozen implementation-interface contract;6023b1a contains the main wiring, and GPT only statically read it this round:

- greedy/actions/eps arrays already exist in dqn.train; reuse them.
- dqn.collect_step obtains r/term/trunc/info; currently replay.add precedes reset. Observer receives scalar events once these facts are known, before reset.
- NStepReplay.add handles queues/flush, NStepReplay._emit actual insertion, and sample only samples existing data. Original replay/TD-target interfaces retain behavior.

Use separate per-environment scalar deques of maximum length n (at most n−1 after processing), recording G/U, died, won/term/trunc, start label/eps. Do not store obs/next_obs/Q vectors/state_dict or add replay fields. Recorder constructs descriptions following actual emitted windows and provides a read-only emission-verification hook for h/count/order; do not infer cumulative insertions from replay-size differences, since size stops growing at capacity.

Logging/observer calls must not reset early, alter returned obs, or change queue/pop/flush; observer state does not enter sampling/loss/optimizer/update budget. Formal runs do not resume; diagnostics need not promise equivalent recovery after losing environment state. If interrupted smoke needs diagnostics, mark partial and repeat acceptance from scratch rather than concatenate interrupted queues.

Target output: results_prereg/runs/<run_name>/window_diagnostics.json. Fixed schema_version="window-diagnostics-1", definition_version="1" (strings); meta records git_sha=F/run_name/arch/n_step/run_seed. Top level records transition_budget, window-statistics source="emitted_once", h/bin boundaries, per-bin C tables/counts/eps summaries, per-bin pending, whole-run summaries, independent death count, and integrity flags. Counts are nonnegative integers (Python arbitrary precision or sufficiently capacious int64/uint64; avoid unsigned subtraction underflow); death-component sums use float64. Save every rate with numerator/denominator; no NaN.

Each bin/h also lists mutually exclusive end_kind_counts: nonterminal/death/win/truncated, classified by actual final-step reason for that inserted window. Their sum equals N_bh; death equals the C-table D=1 total. All flushed tails after termination/truncation count the same final-step reason individually; do not classify every short h as death.

Diagnostic snapshots may be written at existing low-frequency log refreshes, at most 15 periodic refreshes plus final complete file; prohibit per-transition synchronous writes/printing. Publish final successful files atomically; count inconsistencies explicitly report diagnostic errors and retain facts, without silent omission.

These are **auxiliary outputs**. Frozen documents/manifest bind definitions/diagnostic-code hashes; separately bind all 30 diagnostic-file hashes with window_diagnostics_seal.json, then perform one centralized descriptive summary. Do not insert these into evaluation_seal's core input set and violate the v0.3.2 analyzer's “exact required files” contract. Retain core entry/input/output H1/H2 numbers/labels unchanged; diagnostic summaries are separate Markdown/JSON attachments.

Per configuration provide each seed's raw proportion first, then mean/ddof=1 standard deviation/effective denominator count for 5 run proportions. Retain null/identity for runs with denominator 0; use defined items only for that metric's mean, explicitly reporting k/5 rather than a 5-seed confirmatory estimate. Mean=null if k=0; sample standard deviation=null if k<2, with reason, no NaN. Separately name weighted sum-numerator/sum-denominator proportions. Fix 15-bin time curves, per-run first then configuration aggregates; overlapping windows are not independent observations for binomial CIs. No new p values/regression selection/diagnostic ranking/confirmatory CIs.

During training check counts/finiteness/write success; do not adjust ε/budget/architecture/order/seeds/selection/reruns based on proportions/curves. Interpret centrally with formal results only after all 30 complete; mechanism attribution after data viewing is “post-hoc explanation.” Do not fabricate missing diagnostics; handle objective infrastructure faults before formal-score unsealing, without diagnostic-value decisions about worthwhile reruns.

### 11.5.1 Explicitly accepted implementation differences and records

- meta.git_sha=actual training F is accepted; frozen manifest determines C, and auxiliary seals record C/F; do not call F code C.
- U uses only actions!=greedy, accepted; explore_mask checking was optional, so its absence does not change the metric. Random branch selecting g still gives U=0; a tied equal-valued alternative may still give U=1.
- No formal resumption; resumed runs do not generate complete diagnostics, accepted. Partial cannot be concatenated into complete formal logs. Diagnostics must not restore old environment queues/change real training.
- No switch added to TrainConfig/frozen configuration, accepted as **procedural binding**: FREEZE_CHECKLIST in F/external record explicitly state “30/30 enabled,” retain fixed formal command/all actual launch records, and check 30 complete files/F at completion. Benefits are unchanged configuration/CSV contracts and existing algorithm configuration; cost is that configuration schema cannot automatically reject CLI omissions, requiring prefreeze command review/auxiliary sealing. Do not claim code automatically enforces all 30. Report missing records/deviations without fabrication, diagnostic-based retraining, or rejection of core integrity.
- Z uses fixed DEATH_REWARD=-10, accepted only for this frozen environment; add independent environment-reward-component contract tests for death penalty −10 and death+pellet total reward=−9.01 still recorded through info.died. Death is not guessed from total reward.
- One extra code_version/git read at initialization is not per-step synchronization and invokes no random numbers/network; include wall-time cost rather than call it cost-free.

Auxiliary seals/summaries check actual hashes of both diagnostic-code files against frozen manifest and each meta.git_sha=F; current script saves code_sha256 but does not yet verify frozen correspondence in verify_seal. Minimal additions are in specification §9.2. Diagnostic JSON outputs all defined metrics; Markdown uses fixed summary columns in specification §9.3, not result-dependent choices. Raw files retain bin/h detail; configuration curves use 15 fixed all-h bins alongside h≥2, without confirmatory binwise tests.

### 11.6 Overhead and no-side-effect acceptance

No extra forwards/training RNG/per-step CUDA synchronization; only per-environment scalar queues of at most n and 15×h×8 count cells, with no replay fields. Extra replay memory 0; scalar structures estimated KB–hundreds of KB, distinct from process-peak differences. Third-batch A1000 short-load reports satisfy original thresholds: median wall-clock≤5%, additional peak main memory≤16MiB/process, reported approximately −0.54% wall clock/−0.6% process training and +1.5MB working set. These are executor-provided, not GPT runs; thresholds are not scientific-effect criteria.

Quick covers 6 configurations×900/901 with effective learn_start=500/2k steps and updates; load covers parallel res8n1/n3 at 110 k/buffer 100k in four off/on/on/off batches using separate directories, without formal seeds. Attachment reports 4 sets of identical last/best hashes/actual_updates; n3 has 110000=109984 insertions +16 pending. Only two pairs, nonrandomized ABBA, short load/res8 only: no all-architecture 300 k/full-round thermal-stability inference. If final changes affect only sealing/summary/docs, retain recorder-overhead evidence, while freeze candidate still tests formal load. If collection wiring/recorder changes, repeat off/on equality/A1000 overhead without changing parameters just to pass.

Acceptance covers these independent hand-calculation/actual-wiring tests (expectations not reverse-engineered from tested scripts), with personnel/execution levels still separate:

| Test | Hand-calculated/independent expectation |
|---|---|
| Random branch selects greedy | explore=true,A=g⇒U=0; not subsequent mismatch |
| Tied actions | Q=[0,2,2,1,0], actual g=1,executed A=2⇒U=1; selected-action mismatch, not strictly suboptimal Q |
| Complete three-step greedy chain | G=[1,1,1], no episode end⇒h3,G_start=1,L=0,D=0,C[1,0,0]+=1 |
| Mismatch on death step | G=[1,1,0],death on step 3⇒h3 T=1,J=1,P=0,Z=−9.801; flushed h2 still starts greedy,T=J=1,P=0,Z=−9.9; h1 nongreedy start,L=0,T=0,Z=−10. Independent death events 1,death windows 3 |
| Mismatch before death | G=[1,0,1],death on step 3⇒h3 T=1,J=0,P=1; h2 nongreedy start,T=J=P=0; h1 greedy start/no subsequent action,T=J=P=0; still 3 death windows |
| Two-step truncation | G=[1,0],step 2 trunc/no died⇒emit h2/h1,D=0/all Z=0; h2 L=1; original target bootstraps actual truncated observation, excluding post-reset actions |
| Win | term=true,won=true,died=false⇒D=0; not all term events are deaths |
| Death+pellet | reward=−9.01,info.died=true⇒D=1; calculate only discounted −10 component, not total reward as death component |
| Nongreedy start | G=[0,1,1],death on step 3⇒G_start=0; exclude from greedy-start T/J/P co-occurrence |
| Training tail | n3/two nonterminal transitions⇒no window yet,pending=2; no flush at budget stop; n1 on same stream already has 2 samples |
| 2 interleaved environments | Each has preceding short chains; counts equal sum of separate executions, without queue/episode mixing |
| Cross-bin | start global_id=20000,later two steps>20000⇒h3 belongs to bin 1, not emission bin; start 20001 belongs to bin 2 |
| Cumulative insertion/capacity | Small capacity/repeated wraparound⇒cumulative windows keep increasing, not replay.size; whole-run insertions+pending=collected transitions |
| 0 denominator | n1 h≥2⇒numerator=denominator=0,rate=null; zero-death conditional proportions also null, no JSON NaN |
| Death in repeated windows | Each death occurs in at most n inserted windows; independent death transitions separately counted; N_D≤n×death_events; C sum equals total insertions |
| Aggregation | Two run proportions 1/2 and 9/10⇒run mean 0.7,ddof 1 sd=√0.08≈0.282842712474619; weighted 10/12=5/6; not the same value |
| No algorithm side effects | Same CPU training,logging off/on: identical actions/RNG states/inserted obs,act,ret,disc,next_obs/order,updates,loss,online/target/optimizer states,best step/weights; wall time/new diagnostic files may differ |
| No extra forwards/synchronization/RNG | Call counts/spies on actual train/collect paths; logging on adds no model calls,torch RNG,training rng calls, or extra per-step tensor.item/cpu synchronization |
| Central analysis isolation | Same synthetic core input yields identical all H1/H2 numbers/labels with/without diagnostic sidecar; diagnostic summary does not access formal test/checkpoint selection/trainer parameters |

Tests cover actual wired call paths, not only isolated counting functions. Add at least 2 planted bugs: include start in L and replace died with term; original independent expectations must turn them red.

Humans still fill human-review fields;20 hand-calculation/19 wiring tests and attachment 415 passes do not automatically constitute an independent personnel audit. Add frozen-F/hash/death-constant tests under specification §9.4.

## 12. Future research A1–A7 and sample-size/budget planning (outside this round)

All are next-stage candidates, outside this round's 30 runs. Hypotheses are **candidate predictions requiring separate registration**, not existing findings; thresholds/primary contrasts/multiplicity rules must be fixed before the next launch. Record reasons for choosing directions based on this round; questions may be inspired by seen results, but validation data must be new.

Timing gives A1000 workload magnitudes only. Machine B is unvalidated, without speedup/timing guarantees; equivalent smoke on B precedes measured extrapolation. Below 12–20 seeds is a planning range; formal confirmation generally starts budgeting at 20 under this section's power plan, then fixes counts by target-power calculations. If only 12 are feasible, explicitly frame estimation/exploration rather than guarantee H2 power.

### A1: n-step × replay capacity

- **Candidate prediction:** with other conditions fixed, smaller capacity makes n3 worse relative to n1; prespecified endpoint interaction K=Δ_(40万)−Δ_(2.5万)<0,with Δ still n1−n3. Separately measure target distributions to test “capacity changes variance”; score interaction alone does not establish variance mechanisms.
- **Register:** one fixed architecture (prefer res4),capacity{25000,100000,400000}×n{1,3},300k/new common budget,seed count/pairing,learn_start/actual update rules,uniform sampling,absolute epsilon schedule,primary contrast/threshold,train/test partitions. Prespecify fixed replay ratio/sample-age/update reporting; do not change replay sampling strategy with capacity.
- **Machine/time:** recommend validated 32 GB machine B. 7×24×32, two uint8 obs/next_obs arrays at 40 units of ten thousand capacity total approximately 4.3008GB(4.005GiB),arrays only, not full process; adding approximately 1.5GB PyTorch/CUDA baseline gives roughly 5.8GB/process,saving peaks measured separately. 6 configurations×12–20 seeds=72–120 runs; provisional res4 estimate 39 minutes/concurrent process gives approximately 23–39 A-equivalent hours; capacity-related throughput/memory changes unknown.
- **Relation to this round:** only 10 units of ten thousand capacity, no capacity interaction estimate. H1/H2 may motivate further decomposition,but no outcome establishes Fedus reproduction.

### A2: n-step × exploration schedule

- **Candidate prediction:** lowering ε floor reduces n3 disadvantage relative to n1:K=Δ_(ε_end=.01)−Δ_(.05)<0; “reduced bias” remains interpretation, not established by score interaction alone. Adopted B1/B2 describe affected state/time frequencies only.
- **Register:** fixed architecture,n{1,3},ε_end{.05,.01},annealing length{60000,120000},otherwise identical; primary interaction specified first. For a cheaper floor check,fix 120000 annealing and 4 configurations first; do not change length simultaneously then attribute everything to the floor. Lock new holdout/window-co-occurrence recording beforehand.
- **Machine/time:** A1000 can run it. 4 configurations×12–20 seeds at estimated res439 minutes gives 16–26 hours; full 8 configurations×12–20 seeds 31–52 hours. Workload under current throughput, not measured exploration-recipe speed. B may be used after validation.
- **Relation to this round:** fixed ε cannot test interaction. Large/small window fractions do not select schedules; curves cannot establish effects “only in the first 40%.”

### A3: Explicit off-policy treatment controls

- **Candidate prediction:** at least one prespecified treatment improves new-seed scores over uncorrected n3 and narrows the n1 gap. Supports “target construction matters,”not off-policy bias as sole cause; correction also changes effective horizon/variance/data usage.
- **Register:** initially n1,original n3, and one Watkins-style trace-cutting arm,freezing cutoff location/actual h/Double endpoint; subsequent Tree Backup/Retrace studies define target policy,λ,behavior probabilities, valid coverage,tie support. Each arm first passes independent small-MDP hand-oracle/mutation tests. **Expected-Sarsa terminal expectation under the same deterministic greedy target degenerates to original greedy bootstrap, not a distinct correction arm**; a nondegenerate target policy must be registered as an additional change, and terminal expectation does not correct intermediate actions.
- **Machine/time:** A1000 suffices for current models; validated B for more arms. 3 arms×12–20 seeds at res4 throughput approximately 12–20 hours;5–6 arms start at 20–39 hours,extra sampling/computation unknown. Implementation/hand-acceptance development time excluded.
- **Relation to this round:** no correction arm. H1 support/high B2 co-occurrence does not bypass controlled comparisons; “matching n1” does not directly establish a bias mechanism.

### A4: Separate input representation from network structure

- **Candidate prediction:** identical information changes the old “MLP beats convolution” gap; otherwise argues against the strong “information difference explains all advantage” claim. Existing 29-dimensional features differ from 7 channels,so old rankings cannot be attributed purely to architecture.
- **Register:** first MLP reads flattened identical 7-channel input alongside convolutions with the same information,plus identical 5-channel raw-grid controls,forming network×representation. Fix n/budget,define parameter matching/optimizer/normalization/encoding controls; studying n interaction requires explicit n{1,3} expansion/prespecified primary contrast. Handcrafted 29 features are a separate representation arm.
- **Machine/time:** remeasure memory for new MLP input/width/replay format; recommend validated 32 GB B,A adequacy depends on new smoke. 4 configurations×12–20 seeds=48–80 runs; current rough 25–75 minutes/process implies 10–50 hours with two concurrent processes; new model speed entirely unmeasured,range is occupancy planning only.
- **Relation to this round:** all three architectures share fields input, allowing architecture dependence estimates,but no MLP control; H2 does not validate old MLP/convolution attribution.

### A5: Separate depth from parameter count/computation

- **Candidate prediction:** parameter matching narrows old between-architecture score/Δ gaps; if stable differences remain,argues against “parameter count explains all gaps.” Parameter matching does not simultaneously match FLOPs,receptive fields, or optimization difficulty.
- **Register:** depth set,widths matching parameter budgets,residual/plain-convolution structures,n,budget,primary contrast,parameter/FLOPs records,seeds. Fix matching before new scores, without performance-based widths; separate names for additional compute-matched arms.
- **Machine/time:** prefer validated B,A may smoke first. Example 4 structures×2n×12–20 seeds=96–160 runs; current architecture-mixture workload approximately 35–85 A-equivalent hours; new widths may substantially change overhead,replace estimates with smoke measurements.
- **Relation to this round:** structure,parameters,receptive field,compute all vary; call it “architecture effect,”not pure causal depth effect.

### A6: Budget scaling, controlling exploration first

- **Candidate prediction:** Δ_(100万)−Δ_(30万)<0,longer budgets narrow n1 advantage.Δ_(100万)>0 still means n1 better under that budget; narrowing does not mean “identical final performance,”and reaching 100 units of ten thousand does not establish asymptotic performance.
- **Register:** budgets{300000,1000000},n{1,3},architecture scope/paired seeds, fixed endpoints,primary budget interaction/threshold,new val/test partitions. **Lock absolute ε annealing at 120000 steps**: directly applying original eps_frac=.4 to 100 units of ten thousand produces 40 units-of-ten-thousand-step annealing,confounding exploration. Next stage may implement absolute steps or set million-step eps_frac=.12; this does not change current .4.
- **Recommended design:** train new seeds to 100 units of ten thousand, retain fixed checkpoints at 30/100 units of ten thousand under one absolute ε schedule/other rules, and use paired learning curves/budget differences. 30 units of ten thousand is prespecified, not test-selected. Reuse training prefixes,evaluating both checkpoints on the same new test initial states as next-stage paired results. Start with Res4 budget replication; testing H2 budget dependence requires at least cnn2/res8, not Res4-only extrapolation.
- **Machine/time:** prefer B after complete smoke validation; no B estimate. A1000 res8 million-step runs extrapolate 55 minutes×100/30≈183 minutes under current two-process load,approximately 3.1 hours; old 86-minute throughput would imply 4.8 hours,so no 3-hour promise. 40 Res4 million-step trajectories(2n×20 seeds)roughly 43–70 A-equivalent hours under short-smoke/old throughput; all 3 architectures/120 million-step trajectories 147–213 hours(6–9 days),extra testing/failures separate. Running 30 units of ten thousand/million budgets separately from scratch without prefix reuse gives all 3 approximately 191–277 hours(8–12 days). Assumes approximately linear throughput; million-step load/thermal throttling require measurement.
- **Additional implementation gate:** current train_seed block base 1000000/episode guard serve 300k. Conservative episode bounds at a million may exceed blocks; next round must revisit seed namespace/blocks/runtime guards, not just total_env_steps.
- **Relation to this round:** stop strictly at 300 k, no extra checkpoints/extension. Old 120 k/300k cross-condition results motivate but do not replace controlled next-stage budget interactions.

### A7: More training seeds for estimation/replication

- **Purpose/testable prediction:** independently replicate the same fixed effect/interaction with new seeds and assess more precise support/refutation of prior magnitude predictions. **Seed count is not an “algorithm improvement” factor**; one larger sample need not narrow intervals, and “more seeds mean more significance” is not a hypothesis.
- **Register:** new seed count/range,pairing, same architecture/budget,primary predictions/thresholds,σ/target-effect sources for sample planning, fixed stopping,new holdout. Current 5-seed results may plan next-round variance,but disclose they were seen and exclude them from independent confirmatory means; no adding seeds based on interim p/CI.
- **Machine/time:** prefer smoke-validated B,A feasible but slower. Full 3×2:12 seeds=72 runs,scaled from current 11–16 hours gives 26–38 A-equivalent hours;20 seeds=120 runs 44–64 hours;40 seeds=240 runs 88–128 hours. Do not apply these numbers to changed models/budgets.
- **Relation to this round:**5 seeds unchanged;20 next-round seeds are a feasible budgeting start, not a power guarantee. See§12.8.

### 12.8 Basis for A6/A7 seed-count and power planning

**Default next-round budget:20 independent training seeds per cell;12 is an estimation/exploration minimum if resources are insufficient.** “10 exceeds 5” does not establish sufficient H2 power; effects barely exceeding 10 require more seeds. Complete this round first, then estimateσ_C using all 5 c[s], without choosing the most favorable primary effect.

H2's unit is c[s]=d[res8,s]−d[cnn2,s]; use the **standard deviation of these paired interaction differences**, not within-model episode sd or 1500 episodes as training samples. No current analysis changes are needed.

If next round retains both predictions/97.5% intervals,H2 support requires the CI wholly outside 10. For a planned positive true C*,estimate δ=|C*|−10>0, not distance of|C*|from 0. Known-variance normal approximation for approximately 80% power:

~~~text
N ≈ [(z_0.9875 + z_0.80) σ_C / δ]^2
  ≈ 9.5050367452 × (σ_C/δ)^2
~~~

Planning approximation only, not formal statistics; final N uses noncentral t/prespecified simulation,accounting for finite-N variance estimation. If retaining H1,similarly planσ_Res4/|Δ*−10|and take the larger N required for intended predictions; if H2 alone,reregister coverage/multiplicity rather than silently retain/change α.

All following are hypothetical scenarios, **not observations this round**:

| Assumedσ_C | Assumed\|C*\| | δ(distance from 10 threshold) | Normal-approximation N,rounded up | Interpretation |
|---:|---:|---:|---:|---|
| 10 | 20 | 10 | 10 | Finite-sample t generally needs more;12–20 is a reasonable start |
| 20 | 30 | 20 | 10 | If effect clearly exceeds threshold,20 may suffice,still check t planning |
| 20 | 20 | 10 | 39 | 20 may be insufficient; approximately 40 or more,exact planning determines |
| 30 | 30 | 20 | 22 | 20 may still be insufficient; consider 24–30/recheck target |
| 30 | 20 | 10 | 86 | High time cost; more test episodes cannot replace training seeds |

If|C*|=10,δ=0, no finite N guarantees high-probability support with “interval wholly>10.” This is the strict magnitude threshold, not a program bug. H2 “refutation”(interval wholly between −10 and 10)needs separate power planning for true C near 0 and both boundaries, not the support formula;20 may still be insufficient.

Also use interval precision for budgets; with fixed difference sd,97.5% t half-width:

| N | df | t(0.9875,df)/√N,i.e.,half-width/sd |
|---:|---:|---:|
| 5 | 4 | 1.5631930548 |
| 10 | 9 | 0.8490749818 |
| 12 | 11 | 0.7485613791 |
| 20 | 19 | 0.5441337732 |
| 30 | 29 | 0.4315772723 |

Thus 5→20 reduces half-width to approximately 35% at unchanged sd, not automatically supporting every uncertain result. With N=20,sd=20,half-width≈10.88; even C=0 does not fit wholly within(−10,10),so H2 remains uncertain.

σ estimated from 5 c values is unstable. Under normality,df 4 one-sided 95% upper bound is s_C√[4/χ²_(.05,4)],with χ² quantile≈0.7107230214,approximately 2.37236s_C;5-observation sd is not precisely known. Reportσ sensitivity,use conservativeσ, or prespecify an internal variance trial; internal sample-size reestimation requires fixed rules without effect-direction-based N. This round does not use this bound to change sample size.

The t table,normal-approximation coefficient,and χ² quantile retain previous independent mathematical-check records, not real results/tested analysis script; not all entries were recalculated in this integration.

Suggested priority: complete current review; if H2 precision insufficient,prioritize A7/new 300 k seeds without simultaneous factor changes; if insufficient training is the main concern,use A6/uniform-exploration budget comparisons. Do not pursue A1–A7 simultaneously as multiple underpowered searches.

Latest overhead records do not alter future predictions,20-seed starting budget, or power limits; only add evidence for the compact recorder under specified res8 short load. CNN2/Res4 formal-load remeasurement remains pending; future workloads are rough A-equivalent estimates, not known 5070 Ti speedups. A6 million-step prefix reuse/A7 new seeds require new registration/review of million-budget seed blocks/guards.

Local supplement C1 (another standard-environment learning experiment) adds only limited end-to-end checks; different directions do not exclude every Pacman bug. C2 old-curve analysis, if conducted,is post-hoc exploration. Limited literature searches support neither “mainstream opposition/novelty” nor audits alone as algorithmic contributions. Withdrawn claims concerning 7.8%/impact,first 40%,Noisy Nets/policy matching, and Fedus/small-buffer harm remain withdrawn.
