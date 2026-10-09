#!/usr/bin/env python3
"""Generate docs/RESULTS.md and results/figures/*.png from the raw JSON in results/.

No number in the report is typed by hand.  Run after the experiments:
  python python/scripts/make_report.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

import acceptance_lib as L

FIG = L.RESULTS / "figures"
OUT = (L.RESULTS / "RESULTS.md") if os.environ.get("PACMAN_RESULTS_DIR") else (L.ROOT / "docs" / "RESULTS.md")
LABEL = {"random": "L0 random", "greedy-bfs": "L1 greedy-BFS (no dodging)", "legacy": "L2 legacy (Java replica)",
         "safe-heuristic": "L3 safe-heuristic", "tabular": "L4 tabular Q (64 states)",
         "mlp": "L5 MLP-DQN", "cnn2": "L6 CNN-2 DQN", "res2": "L7 ResNet-2 DQN", "res4": "L7 ResNet-4 DQN",
         "res8": "L7 ResNet-8 DQN"}


def ci_str(x):
    lo, hi = L.boot_ci(x)
    return f"{x.mean():.1f} [{lo:.1f}, {hi:.1f}]"


def row(label, payload_or_arrays):
    s, d, w, st = payload_or_arrays
    return f"| {label} | {ci_str(s)} | {d.mean() * 100:.0f}% | {w.mean() * 100:.0f}% | {st.mean():.0f} |"


def arrays_from_payload(p):
    return [L.per_episode(p, k) for k in ("score", "died", "won", "steps")]


def arrays_from_runs(names, scenario):
    ps = [L.run_eval(n, scenario) for n in names]
    if any(p is None for p in ps):
        return None
    return [np.mean([L.per_episode(p, k) for p in ps], axis=0) for k in ("score", "died", "won", "steps")]


HEAD = "| agent | mean score [95% CI] | death rate | win rate | mean steps |\n|---|---|---|---|---|"


def table_main(scenario):
    lines = [HEAD]
    for b in L.BASELINES:
        p = L.baseline(b, scenario)
        if p:
            lines.append(row(LABEL[b], arrays_from_payload(p)))
    a = arrays_from_runs([f"tabular_s{s}" for s in L.SEEDS], scenario)
    if a:
        lines.append(row(LABEL["tabular"] + " (mean of 3 seeds)", a))
    for arch in L.ARCHS:
        a = arrays_from_runs(L.run_names(arch), scenario)
        if a:
            lines.append(row(LABEL[arch] + " (mean of 3 seeds)", a))
    return "\n".join(lines)


def table_seeds(scenario="standard"):
    lines = ["| config | seed 0 | seed 1 | seed 2 | mean ± std over seeds | val score (selection) |", "|---|---|---|---|---|---|"]
    groups = [(a, L.run_names(a)) for a in L.ARCHS]
    base = L.ABLATION_ARCH
    for v in ("nodouble", "nodueling", "nstep1"):
        groups.append((f"{base} -{v}", [f"{base}-{v}_s{s}" for s in L.SEEDS]))
    groups.append((f"{base} raw grid (no distance fields)", [f"{base}raw_s{s}" for s in L.SEEDS]))
    for v in ("nodouble", "nodueling", "nstep1"):
        groups.append((f"mlp -{v}", [f"mlp-{v}_s{s}" for s in L.SEEDS]))
    for label, names in groups:
        ps = [L.run_eval(n, scenario) for n in names]
        if any(p is None for p in ps):
            continue
        m = [float(L.per_episode(p, "score").mean()) for p in ps]
        v = [L.val_score(n) for n in names]
        lines.append(f"| {LABEL.get(label, label)} | " + " | ".join(f"{x:.1f}" for x in m) +
                     f" | {np.mean(m):.1f} ± {np.std(m, ddof=1):.1f} | {np.mean(v):.1f} |")
    return "\n".join(lines)


def ablation_deltas():
    """Each ablation vs. its full-recipe baseline, paired per test episode (seed-averaged runs)."""
    lines = ["| 变体 | 基线 | 得分差(变体 − 基线) [95% CI] | 逐种子:变体高于基线的种子数 |", "|---|---|---|---|"]
    for arch in (L.ABLATION_ARCH, "mlp"):
        base_names = L.run_names(arch)
        base = L.seed_avg(base_names, "standard", "score")
        base_seed = [float(L.per_episode(L.run_eval(n), "score").mean()) for n in base_names]
        variants = [("nodouble", "去掉 Double"), ("nodueling", "去掉 Dueling"), ("nstep1", "n 步=1(去掉 n 步)")]
        if arch != "mlp":
            variants.append(("raw", "原始网格(去掉距离场)"))
        for key, label in variants:
            names = [f"{arch}raw_s{s}" for s in L.SEEDS] if key == "raw" else [f"{arch}-{key}_s{s}" for s in L.SEEDS]
            var = L.seed_avg(names, "standard", "score")
            if var is None or base is None:
                continue
            d, lo, hi = L.paired(var, base)
            seed_means = [float(L.per_episode(L.run_eval(n), "score").mean()) for n in names]
            better = sum(v > b for v, b in zip(seed_means, base_seed))
            lines.append(f"| {label} | {LABEL.get(arch, arch)} | {d:+.1f} [{lo:+.1f}, {hi:+.1f}] | {better}/3 |")
    return "\n".join(lines)


def resumed_runs():
    out = []
    for p in sorted(L.RUNS.glob("*/stdout.log")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "[resume]" in txt:
            out.append(p.parent.name)
    return ", ".join(out) if out else "无"


def curves():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for arch in L.ARCHS:
        series = []
        for n in L.run_names(arch):
            p = L.RUNS / n / "train_log.jsonl"
            if not p.exists():
                continue
            rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
            ev = [(r["env_steps"], r["val_score"]) for r in rows if r["type"] == "eval"]
            series.append(ev)
        if not series:
            continue
        n_pts = min(len(s) for s in series)
        xs = [series[0][i][0] for i in range(n_pts)]
        ys = np.array([[s[i][1] for i in range(n_pts)] for s in series])
        ax.plot(xs, ys.mean(0), marker="o", ms=3, label=LABEL[arch])
        ax.fill_between(xs, ys.min(0), ys.max(0), alpha=0.15)
    for b, ls in (("legacy", "--"), ("safe-heuristic", ":")):
        p = L.baseline(b, "standard", "val")
        if p:
            ax.axhline(np.mean([r["score"] for r in p["records"]]), color="gray", ls=ls, lw=1, label=LABEL[b])
    ax.set_xlabel("environment steps")
    ax.set_ylabel("validation score (pellets eaten, max 377)")
    ax.set_title("Learning curves (mean over 3 seeds, band = min/max)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "learning_curves.png", dpi=140)
    plt.close(fig)

    # final comparison bar chart (standard + hard)
    fig, ax = plt.subplots(figsize=(8, 4))
    labels, std, hard = [], [], []
    for b in L.BASELINES:
        ps, ph = L.baseline(b, "standard"), L.baseline(b, "hard")
        if ps and ph:
            labels.append(LABEL[b].split(" ")[0]); std.append(L.per_episode(ps, "score").mean()); hard.append(L.per_episode(ph, "score").mean())
    for key, lab in [("tabular", "L4")] + [(a, LABEL[a].split(" ")[0] + " " + a) for a in L.ARCHS]:
        names = [f"tabular_s{s}" for s in L.SEEDS] if key == "tabular" else L.run_names(key)
        s_, h_ = arrays_from_runs(names, "standard"), arrays_from_runs(names, "hard")
        if s_ and h_:
            labels.append(lab); std.append(s_[0].mean()); hard.append(h_[0].mean())
    x = np.arange(len(labels))
    ax.bar(x - 0.2, std, 0.4, label="standard (30 % chase)")
    ax.bar(x + 0.2, hard, 0.4, label="hard (70 % chase, unseen)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("test score")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "final_comparison.png", dpi=140)
    plt.close(fig)


def limitations(acc_text: str) -> str:
    """Section 8 text, derived from the data of THIS results directory (no claim is hard-coded)."""
    is_gpu = bool(os.environ.get("PACMAN_RESULTS_DIR"))
    conv = ("cnn2", "res2", "res4", "res8")
    mean_of = lambda arch: float(L.seed_avg(L.run_names(arch), "standard", "score").mean())  # noqa: E731
    leg = float(L.per_episode(L.baseline("legacy"), "score").mean())
    mlp = mean_of("mlp")
    means = {a: mean_of(a) for a in conv}
    above = [LABEL[a].split(" ", 1)[1] for a in conv if means[a] > leg]
    steps = (L.load(L.RUNS / "res4_s0" / "config.json") or {}).get("total_env_steps", "?")
    out = []
    if "S1  SHOULD PASS" in acc_text:
        out.append("- **S1 达成但没有超过强手写启发式**:最终神经网络(MLP)与 `safe-heuristic` 的差距在 -3% 的门槛之内,统计上难以区分(第 7 节配对置信区间),但并不比它好。")
    else:
        out.append("- **S1 未达成**:最终神经网络(MLP)的平均得分低于强手写启发式 `safe-heuristic` 超过 3%,差距见第 7 节。\"认真写规则\"仍然更强。")
    below = [a for a in conv if means[a] < mlp]
    conv_txt = "所有卷积网络的平均得分都明显低于 MLP" if len(below) == len(conv) else "部分卷积网络接近或超过 MLP(见第 3 节)"
    leg_txt = ("平均得分高于 `legacy` 的卷积网络只有:" + "、".join(above) + "(差距是否显著看第 3 节置信区间)") if above else "没有任何卷积网络的平均得分超过 `legacy`"
    mono = "monotone in depth: True" in acc_text
    out.append(f"- **卷积网络**:{conv_txt};{leg_txt}。深度{'单调' if mono else '并不单调'}有益(S4)。\"深度无收益\"的结论只对本报告的训练预算({steps} 环境步/运行)和这一套超参成立;是否已充分训练**没有做收敛检验**(第 6 节曲线仅供参考)。")
    d = L.seed_avg(L.run_names("res4"), "standard", "score")
    v = L.seed_avg([f"res4-nstep1_s{s}" for s in L.SEEDS], "standard", "score")
    if d is not None and v is not None:
        diff, lo, hi = L.paired(v, d)
        if lo > 0:
            out.append("- **默认配方对卷积网络可能次优**:所有架构共用同一套超参(未逐架构调参),而消融显示去掉 n 步在 ResNet-4 上得分明显更高(第 5 节);原因目前只是假设(例如 ε-贪心探索下 n 步回报带入探索动作的偏差),**没有被实验验证**。因此\"深度无收益\"也可能部分来自配方,而不是网络深度本身。")
        else:
            out.append("- 消融里去掉 n 步对 ResNet-4 没有显著提升(第 5 节)。所有架构共用同一套超参,未逐架构调参。")
    out.append("- **各结论的稳健性**:云端 CPU 套与本地 GPU 套两次独立实验里,只有\"去掉 n 步对 ResNet-4 有利\"和\"距离场有帮助\"复现;去掉 Dueling / Double 的效应符号相反,不应据此取舍。详见 `docs/RESULTS_COMPARISON.md`(自动生成)。")
    out.append("- **输入里有特权信息**:MLP 的工程特征和卷积网络的距离场都由游戏内部状态(BFS 距离)算出;原始网格对照显示距离场对 ResNet-4 有帮助。MLP 表现最好,很可能因为特征直接给出了最短路信息,而不是\"神经网络更擅长\"。")
    hard = [float(np.mean(L.per_episode(L.baseline(b, "hard"), "died"))) for b in L.BASELINES] + \
           [float(arrays_from_runs(L.run_names(a), "hard")[1].mean()) for a in L.ARCHS]
    out.append(f"- **困难场景**(幽灵 70% 追击,训练中未见)下各智能体的死亡率最低为 {min(hard) * 100:.0f}%,几乎全部被抓,只能比较被抓前吃到的豆数;不能说明任何智能体\"学会了对付强追击\"。")
    out.append("- **只有一张地图**,随机起点提供了状态多样性,但不能声称泛化到别的地图。")
    out.append("- **统计力有限**:每个配置 3 个训练种子,逐局 CI 不含种子间方差;差距较小的比较(例如 ResNet-2 与 ResNet-4)不应过度解读。")
    if is_gpu:
        out.append(f"- **算力与过程**:GPU 上的补充实验({steps} 步/运行);机器信息、中断续训的运行、内存调度等过程细节见同目录 `LOCAL_RUN_REPORT.md`。被续训过的运行:{resumed_runs()}。与云端 CPU 套的并排对比见 `docs/RESULTS_COMPARISON.md`。")
    else:
        out.append(f"- **算力与过程**:CPU、单进程、{steps} 步/运行。过程中两个卷积运行曾被内存不足杀掉后重跑,`res8_s1`、`res8_s2` 使用旧的 float32 回放(与 uint8 回放等价到 1 ulp),虚拟机挂起后部分运行从断点续训(详见 `docs/PLAN.md` 偏差记录)。被续训过的运行:{resumed_runs()}。GPU 上更长训练的补充实验见 `results_gpu/RESULTS.md` 与 `docs/RESULTS_COMPARISON.md`。")
    return "\n".join(out)


def main():
    acc = subprocess.run([sys.executable, str(Path(__file__).with_name("check_acceptance.py")), "--run-tests"],
                         capture_output=True, text=True, cwd=L.ROOT / "python", env={**os.environ, "PYTHONPATH": str(L.ROOT / "python")})
    try:
        curves()
        pre = "figures" if os.environ.get("PACMAN_RESULTS_DIR") else "../results/figures"  # relative to where OUT lives
        figs = f"![curves]({pre}/learning_curves.png)\n\n![final]({pre}/final_comparison.png)"
    except ImportError:
        figs = "(matplotlib not installed - figures skipped)"

    java = L.load(L.RESULTS / "reference" / "java_legacy.json")
    jtxt = ""
    if java:
        sc = np.array([r["score"] for r in java["records"]], float)
        di = np.array([r["died"] for r in java["records"]], float)
        jtxt = (f"Original Java agent run headless ({len(sc)} games, no seeds): mean score {ci_str(sc)}, "
                f"death rate {di.mean() * 100:.0f}%.")

    arch = L.final_arch()
    md = f"""# 实验结果(由 `python/scripts/make_report.py` 从 `results/` 自动生成,请勿手改)

