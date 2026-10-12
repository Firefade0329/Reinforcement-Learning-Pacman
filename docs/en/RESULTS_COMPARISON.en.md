> This is a reading copy. The Chinese original (`docs/RESULTS_COMPARISON.md`, SHA-256 `fe456d83765143befec71a27d3c8fcf3cb771e49eb293ffd3b799146773ee411`, as of commit aa254a3) governs; in case of any difference the original governs.
>
> Unit note: "wan" (万) means ten thousand; "N wan steps" is the original's "N 万步".

# Comparison of the two experiment sets (auto-generated; do not edit by hand)

- **A = 12 wan steps · CPU (cloud)** (`results/`), **B = 30 wan steps · GPU (local)** (`results_gpu/`). The same 300 test seeds, standard scenario, mean score (maximum 377); for the RL rows, the per-episode average over 3 training seeds.
- The two experiment sets differ in hardware, training steps and parallelism; GPU training is reproducible statistically, not bit for bit, and **evaluation also depends on the device**: evaluating the same checkpoint on GPU and on CPU gives different per-episode results (**the difference in mean score has been independently reproduced**: the same checkpoint `results_gpu/runs/res4_s0/best.pt` scored 142.8 when evaluated on the GPU, the local executor re-evaluated it on the CPU and got 144.6, and the cloud CPU re-evaluation also gave 144.6, with 22/300 episodes differing episode by episode; the range "about 7% to 29%" for the proportion of episodes that differ is the auditors' observation on different checkpoints, with the difference in means within two points; the cloud has no GPU, and the GPU-side numbers are taken from the committed evaluation files). Therefore the comparison between the two sets can only serve as directional evidence.

## 1. Each agent: short training vs long training
| Agent | A: 12 wan steps · CPU (cloud) | B: 30 wan steps · GPU (local) | B − A (paired, per episode) | Per seed A | Per seed B |
|---|---|---|---|---|---|
| random (non-learning, same episodes) | 7.5 [6.9, 8.1] | 7.5 [6.9, 8.1] | — | — | — |
| legacy (Java re-implementation) (non-learning, same episodes) | 153.4 [141.7, 165.4] | 153.4 [141.7, 165.4] | — | — | — |
| strong hand-written heuristic (non-learning, same episodes) | 268.2 [254.9, 281.0] | 268.2 [254.9, 281.0] | — | — | — |
| MLP-DQN | 235.7 [226.5, 244.9] | 263.3 [253.7, 272.9] | +27.7 [+17.9, +37.4] | 246 / 241 / 220 | 266 / 253 / 271 |
| CNN-2 | 80.3 [76.6, 84.0] | 125.5 [120.6, 130.3] | +45.2 [+39.5, +50.9] | 98 / 67 / 76 | 110 / 126 / 141 |
| ResNet-2 | 139.5 [134.2, 144.6] | 159.7 [154.1, 165.2] | +20.2 [+12.9, +27.6] | 134 / 143 / 141 | 176 / 167 / 136 |
| ResNet-4 | 127.8 [122.5, 133.1] | 160.9 [155.5, 166.4] | +33.1 [+25.8, +40.4] | 153 / 102 / 128 | 143 / 149 / 191 |
| ResNet-8 | 102.8 [98.2, 107.6] | 127.9 [122.0, 133.7] | +25.1 [+18.0, +32.0] | 75 / 89 / 144 | 151 / 129 / 104 |

## 2. Ablation: variant − full recipe (paired differences within each set)
| Set | Baseline | Variant | Score difference [95% CI] | Number of seeds in which the variant is higher |
|---|---|---|---|---|
| 12 wan steps · CPU (cloud) | ResNet-4 | without Double | +8.0 [+0.5, +15.5] | 2/3 |
| 12 wan steps · CPU (cloud) | ResNet-4 | without Dueling | +26.7 [+19.4, +34.1] | 3/3 |
| 12 wan steps · CPU (cloud) | ResNet-4 | n-step = 1 | +62.7 [+54.8, +70.6] | 3/3 |
| 12 wan steps · CPU (cloud) | ResNet-4 | raw grid (no distance fields) | -32.4 [-38.7, -26.2] | 0/3 |
| 12 wan steps · CPU (cloud) | MLP-DQN | without Double | +9.0 [-1.1, +19.2] | 2/3 |
| 12 wan steps · CPU (cloud) | MLP-DQN | without Dueling | +19.1 [+10.0, +27.9] | 3/3 |
| 12 wan steps · CPU (cloud) | MLP-DQN | n-step = 1 | +11.6 [+1.7, +21.6] | 1/3 |
| 30 wan steps · GPU (local) | ResNet-4 | without Double | -17.5 [-25.1, -9.9] | 1/3 |
| 30 wan steps · GPU (local) | ResNet-4 | without Dueling | -10.5 [-18.1, -2.9] | 1/3 |
| 30 wan steps · GPU (local) | ResNet-4 | n-step = 1 | +72.5 [+64.3, +80.7] | 3/3 |
| 30 wan steps · GPU (local) | ResNet-4 | raw grid (no distance fields) | -37.5 [-44.7, -30.3] | 0/3 |
| 30 wan steps · GPU (local) | MLP-DQN | without Double | +5.0 [-4.3, +14.3] | 2/3 |
| 30 wan steps · GPU (local) | MLP-DQN | without Dueling | -10.3 [-20.0, -1.0] | 0/3 |
| 30 wan steps · GPU (local) | MLP-DQN | n-step = 1 | -25.8 [-36.9, -14.7] | 0/3 |

## 3. Interpretation (qualitative; numbers are in the tables above)
- **Longer training improves all networks**: the MLP is still clearly higher than all convolutional networks; the improvement of the convolutional networks is limited and not monotone in depth. The ranking within the convolutional networks is **not stable**: the order of ResNet-2 and ResNet-4 swapped between the two runs, and the gap lies within the fluctuation between training seeds.
- **The improvement from n-step = 1 for ResNet-4 appeared in two mutually independent runs** (same code, same seeds, same hyperparameters; the second was run after seeing the conclusion of the first) and is consistent seed by seed. It is the single change that is most effective for convolutional networks so far; it greatly narrows their gap to the MLP, but they remain below the MLP. For the MLP there is no stable conclusion (the sign differs between the two sets of experiments) and it should not be generalised. This suggests that the default recipe (n-step = 3) may be suboptimal for convolutional networks, but **so far only the single depth point ResNet-4 has n-step = 1 data**, so it cannot show the ranking of the depths after the recipe is corrected; "no benefit from depth" can therefore only be understood as "an empirical fact under this recipe", and whether it is attributable to the recipe or to depth has to wait for the full depth × n-step matrix.
- **The effects of removing Double / removing Dueling were not reproduced**: in the short-training set they favour "removing" relative to the full recipe, and in the long-training set the sign is opposite. This indicates that the influence of these two components is smaller than the training fluctuation, or depends on the training length, and **no choice should be made on this basis**; the statement in the cloud report that "removing Dueling gives an improvement" can only count as a single observation.
- **The distance fields** helped ResNet-4 in both runs, but each cell has only 3 training seeds and the gap is close to the fluctuation between seeds, so caution is needed.
- **The best conclusion still has to wait for the second pass of experiments**: re-run all convolutional architectures (CNN-2 / ResNet-2 / ResNet-4 / ResNet-8) with n-step = 1, in order to answer "does depth help after the recipe is corrected". At present only the single depth point ResNet-4 has n-step = 1 data.
- **The gap to the strong hand-written heuristic** narrows as MLP training gets longer; whether it is crossed depends on the number of steps and on the seeds; see the two columns of section 1.
- For engineering events (interrupted-and-resumed training, memory scheduling, etc.) see the respective `LOCAL_RUN_REPORT.md` and the deviation record in `docs/PLAN.md`.
