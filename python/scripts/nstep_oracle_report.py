#!/usr/bin/env python3
"""Evidence report for the n-step target check (preregistration: small-MDP oracle).

Writes, for every hand-computed fixture and n in {1, 3}: the hand-computed samples/targets, the samples and
targets produced by the real pipeline, and the verdict; plus the result of the planted-bug (mutation) checks, the
code version and the (empty) reviewer fields.  It does not read any training / validation / test result.

  python python/scripts/nstep_oracle_report.py [-o report.md]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "tests"))

import nstep_harness as H  # noqa: E402
from nstep_mutants import MUTANTS  # noqa: E402


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def fmt(rows, double):
    return "; ".join(f"s{r[0]}a{r[1]} ret={float(r[2]):g} disc={float(r[3]):g} s'={r[4]} y={float(r[5] if double else r[6]):g}" for r in rows)


def window(case, sample, gamma):
    """The reward window of one hand-computed sample, read from the scripted environment (not from the pipeline): the rewards of the
    transitions from (s, a) up to the one that reaches the sample's next state, within one episode segment, h = their number.  Returns
    (rewards, h, consistent) where `consistent` checks the hand literals against the script: ret = sum gamma^k r_k and disc = gamma^h
    (0 when the window ends in a real termination)."""
    s0, a0, ret, disc, s_next = sample[0], sample[1], H.Fraction(sample[2]), H.Fraction(sample[3]), sample[4]
    g = H.Fraction(gamma)
    for env in case["envs"]:
        for seg in env:
            for i, t in enumerate(seg):
                if t[0] == s0 and t[1] == a0:
                    rewards, status = [], ""
                    for tt in seg[i:]:
                        rewards.append(H.Fraction(tt[2]))
                        status = tt[4]
                        if tt[3] == s_next:
                            break
                    else:
                        return [], 0, False
                    h = len(rewards)
                    total = sum(r * g**k for k, r in enumerate(rewards))
                    want_disc = H.Fraction(0) if status == "terminated" else g**h
                    return [float(r) for r in rewards], h, bool(total == ret and disc == want_disc)
    return [], 0, False


def build() -> str:
    import torch

    gamma = H.CASES["gamma"]
    out = ["# n-step target oracle: evidence", "",
           f"- code version: `{git('rev-parse', 'HEAD')}`  (working tree {'clean' if not git('status', '--porcelain') else 'MODIFIED'})",
           f"- torch {torch.__version__}; gamma = {gamma} (diagnostic fixture value; the real runs use 0.99)",
           f"- reviewer: `{H.CASES['reviewer']}`  review date: `{H.CASES['review_date']}`  (left empty on purpose: to be filled by an independent human reviewer)",
           "- implementer and verifier of the code and of this report are the same model; the expected values are the preregistration's hand computations, re-derived in exact arithmetic by `tests/nstep_oracle.py`.",
           "- no training, validation or test result was read.", ""]
    ok_all = True
    for case in H.CASES["cases"]:
        out += [f"## {case['name']}", f"_{case['doc_ref']}_", ""]
        for n in (1, 3):
            exp = case["expected"][str(n)]
            for double in (True, False):
                lit = [(s[0], s[1], H.Fraction(s[2]), H.Fraction(s[3]), s[4], H.Fraction(s[5 if double else 6])) for s in exp["samples"]]
                actual, counts, _, _ = H.run_pipeline(case["envs"], case["q_online"], case["q_target"], n, gamma, double)
                ok = actual == sorted(lit) and counts == exp["counts"]
                ok_all &= ok
                wins = [window(case, smp, gamma) for smp in exp["samples"]]
                ok_all &= all(w[2] for w in wins)
                out += [f"### n={n}, {'Double DQN' if double else 'plain max target'}: {'PASS' if ok else 'FAIL'}",
                        f"- stored samples after each round (hand / actual): {exp['counts']} / {counts}",
                        f"- hand-computed: {fmt(sorted(lit), True)}", f"- actual:        {fmt(actual, True)}",
                        "- reward window and h of each hand-computed sample (read from the scripted episode; ret = sum gamma^k r_k, disc = gamma^h or 0 at a real termination): "
                        + "; ".join(f"s{smp[0]}a{smp[1]}: rewards={w[0]} h={w[1]} {'consistent' if w[2] else 'INCONSISTENT'}" for smp, w in zip(exp["samples"], wins)), ""]
    out += ["## planted bugs (each must be detected)"]
    for name in sorted(MUTANTS):
        impl, caught = MUTANTS[name](), False
        for case in H.CASES["cases"]:
            for n in (1, 3):
                for double in (True, False):
                    try:
                        H.run_and_compare(case["envs"], case["q_online"], case["q_target"], n, gamma, double, False, **impl)
                    except AssertionError:
                        caught = True
        ok_all &= caught
        out.append(f"- {name}: {'detected' if caught else 'NOT DETECTED'}")
    out += ["", f"**overall: {'PASS' if ok_all else 'FAIL'}**"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = build()
    if "-o" in sys.argv:
        Path(sys.argv[sys.argv.index("-o") + 1]).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