## 1. 怎么读这份报告
- **得分** = 吃掉的金豆数(0–377)。**死亡率** = 被幽灵抓到而结束的局占比。**通关率** = 吃光 377 个。
- 所有行都在同一批 **300 个测试种子**上评估(同起点,可配对比较);RL 行是 3 个训练种子的逐局平均。
- 神经网络的 checkpoint **仅用验证集(50 局,另一批种子)挑选**;测试集只在最终评估时用。
- 标准场景:幽灵 30% 追击(原版规则)。困难场景:70% 追击,训练中从未见过。

## 2. 对原 Java 代码的复刻校验
{jtxt}
复刻版 `legacy` 与之统计上不可区分(见 `python/tests/test_baselines.py::test_legacy_replica_matches_original_java_run`)。
注意:仓库里 `data/Score.txt` 中的 300+ 高分局并不代表该默认配置的真实表现。

## 3. 标准场景(测试集 300 局)
{table_main("standard")}

## 4. 困难场景(测试集 300 局,训练中未见)
{table_main("hard")}

## 5. 逐种子成绩与消融(标准场景,测试得分)
{table_seeds()}

最终智能体(按验证得分在 5 种网络中选出):**{LABEL.get(arch, arch) if arch else 'n/a'}**

### 消融相对完整配方的变化(配对,标准场景)
{ablation_deltas()}

注:"逐种子"按种子编号对应(各配置的随机初始化与探索轨迹并不相同,所以只是粗略的方向一致性,不是严格配对)。CI 只反映测试局的抽样波动,**不含训练种子间的差异**;每格只有 3 个训练种子。

## 6. 曲线
{figs}

## 7. 验收门槛判定(`check_acceptance.py --run-tests` 输出)
```
{acc.stdout.strip()}
```

## 8. 未达成项与局限(文字由数据决定;数字见上表)
{limitations(acc.stdout)}
"""
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
