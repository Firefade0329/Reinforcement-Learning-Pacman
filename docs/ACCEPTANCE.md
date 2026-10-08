# 验收手册

对应 `docs/PLAN.md` 第 7、8 节。门槛已在方案中固定;本文只讲**怎么验**。

## A. 环境准备
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r python/requirements.txt          # numpy, torch (CPU 即可), matplotlib, pytest
```
> 在无外网直连 pytorch.org 的环境里,直接从 PyPI 安装 `torch` 即可(体积大,含 CUDA 依赖,但 CPU 可用)。

## B. 自动验收

| 步骤 | 命令 | 期望 |
|---|---|---|
| 1. 单元/集成测试 (M1) | `python -m pytest python/tests -q` | 全绿 |
| 2. 快速冒烟 (M2) | `bash python/scripts/acceptance.sh --quick` | 约 5–10 分钟,以 `QUICK ACCEPTANCE PASSED` 结束;其中同一 checkpoint 评估两次的 JSON 必须逐字节相同 |
| 3. 对已提交的完整结果判定 | `bash python/scripts/acceptance.sh` | 逐条输出 `PASS / FAIL / REPORTED / MISSING`,有 MUST 不满足则退出码 1 |
| 4. 重新生成报告 | `python python/scripts/make_report.py` | 重写 `docs/RESULTS.md` 与 `results/figures/*.png`;`git diff` 应无变化 |
| 5. (可选)完整复现 | `bash python/scripts/run_all.sh` | 数小时 CPU;可断点续跑 |
| 6. (可选)重跑 Java 真值 | `bash python/scripts/run_java_legacy.sh 150` | 需要 JDK;在临时目录运行,不改动仓库 |

测试覆盖的重点:
- Python 地图与三份 `Game.java` 中的地图**逐格相同**;378 格、377 个可吃金豆。
- 幽灵永不入墙、不掉头;追击概率与 Java 规则一致(统计检验);碰撞、通关、截断、同种子确定性。
- `legacy` 复刻与**真实运行原版 Java 代码**得到的分布统计上不可区分(得分/步数/死亡率 z 检验 + KS 检验)。
- n 步回报、终止/截断处理、ResNet 初始为恒等、感受野、特征有限且有界、checkpoint 往返一致。

## C. 人工复核清单

1. **看行为**:`results/replays/` 下的 GIF(随机 / legacy / 最终智能体)。最终智能体应当会绕开靠近的幽灵、不原地抖动、清掉大部分金豆。
2. **查数字溯源**:在 `results/runs/<run>/test_standard.json` 里任选一局,核对 `docs/RESULTS.md` 的汇总。
3. **查泄漏**:
   - `python/pacman_rl/evaluate.py` 中测试种子 `10000–10299` 与验证种子 `5000–5049`、训练种子(≥ 1,000,000)互不相交(测试里有断言);
   - `dqn.py` 的 `train()` 只使用验证集挑 checkpoint;测试集只由 `cli eval-model --split test` 在训练结束后使用。
4. **查旧代码**:`git diff 5d5efd5 -- ReinforcementLearning HumanPlayGame DijkstraPathFinding '*.java' Images data/QTable.txt` 为空。
5. **读局限**:`docs/RESULTS.md` 末尾和 `PLAN.md` 第 9 节"偏差记录",确认没有被隐藏的失败或事后改门槛。

## D. 验收结论模板
```
日期:           验收人:
M1 [ ]  M2 [ ]  M3 [ ]  M4 [ ]  M5 [ ]  M6 [ ]  M7 [ ]
S1 [ ]  S2 [ ]  S3 [ ]  S4 [ ]   (未达成项已在 RESULTS.md 说明: 是 / 否)
人工复核 C1–C5 [ ]
结论: 通过 / 有条件通过 / 不通过
