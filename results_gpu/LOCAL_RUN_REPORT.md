# 本地 GPU 长跑报告(第一遍,默认配方 n 步 = 3)

> 本文件由本地 Claude Code 如实撰写。表中成绩来自 `RESULTS.md`(由 `make_report.py` 生成)和各运行目录里的 JSON。
> 日志里的本机路径和用户名已替换为占位符 `<repo>` / `<local>` / `<home>`,除此之外未改动。

## 1. 机器信息

| 项 | 值 |
|---|---|
| GPU | NVIDIA RTX A1000 6GB Laptop GPU(WDDM) |
| 驱动 / CUDA | 驱动 596.58,`nvidia-smi` 显示支持 CUDA 13.2 |
| PyTorch | 2.14.1+cu130,`torch.cuda.is_available()` = True |
| Python | 3.12.10(虚拟环境) |
| CPU | 13th Gen Intel Core i7-13700H,14 核 / 20 逻辑核 |
| 内存 | 15.7 GB |
| 系统 | Windows 11 |
| 运行方式 | Git Bash 执行 `run_gpu_longrun.sh`;后期因调整并行拆成了单独的 python 进程(见第 4、7 节) |

## 2. 速度基准(batch 32,每次梯度更新的毫秒数)

| 架构 | GPU | CPU | 加速比 |
|---|---|---|---|
| mlp | 1.6 | 0.9 | 0.56×(MLP 本来就留在 CPU 上训练) |
| cnn2 | 1.7 | 2.9 | 1.7× |
| res2 | 3.7 | 7.0 | 1.9× |
| res4 | 5.3 | 11.2 | 2.11× |
| res8 | 8.3 | 21.4 | 2.58× |

- res4 / res8 都 ≥ 2 倍,按规则继续跑;res4 只是勉强过线。
- 远低于 README 预期的 5–15×。我另测了 res4 在不同 batch 下的整步耗时:batch 32 约 2.7×,batch 256 约 3.9×,batch 1024 约 4.1×;4096×4096 fp32 矩阵乘约 3.9 TFLOPS,说明 GPU 本身正常,加速有限是因为网络很小(宽度 16)、batch 小、本机 CPU 较强。
- 显卡无降频(热降频、功耗降频均为 Not Active)。任务管理器默认显示 3D 引擎,看 CUDA 负载要切到 Compute / Cuda;`nvidia-smi` 显示训练时利用率约 75%。

## 3. 配置

- 步数:每个运行 300000 环境步;`eval_every` = 20000;设备:卷积网络用 `cuda`,MLP 用 CPU。
- 并行数:**计划 3,实际 2**(见第 7 节);消融阶段后期进一步按内存情况调整,最多同时 2 个卷积训练进程。
- 总耗时:约 12 小时 40 分钟(含两次中断重启)。
- 共 39 个运行:baselines + tabular ×3、depth 矩阵(mlp / cnn2 / res2 / res4 / res8 各 3 个种子)、MLP 消融 9 个、ResNet-4 消融 9 个、ResNet-4 原始网格对照 3 个。

## 4. 各运行是否完成

**全部 39 个运行都完成**,每个都有 `test_standard.json`,没有 `FAILED`,没有 stderr 输出,没有残留 `.lock`。

**被中断后续训完成的运行**(均从 `resume.pt` 续训,续训日志里有 `[resume] continuing from ...`):

| 运行 | 中断时步数 | 原因 |
|---|---|---|
| mlp_s0、mlp_s1、mlp_s2 | 约 4 万–6 万步 | 发现可用内存只剩约 5 GB,卷积阶段需要 7–9 GB,我主动停下主脚本,把并行数从 3 降到 2 后重跑同一条命令 |
| res4-nodouble_s0、res4-nodouble_s1 | 18 万步 | 两个卷积训练加一个 MLP 训练同时跑时,系统提交内存只剩约 1 GB 余量,我主动停止并降为 1 个并行再续训 |

续训时环境会换新的训练局(使用未用过的种子),回放缓冲区、网络、优化器和随机数状态都从存档恢复,所以这 5 个运行与不中断的结果在统计上等价,但不是逐位相同。

## 5. 测试集成绩(标准场景,300 局,平均得分,满分 377)

