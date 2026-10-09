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


def build(a: Path, b: Path, la: str, lb: str) -> str:
    out = [f"# 两套实验的对比(自动生成,请勿手改)\n",
           f"- **A = {la}**(`{a.name}/`),**B = {lb}**(`{b.name}/`)。同一批 300 个测试种子,标准场景,平均得分(满分 377),RL 行为 3 个训练种子的逐局平均。",
           "- 两套实验的硬件、训练步数、并行方式不同;GPU 训练在统计上、而非逐位上可复现。差异只能作为方向性证据。\n",
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
            "- **更长的训练让所有网络变好,但排序没变**:MLP 仍明显高于所有卷积网络;卷积网络的提升有限,且不随深度单调。",
            "- **n 步 = 1 对 ResNet-4 的提升在两套独立实验里都出现**,且逐种子一致,是目前对卷积网络最有效的单项改动,把它与 MLP 的差距大幅缩小,但仍低于 MLP;"
            "对 MLP 则没有稳定结论(两套实验里符号不同),不应推广。因此\"深度无收益\"至少部分来自默认配方(n 步 = 3)对卷积网络不利,而不是网络深度本身。",
            "- **去掉 Double / 去掉 Dueling 的效应没有被复现**:它们在短训练套里相对完整配方偏好\"去掉\",在长训练套里符号相反。说明这两项的影响小于训练波动,或依赖训练长度,**不应据此取舍**;云端报告里\"去掉 Dueling 有提升\"的说法只能算单次观察。",
            "- **距离场**在两套实验里都对 ResNet-4 有帮助,但每格只有 3 个训练种子,差距接近种子间波动,需谨慎。",
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
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
