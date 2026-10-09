# Pacman RL — Python / deep-RL edition

Faithful Python port of the Java game plus a ladder of agents from random to a fully-convolutional
residual DQN, evaluated under one protocol.  Plan and gates: [`../docs/PLAN.md`](../docs/PLAN.md),
acceptance manual: [`../docs/ACCEPTANCE.md`](../docs/ACCEPTANCE.md), generated results:
[`../docs/RESULTS.md`](../docs/RESULTS.md).  The original Java code in the repo root is untouched.

```bash
pip install -r requirements.txt
python -m pytest tests -q                       # env fidelity, replay maths, models, reproducibility
bash scripts/acceptance.sh --quick              # ~5-10 min smoke run
bash scripts/run_all.sh                         # full reproduction (hours on 4 CPU cores)
```

Run commands from this directory (`PYTHONPATH=.` is set by the scripts):

```bash
python -m pacman_rl.cli baseline --agent legacy --split val            # random|greedy-bfs|legacy|safe-heuristic
python -m pacman_rl.cli tabular --episodes 3000 --seed 0
python -m pacman_rl.cli train --name my_run --arch res4 --seed 0       # mlp|cnn2|res2|res4|res8
python -m pacman_rl.cli eval-model --ckpt ../results/runs/my_run/best.pt --split val --scenarios standard hard
python -m pacman_rl.cli replay --agent ../results/runs/my_run/best.pt --seed 10003   # -> results/replays/*.gif
```

| module | role |
|---|---|
| `maps.py` | the Java map cell-for-cell + neighbour table + all-pairs BFS distances |
| `env.py` | `PacmanEnv` (reset/step), rules, observations (raw planes, BFS distance fields) |
| `baselines.py` | random, greedy-BFS, exact replica of the Java agent, strong safe-path heuristic |
| `features.py`, `tabular.py` | 64-state design from `QLearning.java`'s comments, standard Q-learning |
| `models.py` | MLP, CNN-2, ResNet-N: fully convolutional, Q read out at Pacman's cell, dueling |
| `replay.py`, `dqn.py` | n-step replay, Double DQN trainer with vectorised envs |
| `evaluate.py` | fixed seed splits, per-episode records, bootstrap / paired CIs |
| `render.py` | GIF replays |

Seeds: validation 5000–5049 (checkpoint selection only), test 10000–10299 (final numbers only),
training seeds ≥ 1,000,000.

## Training on a GPU (e.g. a laptop RTX A1000)

The conv nets are tiny, so a mid-range GPU helps mostly by removing the CPU compute bottleneck
(expect roughly 5-15x per gradient update; measure it with `bench`).  The game simulation stays
on the CPU, and the MLP gains nothing from a GPU.

```bash
# 1. install a CUDA build of PyTorch (pick the command for your CUDA version at https://pytorch.org)
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# 2. how fast is it here?  (ms per gradient update, per architecture)
python -m pacman_rl.cli bench --device auto
python -m pacman_rl.cli bench --device cpu            # compare

# 3. a single run on the GPU
python -m pacman_rl.cli train --name res4_gpu --arch res4 --device cuda --total_env_steps 300000

# 4. the whole matrix, longer, in a separate results dir (results_gpu/)
bash scripts/run_gpu_longrun.sh                       # PACMAN_STEPS / PACMAN_WORKERS / PACMAN_DEVICE override
```

Notes
- `--device` is `cpu` (default, behaviour unchanged), `cuda`, or `auto`.  Checkpoints are
  device-agnostic: a GPU-trained `best.pt` evaluates on CPU or GPU.
- GPU results are statistically, not bit-for-bit, reproducible (CUDA kernels are not
  deterministic); the same checkpoint evaluated twice on one device is still identical.
- GPU runs write to their own results directory; do not mix them into the CPU matrix in `results/`.
- Several runs share one GPU fine; the limit is usually the number of CPU cores stepping the
  environments, so start with `PACMAN_WORKERS=3`.
- **Before committing from another machine**, set the repo-local git identity so your global
  e-mail is not attached to commits:
  `git config user.name "Firefade0329" && git config user.email "114788148+Firefade0329@users.noreply.github.com"`

## Second pass: n-step = 1 for every conv architecture (planned, not yet run)

The ablations suggest the default recipe (n-step = 3) hurts the conv nets: with ResNet-4, n-step = 1 scored
clearly higher in two independent runs (see `docs/RESULTS_COMPARISON.md`).  To test whether depth helps once
the recipe is fixed, re-run the whole matrix with n-step = 1, into a separate results directory:

```bash
PACMAN_TRAIN_EXTRA="--n_step 1" PACMAN_SKIP_ALGO=1 PACMAN_RESULTS_DIR="$PWD/results_gpu_nstep1" \
  bash python/scripts/run_gpu_longrun.sh
```

`PACMAN_TRAIN_EXTRA` is appended to every training command, `PACMAN_SKIP_ALGO=1` skips the ablation stage.
Training is resumable: re-run the same command after an interruption.  Generate the report with
`PACMAN_RESULTS_DIR=... python scripts/make_report.py` and compare with `python scripts/make_comparison.py <dir_a> <dir_b>`.

## Resuming an interrupted run

Training writes `resume.pt` / `resume_replay.npz` at every evaluation boundary and picks them up when the
same command is run again.  A resumed run is **successful but not bit-equivalent** to an uninterrupted one:
environment states and the pending n-step queues are not saved (at most 2 transitions per environment are
lost) and new episodes use unused seeds, so the effect on the training distribution is not quantified.
On resume the log is truncated to the checkpoint and a `{"type": "resume", ...}` row marks the point; logs of
runs resumed with the older code (cloud `res4_s0`, local `mlp_s0/s1/s2`) can contain duplicated or
backward-going rows (weights and `summary.json` are unaffected).  Evaluation also depends on the device: the
same checkpoint evaluated on GPU and on CPU gives different per-episode results.