| 智能体 | 平均得分 [95% CI] | 逐种子 | 死亡率 |
|---|---|---|---|
| random | 7.5 | | 100% |
| greedy-BFS | 60.3 | | 100% |
| legacy(Java 复刻) | 153.4 [141.7, 165.4] | | 95% |
| 强手写启发式 | 268.2 [254.9, 281.0] | | 81% |
| 表格 Q(64 状态) | 80.3 | | 100% |
| MLP-DQN | 263.3 | 266.3 / 252.6 / 271.2 | 70% |
| CNN-2 | 125.5 | 109.8 / 125.8 / 140.8 | 100% |
| ResNet-2 | 159.7 | 175.9 / 166.7 / 136.4 | 98% |
| ResNet-4 | 160.9 | 142.8 / 149.0 / 191.0 | 100% |
| ResNet-8 | 127.9 | 150.8 / 129.3 / 103.7 | 100% |

与参考数字对比:random 7.5、legacy 153、强手写启发式 268 完全一致,说明环境和评估没有问题。MLP 三个种子 266 / 253 / 271,高于参考的 246 / 241 / 220(训练步数更多,30 万对 12 万)。没有出现全部接近随机的异常。

**消融与对照(标准场景测试得分均值 ± 种子间标准差)**

| 配置 | 均值 ± std | 逐种子 |
|---|---|---|
| ResNet-4 默认(n 步 = 3) | 160.9 ± 26.3 | 142.8 / 149.0 / 191.0 |
| ResNet-4 关闭 Double | 143.4 ± 12.7 | 157.8 / 138.5 / 133.9 |
| ResNet-4 关闭 Dueling | 150.4 ± 18.8 | 168.6 / 131.0 / 151.7 |
| **ResNet-4 n 步 = 1** | **233.4 ± 14.7** | 241.7 / 216.5 / 242.1 |
| ResNet-4 原始网格(无距离场) | 123.4 ± 14.9 | 139.2 / 109.6 / 121.4 |
| MLP 关闭 Double | 268.3 ± 1.6 | 267.1 / 270.1 / 267.8 |
| MLP 关闭 Dueling | 253.1 ± 5.9 | 254.5 / 246.5 / 258.1 |
| MLP n 步 = 1 | 237.6 ± 16.7 | 249.3 / 244.9 / 218.5 |

**观察(仅陈述数据,未做统计检验之外的推断)**
1. 30 万步下,所有卷积网络(125–161)都明显低于 MLP(263)和强手写启发式(268),只有 ResNet-2 / 4 略高于 legacy(153)。
2. 深度不单调:CNN-2 125.5 < ResNet-2 159.7 ≈ ResNet-4 160.9 > ResNet-8 127.9(验收脚本的 S4 同样判为 "monotone: False")。种子间波动很大(ResNet-8 的三个种子相差 47 分),单个种子不能下结论。
3. **ResNet-4 把 n 步从 3 改成 1,三个种子分别从 142.8 / 149.0 / 191.0 变为 241.7 / 216.5 / 242.1,逐个种子都更高,均值 +72**,接近 MLP 水平。这与云端的发现一致。对 MLP 则相反(n 步 = 1 为 237.6,低于默认 263.3)。
4. 原始网格(无距离场)ResNet-4 为 123.4,低于带距离场的 160.9,方向上距离场有帮助,但差距在种子波动范围内。

困难场景(幽灵 70% 追击,训练中未见)下各智能体得分都较低:强手写启发式 85.9,MLP 83.1,卷积网络 57–69,legacy 42.2,表格 Q 35.4。

## 6. 验收脚本结果(`check_acceptance.py`)

| 项 | 结果 | 说明 |
|---|---|---|
| M1 | **FAIL(脚本给出)** | 见下面的单独说明 |
| M3 | PASS | 基线和表格 Q 齐全 |
| M4 | PASS | 按验证集选出的最终智能体是 **MLP**(不是卷积网络);相对 legacy 得分差 +110.0 [+95.8, +123.9],死亡率更低 |
| M5 | PASS | 相对表格 Q 得分差 +183.0 [+173.4, +192.7] |
| M6 | PASS | 33 个运行完成,每格 ≥ 3 个种子 |
| M7 | PASS | Java 源码、图片、Q 表无改动 |
| S1 | PASS | 最终智能体相对强手写启发式 −4.8 [−19.7, +10.5],相对 −1.8%(门槛 ≥ −3%) |
| S2 | PASS | ResNet-2 对 CNN-2:+34.2 [+26.7, +41.6] |
| S3 | PASS | 困难场景相对 legacy:+40.9 [+35.7, +46.2] |
| S4 | REPORTED | 各深度得分 cnn2 125.5、res2 159.7、res4 160.9、res8 127.9,不单调 |

