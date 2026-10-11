# Architecture × n-step: protocol summary for readers

> This is a translation for readers. The Chinese originals are the frozen, authoritative texts; in case of any difference the originals govern. Protocol SHA-256: `3030e3eee70eca95ecf03d70ea94d97e2bf0163c4bf07f5bc0dc70ad2c362dcc`. Analysis specification SHA-256: `a4d64d46ed72d0c6e83cb1276f09e136a0639ee2db92954044a22cc642225100`. Frozen commit F: `92bf82eca0dae731f7396ed5b4e887e4f3b200e4`.

This concise reading copy summarizes the frozen protocol, not its execution or outcomes. Parenthetical references identify the authoritative Chinese sections. “Protocol” means PREREG_ARCH_NSTEP_v0.3.2.md; “Analysis” means ANALYSIS_SPEC_v0.3.2.md.

## 1. Question and controlled design

On one fixed Pacman map, with identical privileged BFS distance-field input and an equal environment-transition budget, what does changing n-step from 3 to 1 do to convolutional-agent scores? Does that effect depend on architecture? Previously viewed Res4 observations motivate replication but are excluded from the new estimates. Architecture comparisons jointly change structure, parameter count, receptive field, and computation; they do not isolate depth. (Protocol §1.)

| Architecture | n-step levels | Training seeds | Runs |
|---|---|---|---:|
| cnn2 | 1, 3 | 100–104 | 10 |
| res4 | 1, 3 | 100–104 | 10 |
| res8 | 1, 3 | 100–104 | 10 |
| Total | | | 30 |

Each run receives 300000 transitions. The common recipe uses 7-channel fields input, width 16, Double and Dueling, γ=0.99, τ=0.01, Adam learning rate 0.0005, batch 32, replay capacity 100000 with uint8 encoding, learn_start=4000 stored samples, 8 environments, and steps_per_update=4. ε falls linearly from 1.0 to 0.05 over 120000 transitions, then stays at 0.05; global gradient-norm limit is 10. Rewards are pellet +1, actual death −10, win +10, and step −0.01; episodes have a maximum of 1000 steps. These values are fixed across configurations. (Protocol §2.)

