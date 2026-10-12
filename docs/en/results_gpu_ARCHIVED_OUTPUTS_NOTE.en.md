> This is a reading copy. The Chinese original (`results_gpu/ARCHIVED_OUTPUTS_NOTE.md`, SHA-256 `13baa6c7f5371f19b891800763226900e20647208a6975433ce75a459baed5fd`, as of commit aa254a3) governs; in case of any difference the original governs.

# Note on archived outputs: `check_acceptance_output.txt` and `pytest_output.txt`

These two files are **historical raw outputs, deliberately kept as they were and not modified** (they are non-`.md` data files under `results_gpu/`, and the convention of this repository is not to change committed result data). Read them in the light of this note, and do not take the failures in them as the state of the current code.

| File | Content | Corresponding commit / code state |
|---|---|---|
| `check_acceptance_output.txt` | `M1  MUST  FAIL  1 error in 3.21s` (all other MUST items PASS) | Produced during the local Windows long run and committed with `cb224cc` (2026-10-08); it corresponds to the code **before** that commit, before the Windows fixes were made |
| `pytest_output.txt` | `1 failed, 45 passed`; the failing item is `tests/test_learning.py::test_stale_lock_is_taken_over` | Same as above |

## Why they failed (both are Windows compatibility problems, not problems of the algorithm or the results)

1. **M1 FAIL (`1 error`)**: when the acceptance script called pytest it replaced the subprocess environment with a dictionary containing only `PYTHONPATH` and a Linux-style `PATH`; on Windows variables such as `SystemRoot` were missing and the import failed.
2. **`test_stale_lock_is_taken_over`**: `run_experiments.py` used `/proc/<pid>` at the time to decide whether the process holding a lock was alive; Windows has no `/proc`, so it conservatively assumed the lock holder was still alive and did not take over the stale lock.

## Which commit fixed them

- Commit **`4bfe5cd`** (2026-10-09, "Windows-safe scripts: portable pid check, inherit env in subprocesses, UTF-8 I/O"): added a portable `pid_alive()` (POSIX `os.kill(pid, 0)` / Windows `OpenProcess`) and made the subprocesses of `check_acceptance.py` / `make_report.py` inherit `os.environ`. This fixed both points above; `test_stale_lock_is_taken_over` has passed since.
- The owner checked out commit **`8dfa071`** on local Windows 11 and measured: all 47 `pytest` items pass (including `stale_lock` and `pid_alive_is_portable`), and `check_acceptance.py --run-tests` gives **M1 PASS** for both `results/` and `results_gpu/`, with all MUSTs passing. This record is in the deviation record of `docs/PLAN.md` (the entry "Windows verification (supplementary)", committed with commit `b5f5288`).

## Which record is authoritative now

- **Neither of these two `.txt` files is authoritative**. They only prove that "it did fail on Windows before the fix, and why".
- Whether the current code passes acceptance is determined by the result of **re-running on the commit being cited**: `bash python/scripts/acceptance.sh --quick`; `cd python && PYTHONPATH=. python scripts/check_acceptance.py --run-tests` (for `results_gpu/` additionally set the environment variable `PACMAN_RESULTS_DIR=<repo>/results_gpu`); and the full `pytest` on Windows. The deviation record in `docs/PLAN.md` lists the Windows re-tests that have been recorded in the documents.
- For the narrative addendum see "Addendum (cloud, 2026-10-09)" at the beginning of `LOCAL_RUN_REPORT.md`. The result data (`runs/`, `eval/`, etc.) are not affected by these two Windows compatibility problems.
