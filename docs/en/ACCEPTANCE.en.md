> This is a reading copy. The Chinese original (`docs/ACCEPTANCE.md`, SHA-256 `ad4dcc61995f27c614c36cff3b7827c133019fcc7066669b19b7f1bb55011d5f`, as of commit aa254a3) governs; in case of any difference the original governs.

# Acceptance manual

Corresponds to sections 7 and 8 of `docs/PLAN.md`. The thresholds are already fixed in the plan; this document only describes **how to verify**.

## A. Environment setup
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r python/requirements.txt          # numpy, torch (CPU is enough), matplotlib, pytest
```
> In an environment without direct access to pytorch.org, simply install `torch` from PyPI (it is large and includes CUDA dependencies, but the CPU works).

## B. Automatic acceptance

| Step | Command | Expectation |
|---|---|---|
| 1. Unit/integration tests (M1) | `cd python && PYTHONPATH=. python -m pytest tests -q` (PowerShell: `cd python; $env:PYTHONPATH='.'; python -m pytest tests -q`; identical to what `acceptance.sh` does internally; it must be run inside `python/` with `PYTHONPATH` set — running `python -m pytest python/tests` directly from the repository root fails because `pacman_rl` cannot be found) | All green |
| 2. Quick smoke test (M2) | `bash python/scripts/acceptance.sh --quick` | About 1–10 minutes (depending on the machine), ending with `QUICK ACCEPTANCE PASSED`; the JSON of evaluating the same checkpoint twice must be byte-for-byte identical, otherwise the script fails with a non-zero exit code |
| 3. Judge the committed full results | `bash python/scripts/acceptance.sh` | Prints `PASS / FAIL / REPORTED / MISSING` item by item; exit code 1 if any MUST is not satisfied |
| 4. Regenerate the report | `python python/scripts/make_report.py` | Rewrites `docs/RESULTS.md` and `results/figures/*.png`; the text part should be unchanged (the M1 row no longer contains test durations; test counts vary with the environment, e.g. a machine without a GPU skips 1 item). The bytes of the PNG figures vary with the matplotlib version, **byte-for-byte identity is not required** |
| 5. (Optional) Full reproduction | `bash python/scripts/run_all.sh` | Several hours of CPU; can resume from a breakpoint |
| 6. (Optional) Re-run the Java ground truth | `bash python/scripts/run_java_legacy.sh 150` | Requires a JDK; runs in a temporary directory and does not modify the repository |

Main points covered by the tests:
- The Python map is **cell-for-cell identical** to the maps in the three `Game.java` files; 378 cells, 377 edible pellets.
- Ghosts never enter walls and never turn back; the chase probability agrees with the Java rules (statistical test); collision, winning, truncation, same-seed determinism.
- The distribution of the `legacy` re-implementation and that obtained by **actually running the original Java code** show **no significant difference detected** (z tests + KS test on score/steps/death rate; the seeds are the dedicated 20000–20299). This is only a distribution-level test; it does not prove identical step-by-step transitions (differences such as terminal-state timing are in section 4 of `docs/PLAN.md`).
- n-step returns, termination/truncation handling, ResNet initialised as the identity, receptive field, features finite and bounded, checkpoint round trip consistent.

## C. Manual review checklist

1. **Watch the behaviour**: the GIFs under `results/replays/` (random / legacy / final agent). The final agent should avoid ghosts that come close, not jitter in place, and clear most of the pellets.
2. **Check number provenance**: pick any episode in `results/runs/<run>/test_standard.json` and check it against the summary in `docs/RESULTS.md`.
3. **Check for leakage**:
   - In `python/pacman_rl/evaluate.py`, the test seeds `10000–10299`, the validation seeds `5000–5049` and the training seeds (≥ 1,000,000) are pairwise disjoint (the tests contain assertions);
   - `train()` in `dqn.py` uses only the validation set to choose checkpoints; the test set is used only by `cli eval-model --split test` after training ends.
4. **Check the old code**: `git diff 1e9da5c -- ReinforcementLearning HumanPlayGame DijkstraPathFinding Pacman.java PacmanRL.java PacmanDijkstra.java Images data/QTable.txt ':(exclude,glob)**/.DS_Store'` is empty (exactly the same path set as M7 of `check_acceptance.py`; `.DS_Store` is a macOS junk file, deleted at the owner's request, and excluded from the comparison). Note: the older version of this document used the wildcard `'*.java'`, which also matches the newly added test fixture `python/scripts/java_harness/Harness.java` (16 lines, copied by `run_java_legacy.sh` into a temporary directory to run the original Java; it is a new file, not a modification of the old Java) and therefore showed a non-empty difference; the original Java sources, images and Q-table have not changed at all since the baseline.
5. **Read the limitations**: the end of `docs/RESULTS.md` and the "deviation record" in section 9 of `PLAN.md`; confirm that no failure was hidden and no threshold was changed after the fact.

## D. Acceptance conclusion template
```
Date:           Reviewer:
M1 [ ]  M2 [ ]  M3 [ ]  M4 [ ]  M5 [ ]  M6 [ ]  M7 [ ]
S1 [ ]  S2 [ ]  S3 [ ]  S4 [ ]   (items not met are explained in RESULTS.md: yes / no)
Manual review C1–C5 [ ]
Conclusion: pass / conditional pass / fail