Use the A1000, validated on short loads, with 2 training workers and common dependencies; full-load resource checks on the final freeze candidate remain required. Final testing uses CPU with 1 torch thread per model. Equal transitions do not mean equal FLOPs, time, or update counts. Record replay.size and actual_updates. matrix.csv fixes dispatch order and retains SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`. (Protocol §§2, 6.)

---

## 2. Endpoints, hypotheses, and exact decisions

The primary endpoint is the last checkpoint's mean standard-test pellet score at 300000 transitions. Best is secondary: select the first strictly maximal GPU-validation mean, with validation every 20000 steps. Identical duplicate final validation is removed, yielding 15×50 validation episodes; deduplication does not change selection under the specified identical-weight/settings/score conditions. Optional hard evaluation uses last only, with chase probability 0.7, and must be decided before formal launch. (Protocol §4.)

Let m[a,n,s] be a model's mean over 300 test seeds. Define d[a,s]=m[a,1,s]−m[a,3,s] and c[s]=d[res8,s]−d[cnn2,s]. Auxiliary interactions are d[res4]−d[cnn2] and d[res8]−d[res4]. Positive c means a larger n=1 gain for res8, not necessarily a higher absolute res8 score under n=1. (Protocol §5; Analysis §3.)

With [L,U] denoting the corresponding 97.5% two-sided training-seed t interval:

| Prediction | supported | refuted | uncertain |
|---|---|---|---|
| H1: Res4 mean gain ≥10 | L>10 | Otherwise U<10 | Otherwise |
| H2: absolute res8-versus-cnn2 interaction ≥10 | L>10 or U<−10 | Otherwise L>−10 and U<10 | Otherwise |

H1 positive_gain_refuted additionally equals U<0. Boundaries are strict and decisions use unrounded values. With 5 seeds, H1 support requires `mean(d)>10+[3.4954059325164377/√5]·sd(d)`, approximately `10+1.5631930548·sd(d)`; 10 alone is not the required mean effect. (Protocol §1; Analysis §6.)

Separate descriptive signals use 95% t intervals: direction_signal[a]=supported_signal if mean(d[a])≥10, L>0, and positive_count≥4; interaction_signal=supported_signal if abs(mean(c))≥10 and (L>0 or U<0). Otherwise each is insufficient_evidence. Signal support is not H1/H2 support. Best/hard do not generate additional confirmatory decisions. (Analysis §6.)

---

## 3. Statistical analysis and input integrity

Training seeds, not episodes, are the statistical units. Report all 5 raw paired differences, mean, sample sd with ddof=1, and sign counts. Integer numerators and exact rational means/variances precede float64 conversion, square root, se, and t intervals under the unique operation sequence. Do not use rounded displays for decisions. (Protocol §5; Analysis §3.)

The 95% t critical value is 2.7764451051977944; H1/H2 use 97.5% intervals with 3.4954059325164377, both df=4. Bonferroni allocates α=.025 per prediction. Approximate normality of independent seed differences is an assumption that the small sample cannot reliably verify. Zero sd yields a labeled degenerate interval, not evidence of unlimited precision; intervals are not clipped. (Analysis §4.1.)

Crossed-bootstrap sensitivity uses 10000 replicates and `numpy.random.Generator(numpy.random.PCG64(271828))`. Each replicate independently draws 5 training-seed-block indices with replacement, then 300 test-seed indices with replacement, sharing both draws across every configuration and endpoint. Fixed call order and index-stream checks apply; percentile 95% intervals use `np.quantile(...,method="linear")`, type 7. Bootstrap does not replace training seeds. (Analysis §4.2.)

Res4 alone receives a prespecified one-sided exact sign test of positive-difference probability conditional on nonzero differences. Zeros are excluded and counted: 5/5 positives give p=1/32=.03125; 4/5 give 6/32=.1875; no effective samples gives p=1 with status=no_effective_samples. This is not a zero-mean test and does not determine H1/H2. (Analysis §5.)

Each required last/standard.json and best/standard.json has exactly 300 unique seeds, precisely 30000–30299; enabled hard requires all runs' last/hard.json. Required episode fields are seed, score, steps, died, won, truncated. Scores are finite integral values in 0–377, steps in 1–1000; won implies score=377, exactly one end flag is true, and truncation requires steps=1000. Any failed integrity check terminates rather than silently skipping data. Synthetic acceptance, including F1–F8/E1–E13, precedes freeze; formal analysis is centralized and performed once. (Analysis §§1, 2, 8.)

---

## 4. Sealing, freeze identity, and execution sequence

Initialization/exploration uses 100–104; training episodes use `1_000_000 × (run_seed + 1) + episode_index`. Validation uses 21000–21049, sealed testing 30000–30299, smoke evaluation 40000–40009, and smoke training 900/901. Legacy EQUIV_SEEDS=20000–20299 is for non-learning-agent fidelity only. Identical paired seeds provide common initial states, not identical full trajectories. (Protocol §3.)

Code commit C fixes code and the full accepted runtime snapshot docs/prereg/dependency_lock.txt. Freeze commit F changes only the permitted configuration/manifest/protocol/specification/handoff/checklist files. F and manifest's own SHA-256 are recorded externally before first formal training; they are not self-embedded in F's configuration/manifest. Training, final evaluation, and formal analysis verify their respective C/F identities and current hashes. (Protocol §7.1; Analysis §1.2.)

Hashes concern raw working-tree bytes, without line-ending normalization or JSON reserialization. Frozen paths have -text attributes committed in C; fixed matrix bytes retain their CRLF identity. A fresh exact-F clone on formal Windows/A1000 must reproduce every frozen-file hash. Before training and before test permission, common binding checks require complete manifest, matching C, all required/current file hashes, and all three configuration-hash bindings. Missing or inconsistent bindings reject execution. (Protocol §7.1.1–7.1.4.)

The owner approves and retains the external FREEZE_RECORD and original GitHub Release asset/server-time/download-hash receipt; the executor checks them before first launch and retains launch records. Self-entered UTC alone is not independent timing proof. After all 30 fresh runs, reread full current training/checkpoint integrity, explicitly unseal, evaluate the whole matrix centrally, seal outputs, and analyze once. Actual final-evaluation environment evidence is saved separately and hash-bound; it cannot be backfilled into the prelaunch record. (Protocol §7.2–7.5.)

Sealing is protocol-based, not an unbypassable security boundary: lower-level APIs/public constants/source edits can bypass guards. Objective infrastructure failures are retained and may justify same-code/configuration/seed reruns from scratch; low scores do not. Formal resumption is excluded. Core algorithm/environment bugs require explicit uniform revision rather than retaining favorable old runs. (Protocol §§5–7.)

---

## 5. Descriptive diagnostics, disclosures, and inference limits

B1/B2 are enabled for all 30 runs through frozen procedural records. They count each actually inserted n-step window once, not repeated replay uses. U=1[A≠g] uses the online network's actual selected greedy action at collection, not the target/final/update-time network. L includes subsequent actions only; ties can produce mismatch with another equal-valued action. Death comes from info.died, not negative reward or termination flags. Short flushed windows use actual h; budget stopping adds no flush. (Protocol §11.1–11.2; Analysis §9.1.)

Diagnostics retain counts, denominators, and death/mismatch/greedy-start co-occurrence, with zero denominators represented by null. Overlapping death windows are not independent deaths. The known discounted −10 death component is not the entire return/TD target, nor causal impact. Separate auxiliary sealing/aggregation does not enter core H1/H2, selection, stopping, or reruns; no added confirmatory tests or CIs. (Protocol §11.3–11.6; Analysis §9.)

The frozen disclosure states that disposable rehearsals actually started seed100/res4/n1 several times, each at most approximately 75 seconds; one reached a first prereg_val early-model validation. Outputs are excluded from formal runs, never reused, and not used for any selection. This is not a claim of prior sealed-test access, nor proof of a complete historical access record. (Protocol §7.4.)

Report both interval methods when they disagree, using method_sensitive_zero and the specified magnitude checks; describe method sensitivity without substituting bootstrap for formal t decisions. The 95% bootstrap versus 97.5% t magnitude comparison also differs in coverage level. (Analysis §6.)

The study is limited to one map, 5 training seeds, privileged input, last@300k, equal transitions with unequal compute, GPU-selected secondary best, and possible numerical/GPU nondeterminism. It cannot establish universal architecture/depth rankings, general n=1 superiority, multi-map generalization, equivalence to heuristics, or an off-policy/death mechanism. B1/B2 co-occurrence is descriptive; explanations developed after seeing data are post hoc and require new interventions. Literature reading levels remain full-text/abstract/secondary as supplied, with human source checks distinct from AI static review. (Protocol §§1, 8, 9, 11.)

Future capacity, exploration, target-correction, representation, parameter-matching, budget-scaling, and new-seed studies require separate registration/new holdouts. The 20-seed planning starting point is not a power guarantee and does not change this round. (Protocol §12.)
