#!/usr/bin/env python3
"""Evaluate the acceptance gates of docs/PLAN.md section 7 from results/.

Prints one row per gate: PASS / FAIL / REPORTED / MISSING.  Exit code 1 if any MUST gate is
FAIL or MISSING.  Thresholds are fixed by the plan and must not be edited to fit results.

  python python/scripts/check_acceptance.py [--run-tests]
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np

import acceptance_lib as L

rows = []  # (id, level, status, detail)


def add(gid, level, status, detail):
    rows.append((gid, level, status, detail))


def fmt_paired(label, a, b):
    d, lo, hi = L.paired(a, b)
    return d, lo, hi, f"{label}: diff {d:+.1f} [95% CI {lo:+.1f}, {hi:+.1f}]"


def main(run_tests: bool):
    # ---- M1 / M2 (tests) ---------------------------------------------------------------
    if run_tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", str(L.ROOT / "python" / "tests")],
                           cwd=L.ROOT / "python", env={"PYTHONPATH": str(L.ROOT / "python"), "PATH": "/usr/bin:/bin"},
                           capture_output=True, text=True)
        add("M1", "MUST", "PASS" if r.returncode == 0 else "FAIL", r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])
    else:
        add("M1", "MUST", "MISSING", "run with --run-tests (or: python -m pytest python/tests)")

    # ---- M3 baselines + tabular --------------------------------------------------------
    base = {b: L.baseline(b) for b in L.BASELINES}
    tab = [L.run_eval(f"tabular_s{s}") for s in L.SEEDS]
    miss = [b for b, p in base.items() if p is None] + [f"tabular_s{s}" for s, p in zip(L.SEEDS, tab) if p is None]
    add("M3", "MUST", "PASS" if not miss else "MISSING",
        "baselines random/greedy-bfs/legacy/safe-heuristic + tabular x3 seeds present" if not miss else f"missing: {miss}")

    arch = L.final_arch()
    names = L.run_names(arch) if arch else []
    deep = {sc: L.seed_avg(names, sc, "score") for sc in ("standard", "hard")} if arch else {}
    deep_died = L.seed_avg(names, "standard", "died") if arch else None

    # ---- M4 deep vs legacy -------------------------------------------------------------
    if arch and deep.get("standard") is not None and base["legacy"]:
        leg = L.per_episode(base["legacy"], "score")
        legd = L.per_episode(base["legacy"], "died")
        d, lo, hi, txt = fmt_paired("score", deep["standard"], leg)
        dd, dlo, dhi, txt2 = fmt_paired("death (legacy - deep)", legd, deep_died)
        per_seed = [float(L.per_episode(L.run_eval(n), "score").mean()) for n in names]
        ok = lo > 0 and dlo > 0 and all(x > leg.mean() for x in per_seed)
        add("M4", "MUST", "PASS" if ok else "FAIL",
            f"final arch={arch} (chosen on val). {txt}; {txt2}; per-seed means {[round(x, 1) for x in per_seed]} vs legacy {leg.mean():.1f}")
    else:
        add("M4", "MUST", "MISSING", "needs depth-group runs + legacy baseline")

    # ---- M5 deep vs tabular ------------------------------------------------------------
    tab_names = [f"tabular_s{s}" for s in L.SEEDS]
    tab_avg = L.seed_avg(tab_names, "standard", "score")
    if arch and tab_avg is not None and deep.get("standard") is not None:
        d, lo, hi, txt = fmt_paired("score vs tabular", deep["standard"], tab_avg)
        add("M5", "MUST", "PASS" if lo > 0 else "FAIL", txt)
    else:
        add("M5", "MUST", "MISSING", "needs depth-group runs + tabular runs")

    # ---- M6 matrix completeness + report freshness ------------------------------------
    need = [n for a in L.ARCHS for n in L.run_names(a)]
    base_arch = L.ABLATION_ARCH
    need += [f"{a}-{v}_s{s}" for a in (base_arch, "mlp") for v in ("nodouble", "nodueling", "nstep1") for s in L.SEEDS]
    absent = [n for n in need if L.run_eval(n) is None or L.run_eval(n, "hard") is None]
    add("M6", "MUST", "PASS" if not absent else "MISSING",
        f"{len(need)} runs complete (>=3 seeds per cell)" if not absent else f"missing runs: {absent[:6]}{'...' if len(absent) > 6 else ''}")

    # ---- M7 Java untouched -------------------------------------------------------------
    r = subprocess.run(["git", "diff", "--stat", L.JAVA_BASE_COMMIT, "--", "ReinforcementLearning", "HumanPlayGame",
                        "DijkstraPathFinding", "Pacman.java", "PacmanRL.java", "PacmanDijkstra.java", "Images",
                        "data/QTable.txt", ":(exclude,glob)**/.DS_Store"], cwd=L.ROOT, capture_output=True, text=True)
    add("M7", "MUST", "PASS" if r.returncode == 0 and not r.stdout.strip() else "FAIL",
        "no changes to Java sources / images / Q-table since base commit" if not r.stdout.strip() else r.stdout.strip()[:200])

    # ---- SHOULD gates ------------------------------------------------------------------
    if arch and deep.get("standard") is not None and base["safe-heuristic"]:
        safe = L.per_episode(base["safe-heuristic"], "score")
        rel = (deep["standard"].mean() - safe.mean()) / safe.mean()
        _, _, _, txt = fmt_paired("deep vs safe-heuristic", deep["standard"], safe)
        add("S1", "SHOULD", "PASS" if rel >= -0.03 else "FAIL", f"{txt}; relative {rel * 100:+.1f}% (target >= -3%)")
    else:
        add("S1", "SHOULD", "MISSING", "needs deep + safe-heuristic")

    br = L.best_resnet()
    c2 = L.seed_avg(L.run_names("cnn2"), "standard", "score")
    rn = L.seed_avg(L.run_names(br), "standard", "score") if br else None
    if rn is not None and c2 is not None:
        d, lo, hi, txt = fmt_paired(f"{br} vs cnn2", rn, c2)
        add("S2", "SHOULD", "PASS" if lo > 0 else "FAIL", txt + ("" if lo > 0 else "  -> depth shows no significant gain"))
    else:
        add("S2", "SHOULD", "MISSING", "needs cnn2 and resnet runs")

    if arch and deep.get("hard") is not None and base_hard_ok():
        leg_h = L.per_episode(L.baseline("legacy", "hard"), "score")
        d, lo, hi, txt = fmt_paired("hard: deep vs legacy", deep["hard"], leg_h)
        add("S3", "SHOULD", "PASS" if lo > 0 else "FAIL", txt)
    else:
        add("S3", "SHOULD", "MISSING", "needs hard-scenario evaluations")

    trend = {a: L.seed_avg(L.run_names(a), "standard", "score") for a in ("cnn2", "res2", "res4", "res8")}
    if all(v is not None for v in trend.values()):
        means = {a: float(v.mean()) for a, v in trend.items()}
        mono = means["cnn2"] <= means["res2"] <= means["res4"] <= means["res8"]
        add("S4", "SHOULD", "REPORTED", f"test score by depth {{{', '.join(f'{k}: {v:.1f}' for k, v in means.items())}}}; "
            f"monotone in depth: {mono}")
    else:
        add("S4", "SHOULD", "MISSING", "needs depth group")

    # ---- print -------------------------------------------------------------------------
    w = max(len(r[3]) for r in rows)
    for gid, level, status, detail in rows:
        print(f"{gid:3s} {level:6s} {status:9s} {detail}")
    bad = [r for r in rows if r[1] == "MUST" and r[2] in ("FAIL", "MISSING")]
    print("\nMUST gates:", "ALL PASS" if not bad else f"{len(bad)} not satisfied: {[r[0] for r in bad]}")
    return 1 if bad else 0


def base_hard_ok():
    return L.baseline("legacy", "hard") is not None


if __name__ == "__main__":
    sys.exit(main("--run-tests" in sys.argv))