MUST 里 1 项未通过(M1)。**M1 的真实情况有两层:**
1. 验收脚本自己调用 pytest 时把环境变量替换成只含 `PYTHONPATH` 和 Linux 风格 `PATH` 的字典,在 Windows 上缺少 `SystemRoot` 等变量,导入失败,于是报 "1 error";这是脚本不兼容 Windows,不是测试结果。
2. 直接运行 `python -m pytest tests -q`(输出见 `pytest_output.txt`):**45 项通过,1 项失败**,失败的是 `test_stale_lock_is_taken_over`。原因:`run_experiments.py` 用 `/proc/<pid>` 判断持锁进程是否存活,Windows 没有 `/proc`,于是保守地认为"还活着",不会自动接管残留锁。训练本身不受影响,残留 `.lock` 需要手动删除。我没有改测试或这段代码。

未运行 `acceptance.sh --quick`(M2)。

## 7. 遇到的问题和处理

1. **测试失败(Windows 兼容)**:首次 pytest 为 44 过、2 败。
   - `test_training_resumes_after_interruption`:续训时 `np.load` 打开 `resume_replay.npz` 后一直没关闭,Windows 不允许覆盖已打开的文件,下一次存档会报 `PermissionError`。**已修复**:改为 `with np.load(...) as data:`,共 3 行,单独提交(`dqn.py`),修复后该项通过。**注意:云端新历史里的 `dqn.py` 没有这个修复(`np.load` 仍未关闭);本分支只含结果目录,不含此补丁**。
   - `test_stale_lock_is_taken_over`:未修,见第 6 节。
2. **内存紧张**:机器 15.7 GB,Claude 桌面应用等常驻进程占了约 3.6 GB。把并行数从 3 降到 2;消融阶段曾尝试 `algo` 与 `algo_mlp` 并行,出现三个训练进程同时跑的组合时可用内存降到约 0.7 GB、系统提交内存余量约 1 GB,于是停掉 `algo`,降为 1 个并行续训;`algo_mlp` 结束后再补开第二个 `algo` 进程。此后没有运行被杀。
3. **主脚本被拆开**:为让消融并行,我只终止了主脚本的 bash 外壳(`algo_mlp` 的 python 进程继续跑),`algo` 阶段以单独的 `run_experiments.py algo` 进程启动(两个进程靠运行锁分工)。因此 `make_report.py` 和 `check_acceptance.py` 没有由主脚本自动执行,而是训练全部结束后手动运行。
4. **残留 `.lock`**:Windows 上不会自动接管,每次中断后确认没有残留 python 进程、锁的持有者 pid 已不存在,才手动删除了 5 个 `.lock`(mlp_s0 / s1 / s2,res4-nodouble_s0 / s1)。
5. **`make_report.py` 在 Windows 上报编码错误**:默认 cp1252 无法写中文。不改代码,设置环境变量 `PYTHONUTF8=1` 后正常。
6. **`.gitignore` 只覆盖 `results/runs/...`,不覆盖 `results_gpu/`**:训练结束时已自动清掉 `resume.pt`、`resume_replay.npz`(最终目录里没有),所以没有大文件;训练期间用仓库本地的 `.git/info/exclude` 排除。
7. **`RESULTS.md` 的细节**:图链接指向 `../results/figures/...`(生成脚本的默认值),实际图片在本目录 `figures/`;第 7 节"验收门槛判定"为空。未手改这份自动生成的报告,验收输出见 `check_acceptance_output.txt`。
8. **日志合并**:`longrun_attempt1.log`、`longrun_algo_attempt1.log` 是被中断前的首次日志;`longrun.log`、`longrun_algo.log`、`longrun_algo2.log` 是后续日志。

## 8. 未完成 / 后续

- **第二遍(所有卷积架构 n 步 = 1,写到 `results_gpu_nstep1/`)尚未运行**,等用户安排时间后再跑。
- 云端新历史里新增了 `PACMAN_TRAIN_EXTRA` / `PACMAN_SKIP_ALGO` 环境变量,本次第一遍使用的是旧版脚本,没有用到它们。

## 9. 本目录文件说明

`runs/<名称>/` 含 `best.pt`(按验证集选出)、`last.pt`、`config.json`、`summary.json`、`train_log.jsonl`、`stdout.log`、`test_standard.json`、`test_hard.json`;`bench_cuda.txt` / `bench_cpu.txt` 是速度基准原始输出;`RESULTS.md`、`figures/` 是生成的报告;`pytest_output.txt`、`check_acceptance_output.txt`、`make_report_output.txt` 是对应命令输出。
