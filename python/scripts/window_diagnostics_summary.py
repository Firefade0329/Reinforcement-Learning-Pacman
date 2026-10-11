#!/usr/bin/env python3
"""Central DESCRIPTIVE summary of the window records (B1 / B2) of the 30 preregistered runs.

  python window_diagnostics_summary.py seal      --results-dir results_prereg --freeze-manifest docs/prereg/freeze_manifest.json --freeze-commit <F> [--out ...]
  python window_diagnostics_summary.py summarize --results-dir results_prereg --freeze-manifest ... --freeze-commit <F> [--seal ...] --out-dir results_prereg/window_diagnostics_summary

Both commands first check the frozen identity (the manifest freezes the two diagnostic code files, their current bytes match, HEAD is exactly the external F, C is
an ancestor, python/ is identical, the C -> F differences are the six freeze-material files, the tracked tree is clean); a failure refuses and publishes nothing.

Reads ONLY the 30 ``runs/<run_name>/window_diagnostics.json`` files (and the matrix for the run list): no evaluation file, checkpoint, test
seed, summary.json, configuration or analysis input.  The seal ``window_diagnostics_seal.json`` is separate from the evaluation seal and
from the core analysis; the core analysis (H1 / H2) neither reads nor needs these files.  Nothing here is a hypothesis test: per
configuration it prints the five per-run rates, mean / sd (ddof=1) over the runs with a defined rate (k of 5), and the pooled
ratio sum(numerator) / sum(denominator).  No p-values, intervals, rankings or regressions.  Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs" / "prereg" / "matrix.csv"
MATRIX_SHA256 = "5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe"
CODE_FILES = ("python/pacman_rl/window_diag.py", "python/scripts/window_diagnostics_summary.py")
FREEZE_MATERIALS = ("docs/prereg/frozen_config_v0.3.2.json", "docs/prereg/freeze_manifest.json", "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md",
                    "docs/prereg/ANALYSIS_SPEC_v0.3.2.md", "docs/prereg/CLAUDE_HANDOFF_v0.3.2.md", "docs/prereg/FREEZE_CHECKLIST.md")  # mirror of provenance.FREEZE_MATERIALS
HEX = set("0123456789abcdef")
SEAL_SCHEMA, SUMMARY_SCHEMA, FILE_SCHEMA = "window-diagnostics-seal-1", "window-diagnostics-summary-1", "window-diagnostics-1"
HEADER = {"definition_version": "1", "counting_source": "emitted_once", "indicator": "action_mismatch_to_selected_greedy", "descriptive_only": True,
          "n_envs": 8, "gamma": 0.99, "bin_size": 20_000}  # the fixed header of every record
BUDGET = 300_000
DIAG = "window_diagnostics.json"


class DiagError(Exception):
    pass


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_matrix(path: Path = MATRIX) -> list[dict]:
    if sha256_file(path) != MATRIX_SHA256:
        raise DiagError("matrix.csv is not the registered file")
    with open(path, newline="", encoding="utf-8") as f:
        return [{"run_name": r["run_name"], "arch": r["arch"], "n_step": int(r["n_step"]), "seed": int(r["seed"])} for r in csv.DictReader(f)]


def _reject_constant(s):
    raise DiagError(f"non-finite JSON constant {s}")


def _finite_float(s):
    v = float(s)
    if not math.isfinite(v):  # 1e999 parses to infinity
        raise DiagError(f"non-finite number {s}")
    return v


def read_diag(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_constant, parse_float=_finite_float)
    except (OSError, ValueError) as e:
        raise DiagError(f"{path.name}: unreadable ({e})")


def file_problems(doc: dict, row: dict, budget: int, freeze_commit: str | None = None) -> list[str]:
    p = []
    if not isinstance(doc, dict) or doc.get("schema_version") != FILE_SCHEMA:
        return [f"schema_version is not {FILE_SCHEMA}"]
    for k, want in HEADER.items():
        if doc.get(k) != want or type(doc.get(k)) is not type(want):
            p.append(f"header {k} is {doc.get(k)!r}, expected {want!r}")
    meta = doc.get("meta") or {}
    if freeze_commit is not None and meta.get("git_sha") != freeze_commit:
        p.append(f"meta.git_sha is {meta.get('git_sha')!r}, the freeze commit F is {freeze_commit}")
    if (doc.get("integrity") or {}).get("verified_against_replay") is not True:
        p.append("the recorder was not verified against the real replay emission (verified_against_replay is not true)")
    for k, want in (("run_name", row["run_name"]), ("arch", row["arch"]), ("n_step", row["n_step"]), ("run_seed", row["seed"])):
        if meta.get(k) != want:
            p.append(f"meta.{k} is {meta.get(k)!r}, the matrix says {want!r}")
    if doc.get("n_step") != row["n_step"] or doc.get("transition_budget") != budget:
        p.append(f"n_step / transition_budget are {doc.get('n_step')!r} / {doc.get('transition_budget')!r}")
    if doc.get("counting_source") != "emitted_once":
        p.append("windows were not counted once at emission")
    if not (doc.get("integrity") or {}).get("complete"):
        p.append(f"the recorder's own integrity checks failed: {(doc.get('integrity') or {}).get('errors')}")
    if (doc.get("totals") or {}).get("collected_transitions") != budget:
        p.append("collected_transitions != the training budget")
    return p


def _git(root: Path, *args: str, allow_fail=False):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise DiagError(f"git is unavailable or timed out ({' '.join(args[:2])}): {e}")
    if r.returncode != 0 and not allow_fail:
        raise DiagError(f"git {' '.join(args[:3])} failed: {r.stderr.strip()[:200]}")
    return r


def freeze_context(manifest_path: Path, root: Path, external_f: str) -> dict:
    """The frozen identity the auxiliary tools rely on: the manifest (formal, complete) and its two frozen diagnostic-code hashes, the external F, and the current
    repository being exactly F (C an ancestor, equal python/ trees, C -> F differences within the six freeze-material files, clean tracked tree)."""
    root = Path(root)
    if not (isinstance(external_f, str) and len(external_f) == 40 and set(external_f) <= HEX):
        raise DiagError("--freeze-commit must be the full 40-hex freeze commit F from the external freeze record")
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"), parse_constant=_reject_constant, parse_float=_finite_float)
    except (OSError, ValueError) as e:
        raise DiagError(f"freeze manifest unreadable: {e}")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "prereg-freeze-1" or manifest.get("synthetic") is not False or manifest.get("complete") is not True:
        raise DiagError("the freeze manifest is not a complete formal prereg-freeze-1 manifest")
    c = manifest.get("code_commit")
    if not (isinstance(c, str) and len(c) == 40 and set(c) <= HEX):
        raise DiagError("the freeze manifest has no full code_commit")
    files = manifest.get("frozen_files") if isinstance(manifest.get("frozen_files"), dict) else {}
    frozen_code = {}
    for rel in CODE_FILES:
        want = files.get(rel)
        if not (isinstance(want, str) and len(want) == 64 and set(want) <= HEX):
            raise DiagError(f"the freeze manifest does not freeze {rel}")
        actual = sha256_file(root / rel) if (root / rel).is_file() else None
        if actual != want:
            raise DiagError(f"{rel}: the current code {actual} differs from the frozen hash {want}")
        frozen_code[rel] = want
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if head != external_f:
        raise DiagError(f"HEAD {head} is not the external freeze commit F {external_f}")
    if _git(root, "rev-parse", "--verify", f"{c}^{{commit}}", allow_fail=True).stdout.strip() != c:
        raise DiagError("the code commit C of the manifest is not a commit of this repository")
    if _git(root, "merge-base", "--is-ancestor", c, "HEAD", allow_fail=True).returncode != 0:
        raise DiagError("the code commit C is not an ancestor of F")
    if _git(root, "rev-parse", f"{c}:python").stdout.strip() != _git(root, "rev-parse", "HEAD:python").stdout.strip():
        raise DiagError("the python/ tree at F differs from the one at C")
    outside = sorted(x for x in _git(root, "diff", "--name-only", c, "HEAD").stdout.splitlines() if x and x not in FREEZE_MATERIALS)
    if outside:
        raise DiagError(f"files outside the six freeze-material files differ between C and F: {outside[:5]}")
    if [x for x in _git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines() if x.strip()]:
        raise DiagError("the working tree has uncommitted changes to tracked files")
    return {"code_commit": c, "freeze_commit": external_f, "freeze_manifest_sha256": sha256_file(manifest_path), "frozen_code_sha256": frozen_code}


def build_seal(results_dir: Path, rows: list[dict], freeze: dict, budget: int | None = None) -> dict:
    budget = BUDGET if budget is None else budget
    runs = Path(results_dir) / "runs"
    files, problems = {}, []
    for r in rows:
        f = runs / r["run_name"] / DIAG
        if not f.is_file():
            problems.append(f"{r['run_name']}: {DIAG} missing")
            continue
        try:
            problems += [f"{r['run_name']}: {x}" for x in file_problems(read_diag(f), r, budget, freeze["freeze_commit"])]
        except DiagError as e:
            problems.append(f"{r['run_name']}: {e}")
        files[f"{r['run_name']}/{DIAG}"] = sha256_file(f)
    if problems:
        raise DiagError("not sealable:\n  - " + "\n  - ".join(problems))
    return {"schema_version": SEAL_SCHEMA, "matrix_sha256": MATRIX_SHA256, "runs": [r["run_name"] for r in rows], "files": files,
            "transition_budget": budget, "code_commit": freeze["code_commit"], "freeze_commit": freeze["freeze_commit"],
            "freeze_manifest_sha256": freeze["freeze_manifest_sha256"], "code_sha256": dict(freeze["frozen_code_sha256"]), "descriptive_only": True}


def verify_seal(results_dir: Path, seal: dict, rows: list[dict], freeze: dict | None = None) -> None:
    if seal.get("schema_version") != SEAL_SCHEMA or seal.get("runs") != [r["run_name"] for r in rows] or seal.get("matrix_sha256") != MATRIX_SHA256:
        raise DiagError("the seal is not a window-diagnostics seal for this matrix")
    if freeze is not None:  # frozen identity: manifest, F, C and the code hashes sealed == frozen == current
        for k in ("code_commit", "freeze_commit", "freeze_manifest_sha256"):
            if seal.get(k) != freeze[k]:
                raise DiagError(f"the seal's {k} {seal.get(k)!r} differs from the frozen {freeze[k]!r}")
        if seal.get("code_sha256") != freeze["frozen_code_sha256"]:
            raise DiagError("the sealed code hashes differ from the frozen / current diagnostic code")
    if set(seal.get("files", {})) != {f"{r['run_name']}/{DIAG}" for r in rows}:
        raise DiagError("the sealed file set is not exactly the 30 window records")
    for rel, want in seal["files"].items():
        f = Path(results_dir) / "runs" / rel
        if not f.is_file() or sha256_file(f) != want:
            raise DiagError(f"{rel} is missing or differs from the sealed hash")


# ------------------------------------------------------------------------------------------------ statistics
def ratio_summary(pairs: list[tuple[int, int]]) -> dict:
    """pairs = [(numerator, denominator)] of the runs of one configuration (any number).  Per-run raw rates (null at a zero denominator),
    mean and sd (ddof=1) over the runs with a defined rate, k defined, and the pooled ratio sum(num) / sum(den).  Exact rational arithmetic."""
    per = [{"numerator": n, "denominator": d, "rate": (n / d) if d else None} for n, d in pairs]
    defined = [Fraction(n) / Fraction(d) for n, d in pairs if d]
    k = len(defined)
    mean = sum(defined) / k if k else None
    if k >= 2:
        var = sum((x - mean) ** 2 for x in defined) / (k - 1)
        sd, sd_status = math.sqrt(var), "ok"
    else:
        sd, sd_status = None, "needs_at_least_2_defined_runs"
    sn, sd_den = sum(n for n, _ in pairs), sum(d for _, d in pairs)
    return {"per_run": per, "k_defined": k, "n_runs": len(pairs), "mean_of_defined": float(mean) if mean is not None else None,
            "mean_status": "ok" if k else "no_defined_run", "sd_ddof1": sd, "sd_status": sd_status,
            "pooled": {"numerator": sn, "denominator": sd_den, "rate": (sn / sd_den) if sd_den else None, "status": "ok" if sd_den else "no_eligible_windows"},
            "note": "descriptive: mean of the per-run rates over the k runs with a defined rate, and the pooled ratio; two different quantities"}


def value_summary(vals: list) -> dict:
    d = [Fraction(v) for v in vals if v is not None]
    k = len(d)
    mean = sum(d) / k if k else None
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (k - 1)) if k >= 2 else None
    return {"per_run": list(vals), "k_defined": k, "n_runs": len(vals), "mean_of_defined": float(mean) if mean is not None else None, "sd_ddof1": sd}


RATE_KEYS = ("p_later_mismatch", "p_greedy_start", "p_later_mismatch_given_greedy_start", "p_later_mismatch_hge2", "p_later_mismatch_given_greedy_start_hge2",
             "full_horizon_fraction", "death_window_fraction", "greedy_start_death_window_fraction", "cooccurrence_given_greedy_start_death",
             "cooccurrence_given_any_death", "cooccurrence_of_all_windows", "death_step_mismatch_given_greedy_start_death",
             "earlier_mismatch_given_greedy_start_death", "death_given_later_mismatch_greedy_start", "death_given_no_later_mismatch_greedy_start",
             "death_component_abs_share_T")
VALUE_KEYS = ("death_component_mean_greedy_start_death", "death_component_mean_T")


def group_summary(docs: list[dict], getter) -> dict:
    """docs = the (up to five) run records of one configuration; getter(doc) -> the metric group of one run (or None)."""
    groups = [getter(d) for d in docs]
    out = {"n_windows": value_summary([g["n_windows"] if g else None for g in groups])}
    for k in RATE_KEYS:
        out[k] = ratio_summary([(g[k]["numerator"], g[k]["denominator"]) if g and g.get(k) else (0, 0) for g in groups])
    for k in VALUE_KEYS:
        out[k] = value_summary([g[k] if g else None for g in groups])
    return out


def summarize(results_dir: Path, seal: dict, rows: list[dict], freeze: dict | None = None, budget: int | None = None) -> dict:
    verify_seal(results_dir, seal, rows, freeze)
    docs = {r["run_name"]: read_diag(Path(results_dir) / "runs" / r["run_name"] / DIAG) for r in rows}
    if freeze is not None:  # structure and identity of every record again (a record can be fine in bytes and wrong in content)
        bad = [f"{r['run_name']}: {x}" for r in rows for x in file_problems(docs[r["run_name"]], r, BUDGET if budget is None else budget, freeze["freeze_commit"])]
        if bad:
            raise DiagError("the sealed records are not acceptable:\n  - " + "\n  - ".join(bad))
    configs = {}
    for r in rows:
        configs.setdefault((r["arch"], r["n_step"]), []).append(r)
    out = {}
    for (arch, n), rs in configs.items():
        rs = sorted(rs, key=lambda r: r["seed"])
        ds = [docs[r["run_name"]] for r in rs]
        c = {"training_seeds": [r["seed"] for r in rs], "run_names": [r["run_name"] for r in rs],
             "run_level": {g: group_summary(ds, lambda d, g=g: d["rates"]["run"].get(g)) for g in [f"h{h}" for h in range(1, n + 1)] + ["all"]},
             "by_start_bin_all_h": {b: group_summary(ds, lambda d, b=b: d["rates"]["by_bin"].get(str(b), {}).get("all")) for b in range(15)},
             "pending_total": value_summary([d["pending_total"] for d in ds]),
             "death_events": value_summary([d["totals"]["death_events"] for d in ds])}
        out[f"{arch}.n{n}"] = c
    return {"schema_version": SUMMARY_SCHEMA, "descriptive_only": True, "no_hypothesis_tests": True, "definition_version": HEADER["definition_version"],
            "definition": "action_mismatch_to_selected_greedy; counts are emitted windows (once), not replay samples", "configs": out,
            "identity": {k: seal.get(k) for k in ("code_commit", "freeze_commit", "freeze_manifest_sha256")},
            "inputs": {"files": seal["files"], "seal_code_sha256": seal.get("code_sha256")}}


def _fmt(x, d=4):
    return "n/a" if x is None else f"{x:.{d}f}"


def render(summary: dict) -> str:
    L = ["# Window diagnostics B1 / B2 (descriptive, secondary)", "",
         "Not part of the H1 / H2 decision. No tests, intervals or rankings. 'mean' is over the k of 5 runs with a defined rate; 'pooled' is sum(numerator) / sum(denominator).",
         "A deviation means 'executed action != the greedy action selected for that batch' (ties are not special-cased); co-occurrence with death does not say which action caused it.", ""]
    for cfg, c in summary["configs"].items():
        L += [f"## {cfg}", "", "| group | quantity | seed " + " | seed ".join(str(s) for s in c["training_seeds"]) + " | mean (k/5) | sd | pooled |", "|---|---|" + "---|" * 8]
        for g, gs in c["run_level"].items():
            for k in ("p_later_mismatch", "p_later_mismatch_hge2", "p_later_mismatch_given_greedy_start", "full_horizon_fraction", "death_window_fraction",
                      "cooccurrence_given_greedy_start_death", "death_given_later_mismatch_greedy_start"):
                s = gs[k]
                L.append(f"| {g} | {k} | " + " | ".join(f"{p['numerator']}/{p['denominator']}" for p in s["per_run"]) + f" | {_fmt(s['mean_of_defined'])} ({s['k_defined']}/{s['n_runs']}) | {_fmt(s['sd_ddof1'])} | {_fmt(s['pooled']['rate'])} |")
        L += ["", "Start-time bins (20000 transitions each), all windows, p_later_mismatch_hge2 (mean of defined / pooled):", "",
              "| bin | " + " | ".join(str(b) for b in range(15)) + " |", "|---|" + "---|" * 15,
              "| mean | " + " | ".join(_fmt(c["by_start_bin_all_h"][b]["p_later_mismatch_hge2"]["mean_of_defined"]) for b in range(15)) + " |",
              "| pooled | " + " | ".join(_fmt(c["by_start_bin_all_h"][b]["p_later_mismatch_hge2"]["pooled"]["rate"]) for b in range(15)) + " |", ""]
    return "\n".join(L) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("seal", "summarize"):
        p = sub.add_parser(name)
        p.add_argument("--results-dir", type=Path, default=ROOT / "results_prereg")
        p.add_argument("--freeze-manifest", type=Path, required=True, help="the committed freeze_manifest.json (it freezes the two diagnostic code files)")
        p.add_argument("--freeze-commit", required=True, help="the full freeze commit F from the external freeze record; HEAD must be exactly this commit")
        p.add_argument("--project-root", type=Path, default=ROOT)
        if name == "seal":
            p.add_argument("--out", type=Path)
        else:
            p.add_argument("--seal", type=Path)
            p.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        rows = load_matrix()
        freeze = freeze_context(a.freeze_manifest, a.project_root, a.freeze_commit)
        if a.cmd == "seal":
            out = a.out or a.results_dir / "window_diagnostics_seal.json"
            if out.exists():
                raise DiagError(f"{out.name} already exists; the window records are sealed once")
            write_text_atomic(out, json.dumps(build_seal(a.results_dir, rows, freeze), indent=1, sort_keys=True, allow_nan=False))
            print(f"window diagnostics seal written: {sha256_file(out)}")
            return 0
        seal_path = a.seal or a.results_dir / "window_diagnostics_seal.json"
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        if a.out_dir.exists():
            raise DiagError("output directory already exists")
        summary = summarize(a.results_dir, seal, rows, freeze)
        summary["created_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        summary["seal_sha256"] = sha256_file(seal_path)
        a.out_dir.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix=".wd_tmp_", dir=a.out_dir.parent))
        (tmp / "window_diagnostics_summary.json").write_text(json.dumps(summary, indent=1, allow_nan=False), encoding="utf-8", newline="\n")
        (tmp / "window_diagnostics_summary.md").write_text(render(summary), encoding="utf-8", newline="\n")
        os.rename(tmp, a.out_dir)
        print(f"summary written to {a.out_dir.name}")
        return 0
    except (DiagError, OSError, ValueError) as e:
        sys.stderr.write(json.dumps({"error": str(e)}) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
