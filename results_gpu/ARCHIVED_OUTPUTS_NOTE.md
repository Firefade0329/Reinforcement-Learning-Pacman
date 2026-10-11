# 归档输出说明:`check_acceptance_output.txt` 与 `pytest_output.txt`

这两个文件是**历史原始输出,有意保持原样、没有修改**(它们是 `results_gpu/` 下的非 `.md` 数据文件,本仓库的约定是不改动已提交的结果数据)。读它们时请按本说明理解,不要把里面的失败当作当前代码的状态。

| 文件 | 内容 | 对应的提交 / 代码状态 |
|---|---|---|
| `check_acceptance_output.txt` | `M1  MUST  FAIL  1 error in 3.21s`(其余 MUST 项均 PASS) | 本地 Windows 长跑时产生,随提交 `cb224cc`(2026-10-08)入库;对应的是该提交**之前**、尚未做 Windows 修复的代码 |
| `pytest_output.txt` | `1 failed, 45 passed`;失败项 `tests/test_learning.py::test_stale_lock_is_taken_over` | 同上 |

## 为什么失败(两处都是 Windows 兼容问题,不是算法或结果问题)

1. **M1 FAIL(`1 error`)**:验收脚本调用 pytest 时把子进程环境换成只含 `PYTHONPATH` 与 Linux 风格 `PATH` 的字典,Windows 上缺少 `SystemRoot` 等变量,导入失败。
2. **`test_stale_lock_is_taken_over`**:`run_experiments.py` 当时用 `/proc/<pid>` 判断持锁进程是否存活,Windows 没有 `/proc`,于是保守地认为持锁进程还活着,不接管残留锁。

## 由哪个提交修复

- 提交 **`4bfe5cd`**(2026-10-09,"Windows-safe scripts: portable pid check, inherit env in subprocesses, UTF-8 I/O"):新增可移植的 `pid_alive()`(POSIX `os.kill(pid, 0)` / Windows `OpenProcess`),并让 `check_acceptance.py` / `make_report.py` 的子进程继承 `os.environ`。这同时修复了上面两处;`test_stale_lock_is_taken_over` 自此通过。
- 所有者在本地 Windows 11 上检出提交 **`8dfa071`** 实测:`pytest` 47 项全过(含 `stale_lock`、`pid_alive_is_portable`),`check_acceptance.py --run-tests` 对 `results/` 与 `results_gpu/` 均 **M1 PASS**、全部 MUST 通过。该记录写在 `docs/PLAN.md` 的偏差记录(条目"Windows 验证(补充)",由提交 `b5f5288` 入库)。

## 现在以哪份记录为准

- **不以这两个 `.txt` 为准**。它们只证明"修复之前在 Windows 上确实失败过,以及失败的原因"。
- 当前代码是否通过验收,以**对被引用的那个提交重新运行**的结果为准:`bash python/scripts/acceptance.sh --quick`;`cd python && PYTHONPATH=. python scripts/check_acceptance.py --run-tests`(对 `results_gpu/` 再加环境变量 `PACMAN_RESULTS_DIR=<repo>/results_gpu`);以及 Windows 上的完整 `pytest`。`docs/PLAN.md` 的偏差记录列出已记入文档的 Windows 复测。
- 叙述性的补注见 `LOCAL_RUN_REPORT.md` 开头的"补注(云端,2026-10-09)"。成绩数据(`runs/`、`eval/` 等)不受这两处 Windows 兼容问题影响。
