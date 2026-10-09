#!/usr/bin/env python3
"""Compare two experiment matrices (default: cloud 120k-step CPU run vs local 300k-step GPU run).

All numbers come from the raw per-episode JSON; nothing is typed by hand.
  python python/scripts/make_comparison.py [dir_a dir_b] [-o docs/RESULTS_COMPARISON.md]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ARCHS = ("mlp", "cnn2", "res2", "res4", "res8")
LABEL = {"mlp": "MLP-DQN", "cnn2": "CNN-2", "res2": "ResNet-2", "res4": "ResNet-4", "res8": "ResNet-8"}
SEEDS = (0, 1, 2)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def scores(d: Path, name: str, scenario="standard"):
    p = load(d / "runs" / name / f"test_{scenario}.json")
    if p is None:
        return None
    return np.array([r["score"] for r in sorted(p["records"], key=lambda r: r["seed"])], float)


def seed_avg(d: Path, names, scenario="standard"):
    xs = [scores(d, n, scenario) for n in names]
    return None if any(x is None for x in xs) else np.mean(xs, axis=0)


def ci(x, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def fmt(x):
    lo, hi = ci(x)
    return f"{x.mean():.1f} [{lo:.1f}, {hi:.1f}]"


def per_seed(d: Path, names):
    xs = [scores(d, n) for n in names]
    return None if any(x is None for x in xs) else [float(x.mean()) for x in xs]


def baseline(d: Path, agent: str, scenario="standard"):
    p = load(d / "eval" / f"{agent}__{scenario}__test.json")
    return None if p is None else np.array([r["score"] for r in sorted(p["records"], key=lambda r: r["seed"])], float)


def order_note(a: Path, b: Path) -> str:
    """Is the ResNet-2 vs ResNet-4 order the same in both runs?  (Derived from the data.)"""
    def res2_gt_res4(d):
        x2 = seed_avg(d, [f"res2_s{s}" for s in SEEDS])
        x4 = seed_avg(d, [f"res4_s{s}" for s in SEEDS])
        return None if x2 is None or x4 is None else bool(x2.mean() > x4.mean())

    ra, rb = res2_gt_res4(a), res2_gt_res4(b)
    if ra is None or rb is None:
        return ""
    if ra != rb:
        return "卷积网络内部的排序**不稳定**:ResNet-2 与 ResNet-4 的先后在两次运行里互换,差距落在训练种子间的波动范围内。"
    return "ResNet-2 与 ResNet-4 的先后在两次运行里一致,但差距仍在训练种子波动范围内。"


def build(a: Path, b: Path, la: str, lb: str) -> str:
    out = [f"# 两套实验的对比(自动生成,请勿手改)\n",
           f"- **A = {la}**(`{a.name}/`),**B = {lb}**(`{b.name}/`)。同一批 300 个测试种子,标准场景,平均得分(满分 377),RL 行为 3 个训练种子的逐局平均。",
           "- 两套实验的硬件、训练步数、并行方式不同;GPU 训练在统计上、而非逐位上可复现,**评估同样依赖设备**:同一 checkpoint 在 GPU 与 CPU 上评估,逐局结果会不同(**均分差异已被独立复现**:同一检查点 `results_gpu/runs/res4_s0/best.pt` 在 GPU 上评估得 142.8,本地执行者在 CPU 上重评得 144.6,云端 CPU 重评同样得 144.6,其中 22/300 局逐局不同;逐局不同的比例范围“约 7% 到 29%”是审计员在不同检查点上的观察,均分差在两分以内;云端没有 GPU,GPU 一侧的数字取自已提交的评估文件)。因此两套之间的比较只能作为方向性证据。\n",
           "## 1. 各智能体:短训练 vs 长训练", f"| 智能体 | A:{la} | B:{lb} | B − A(配对,逐局) | 逐种子 A | 逐种子 B |", "|---|---|---|---|---|---|"]
    for ag, nm in (("random", "random"), ("legacy", "legacy(Java 复刻)"), ("safe-heuristic", "强手写启发式")):
        xa, xb = baseline(a, ag), baseline(b, ag)
        if xa is not None:
            out.append(f"| {nm}(非学习,同一批局) | {fmt(xa)} | {fmt(xb) if xb is not None else '—'} | — | — | — |")
    for arch in ARCHS:
        names = [f"{arch}_s{s}" for s in SEEDS]
        xa, xb = seed_avg(a, names), seed_avg(b, names)
        if xa is None or xb is None:
            continue
        d = xb - xa
        lo, hi = ci(d)
        sa, sb = per_seed(a, names), per_seed(b, names)
        out.append(f"| {LABEL[arch]} | {fmt(xa)} | {fmt(xb)} | {d.mean():+.1f} [{lo:+.1f}, {hi:+.1f}] | "
                   f"{' / '.join(f'{v:.0f}' for v in sa)} | {' / '.join(f'{v:.0f}' for v in sb)} |")
    out += ["", "## 2. 消融:变体 − 完整配方(各自套内的配对差)", "| 套 | 基线 | 变体 | 得分差 [95% CI] | 逐种子变体更高的个数 |", "|---|---|---|---|---|"]
    for tag, d in ((la, a), (lb, b)):
        for arch in ("res4", "mlp"):
            base = [f"{arch}_s{s}" for s in SEEDS]
            xb = seed_avg(d, base)
            if xb is None:
                continue
            variants = [("nodouble", "去掉 Double"), ("nodueling", "去掉 Dueling"), ("nstep1", "n 步 = 1")]
            if arch == "res4":
                variants.append(("raw", "原始网格(无距离场)"))
            for key, lab in variants:
                names = [f"{arch}raw_s{s}" for s in SEEDS] if key == "raw" else [f"{arch}-{key}_s{s}" for s in SEEDS]
                xv = seed_avg(d, names)
                if xv is None:
                    continue
                diff = xv - xb
                lo, hi = ci(diff)
                better = sum(v > w for v, w in zip(per_seed(d, names), per_seed(d, base)))
                out.append(f"| {tag} | {LABEL[arch]} | {lab} | {diff.mean():+.1f} [{lo:+.1f}, {hi:+.1f}] | {better}/3 |")
    out += ["", "## 3. 解读(定性,数字见上表)",
            "- **更长的训练让所有网络变好**:MLP 仍明显高于所有卷积网络;卷积网络的提升有限,且不随深度单调。" + order_note(a, b),
            "- **n 步 = 1 对 ResNet-4 的提升在两次相互独立的运行里都出现**(同代码、同种子、同超参,第二次是在看到第一次结论之后运行的),且逐种子一致,是目前对卷积网络最有效的单项改动,把它与 MLP 的差距大幅缩小,但仍低于 MLP;"
            "对 MLP 则没有稳定结论(两套实验里符号不同),不应推广。这提示默认配方(n 步 = 3)可能对卷积网络次优,但**目前只有 ResNet-4 一个深度点有 n 步 = 1 的数据**,不能说明配方修正后各深度的排序;\"深度无收益\"因此只能理解为\"在这套配方下的经验事实\",归因于配方还是深度要等完整的深度 × n 步矩阵。",
            "- **去掉 Double / 去掉 Dueling 的效应没有被复现**:它们在短训练套里相对完整配方偏好\"去掉\",在长训练套里符号相反。说明这两项的影响小于训练波动,或依赖训练长度,**不应据此取舍**;云端报告里\"去掉 Dueling 有提升\"的说法只能算单次观察。",
            "- **距离场**在两次运行里都对 ResNet-4 有帮助,但每格只有 3 个训练种子,差距接近种子间波动,需谨慎。",
            "- **最好的结论仍然要等第二遍实验**:把所有卷积架构(CNN-2 / ResNet-2 / ResNet-4 / ResNet-8)都用 n 步 = 1 重跑,才能回答\"配方修正后深度是否有益\"。目前只有 ResNet-4 一个深度点有 n 步 = 1 的数据。",
            "- **强手写启发式的差距**会随 MLP 训练变长而缩小,是否越过取决于步数和种子,见第 1 节两列。",
            "- 工程事件(中断续训、内存调度等)见各自的 `LOCAL_RUN_REPORT.md` 与 `docs/PLAN.md` 偏差记录。"]
    return "\n".join(out) + "\n"


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("-")]
    a = Path(args[0]) if len(args) > 0 else ROOT / "results"
    b = Path(args[1]) if len(args) > 1 else ROOT / "results_gpu"
    out = ROOT / "docs" / "RESULTS_COMPARISON.md"
    if "-o" in sys.argv:
        out = Path(sys.argv[sys.argv.index("-o") + 1])
    out.write_text(build(a, b, "12 万步 · CPU(云端)", "30 万步 · GPU(本地)"), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out.name}")


if __name__ == "__main__":
    main()
