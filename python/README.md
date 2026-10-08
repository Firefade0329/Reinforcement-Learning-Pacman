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
