"""Output contract of the analysis script (ANALYSIS_SPEC section 7) on a SYNTHETIC study that has nonzero death / win / truncation
rates, different best and last scores, a hard scenario that differs from the standard one, missing optional resource fields, an archived
failed attempt and a declared deviation.  Expected values are re-computed here with plain Python from the generating formulas (stdlib
mean/stdev, explicit loops); nothing is taken from the analysis code."""
import json
import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
from prereg_fixture import ARCHS, NS, SEEDS, Study  # noqa: E402

AI = {a: i for i, a in enumerate(ARCHS)}
RUN_A = "prereg_res4_n1_s102"  # carries the archived attempt
RUN_B = "prereg_cnn2_n1_s100"  # lacks the optional resource fields


# --- the generating formulas (the "truth" of the synthetic study)
def base(a, n, si):
    return 100 + si + 3 * AI[a] + (7 if n == 1 else 0)


def n_trunc(a, n, si):
    return si + 1 + (10 if n == 1 else 0)


def n_won(a, n, si):
    return AI[a] + (2 if n == 1 else 0)


def last_rec(kind, a, n, si, e):
    t, w = n_trunc(a, n, si), n_won(a, n, si)
    if e < t:
        return {"steps": 1000, "died": False, "truncated": True}
    if e < t + w:
        return {"score": 377, "steps": 250, "died": False, "won": True}
    return {}


def best_score(a, n, si, e):
    return base(a, n, si) + 6 + (si % 2) + (4 if n == 1 else 0) + (e % 3)


def best_rec(kind, a, n, si, e):
    return {"steps": 1000, "died": False, "truncated": True} if e < 2 else {}


def hard_score(a, n, si, e):
    return 50 + 2 * AI[a] + (5 if n == 1 else 0) + (e % 2)


def hard_rec(kind, a, n, si, e):
    return {"steps": 1000, "died": False, "truncated": True} if e % 50 == 0 else {}


def rec_fn(kind, a, n, si, e):
    return {"last": last_rec, "best": best_rec, "hard": hard_rec}[kind](kind, a, n, si, e)


def last_score_of(a, n, si, e):
    return 377 if n_trunc(a, n, si) <= e < n_trunc(a, n, si) + n_won(a, n, si) else base(a, n, si)


def best_step(a, n, si):
    return 20000 * (1 + (si + AI[a]) % 15)


def summary_fn(name, s):
    s["minutes"] = 100.5 + len(name) % 7
    if name == RUN_B:
        s["peak_working_set_mb"] = None
        s["peak_commit_mb"] = None
        s["peak_memory_error"] = "psutil not installed"  # the file itself explains why the numbers are missing
    else:
        s["peak_working_set_mb"], s["peak_commit_mb"] = 1234.5, None
        s["cuda_max_allocated_mb"] = 10.5 if name == RUN_A else None


ATTEMPT = {"run": RUN_A, "attempt": 1, "reason": "unfinished run directory found at start (synthetic)", "archived_utc": "2000-01-01T00:00:00Z", "files": ["a.json", "b.pt"]}
DEV = {"id": "D1", "description": "synthetic declared deviation", "source": "docs/prereg/FREEZE_CHECKLIST.md#C3"}


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("outputs")
    st = Study(base_dir / "proj", score_fn=lambda a, n, si, e: last_score_of(a, n, si, e), best_fn=best_score, best_step_fn=best_step, hard=True, hard_fn=hard_score,
               rec_fn=rec_fn, summary_fn=summary_fn, attempts=[ATTEMPT], deviations=[DEV])
    out = base_dir / "out"
    A.analyze(st.manifest, st.runs, out, "synthetic")
    return json.loads((out / "analysis.json").read_text()), (out / "REPORT.md").read_text(), json.loads((out / "input_manifest.json").read_text()), st


def near(a, b, tol=1e-12):
    assert abs(a - b) <= tol, (a, b)


# ------------------------------------------------------------------ rates and steps: per-seed counts and sources
def expected_counts(kind, a, n, si):
    if kind == "last_standard":
        t, w = n_trunc(a, n, si), n_won(a, n, si)
        scores = [last_score_of(a, n, si, e) for e in range(300)]
        steps = 1000 * t + 250 * w + 100 * (300 - t - w)
        return {"truncated": t, "won": w, "died": 300 - t - w, "steps": steps, "score": sum(scores)}
    if kind == "best_standard":
        return {"truncated": 2, "won": 0, "died": 298, "steps": 2000 + 100 * 298, "score": sum(best_score(a, n, si, e) for e in range(300))}
    t = len([e for e in range(300) if e % 50 == 0])  # hard
    return {"truncated": t, "won": 0, "died": 300 - t, "steps": 1000 * t + 100 * (300 - t), "score": sum(hard_score(a, n, si, e) for e in range(300))}


@pytest.mark.parametrize("kind", ["last_standard", "best_standard", "last_hard"])
def test_rates_and_steps_report_per_seed_integer_counts_and_their_sources(outputs, kind):
    an, _, inputs, st = outputs
    fname = {"last_standard": "last/standard.json", "best_standard": "best/standard.json", "last_hard": "last/hard.json"}[kind]
    for a in ARCHS:
        for n in NS:
            rs = an["endpoints"][kind]["rates_steps"][f"{a}.n{n}"]
            per = [expected_counts(kind, a, n, si) for si in range(5)]
            for key, field, ck in (("died_rate", "died", "died"), ("won_rate", "won", "won"), ("truncated_rate", "truncated", "truncated"), ("steps_mean", "steps", "steps")):
                obj = rs[key]
                nums = [p[ck] for p in per]
                assert obj["integer_numerators"] == nums and obj["denominator"] == 300 and obj["record_field"] == field
                vals = [x / 300 for x in nums]
                for got, want in zip(obj["per_model"], vals):
                    near(got, want)
                near(obj["mean"], statistics.fmean(vals))
                near(obj["sd_ddof1"], statistics.stdev(vals))
                assert obj["metric_id"] == f"{kind}.{key}.{a}.n{n}" and obj["source_metric_ids"] == [f"{kind}.m.{a}.n{n}"]
                assert [s["run_name"] for s in obj["sources"]] == [f"prereg_{a}_n{n}_s{s}" for s in SEEDS]
                for s_, si in zip(obj["sources"], range(5)):
                    rel = f"{s_['run_name']}/{fname}"
                    assert s_["file"] == rel and s_["sha256"] == inputs["files"][rel]["sha256"] and s_["integer_sum"] == nums[si] and s_["episodes"] == 300
            m = an["endpoints"][kind]["model_metrics"][f"{a}.n{n}"]
            assert m["integer_numerators"] == [p["score"] for p in per]


def test_nonzero_rates_truncation_and_win_actually_occur_in_the_study(outputs):
    an = outputs[0]
    rs = an["endpoints"]["last_standard"]["rates_steps"]["res8.n1"]
    assert rs["truncated_rate"]["integer_numerators"] == [11, 12, 13, 14, 15] and rs["won_rate"]["integer_numerators"] == [4] * 5
    assert rs["died_rate"]["integer_numerators"] == [285, 284, 283, 282, 281]


# ------------------------------------------------------------------ best vs last, hard, report tables
def test_best_minus_last_is_nonzero_and_lists_the_selected_steps(outputs):
    an = outputs[0]
    bl = an["exploratory"]["best_minus_last"]
    for a in ARCHS:
        for n in NS:
            b = bl["b"][f"{a}.n{n}"]
            want = [sum(best_score(a, n, si, e) - last_score_of(a, n, si, e) for e in range(300)) for si in range(5)]
            assert b["integer_numerators"] == want and any(x != 0 for x in want)
            assert b["best_selected_steps"] == [best_step(a, n, si) for si in range(5)]


def test_hard_scenario_values_differ_from_the_standard_ones(outputs):
    an = outputs[0]
    hard, std = an["endpoints"]["last_hard"], an["endpoints"]["last_standard"]
    for a in ARCHS:
        for n in NS:
            h = hard["model_metrics"][f"{a}.n{n}"]
            assert h["integer_numerators"] == [sum(hard_score(a, n, si, e) for e in range(300)) for si in range(5)]
            assert h["integer_numerators"] != std["model_metrics"][f"{a}.n{n}"]["integer_numerators"]


def test_report_contains_model_and_rate_tables_for_best_and_hard_and_a_header_for_the_r_label(outputs):
    rep = outputs[1]
    for q in ("best_standard", "last_hard"):
        assert f"### {q}: model scores, rates and steps" in rep and f"### {q}: per-seed rates and mean steps" in rep
    assert "### last_standard: per-seed death / win / truncation rates and mean steps" in rep
    lines = rep.splitlines()
    i = lines.index("### n=1: res8 minus cnn2 (r)")
    header = lines[i + 2]
    assert header.rstrip().endswith("95% cross-bootstrap | order label |")
    assert all(l.count("|") == header.count("|") for l in lines[i + 4: i + 7])  # every r row has the same number of cells as its header
    assert [l.split("|")[1].strip() for l in lines[i + 4: i + 7]] == ["last_standard.r", "best_standard.r", "last_hard.r"]


# ------------------------------------------------------------------ resources, attempts, deviations
def test_resource_fields_come_from_summary_with_null_and_reason_when_missing(outputs):
    an = outputs[0]
    recs = {r["run_name"]: r for r in an["resource_records"]}
    assert len(recs) == 30
    for name, r in recs.items():
        assert r["resources"]["minutes"] == {"value": 100.5 + len(name) % 7, "reason": None, "source": f"{name}/summary.json#minutes"}
        assert r["replay_size"] == 100000 and r["actual_updates"] == 74000 and r["sources"]["replay_size"] == f"{name}/summary.json#replay.size"
    b = recs[RUN_B]["resources"]
    assert b["peak_working_set_mb"]["value"] is None and "psutil not installed" in b["peak_working_set_mb"]["reason"]
    assert b["cuda_max_reserved_mb"]["value"] is None and b["cuda_max_reserved_mb"]["reason"] == "field absent from summary.json; peak_memory_error: psutil not installed"
    a = recs[RUN_A]["resources"]
    assert a["peak_working_set_mb"]["value"] == 1234.5 and a["peak_commit_mb"] == {"value": None, "reason": "null in summary.json", "source": f"{RUN_A}/summary.json#peak_commit_mb"}
    assert a["cuda_max_allocated_mb"]["value"] == 10.5
    assert "NaN" not in json.dumps(an)


def test_report_shows_resource_columns_and_n_a_for_missing(outputs):
    rep = outputs[1]
    sec = rep[rep.index("## 6. Resource records"):rep.index("## 7.")]
    assert "| minutes | peak working set MB | peak commit MB | CUDA max allocated MB | CUDA max reserved MB | failed attempts |" in sec
    row_b = next(l for l in sec.splitlines() if l.startswith(f"| {RUN_B} |"))
    assert "n/a" in row_b and row_b.rstrip().endswith("| 0 |")
    row_a = next(l for l in sec.splitlines() if l.startswith(f"| {RUN_A} |"))
    assert "1234.5" in row_a and "10.5" in row_a and row_a.rstrip().endswith("| 1 |")


def test_failed_attempts_are_listed_per_run_with_their_details(outputs):
    an, rep, _, _ = outputs
    recs = {r["run_name"]: r for r in an["resource_records"]}
    assert recs[RUN_A]["attempts"] == [{**ATTEMPT, "source": "results_prereg/evaluation_seal.json#attempts[0]"}]
    assert all(r["attempts"] == [] for n, r in recs.items() if n != RUN_A)
    assert f"| {RUN_A} | 1 | 2000-01-01T00:00:00Z | unfinished run directory found at start (synthetic) | 2 |" in rep


def test_deviations_come_only_from_the_freeze_record_and_the_seal_attempts(outputs):
    an, rep, _, _ = outputs
    d = an["deviations"]
    assert d[0] == {"id": "D1", "origin": "freeze_manifest", "description": "synthetic declared deviation", "source": "docs/prereg/FREEZE_CHECKLIST.md#C3"}
    assert d[1]["id"] == f"failed_attempt:{RUN_A}:1" and d[1]["origin"] == "evaluation_seal" and d[1]["source"] == "results_prereg/evaluation_seal.json#attempts[0]"
    assert len(d) == 2 and "deviations on record: 2" in rep and "synthetic declared deviation" in rep


def test_a_study_without_records_reports_no_deviations_and_says_the_script_does_not_infer_any(tmp_path):
    st = Study(tmp_path / "proj")
    out = tmp_path / "out"
    A.analyze(st.manifest, st.runs, out, "synthetic")
    an = json.loads((out / "analysis.json").read_text())
    rep = (out / "REPORT.md").read_text()
    assert an["deviations"] == [] and "does not infer deviations" in rep and "No failed attempts were archived." in rep
    assert all(r["resources"]["minutes"]["value"] is None and r["resources"]["minutes"]["reason"] == "field absent from summary.json" for r in an["resource_records"])


def test_source_claims_in_the_report_are_the_ones_the_json_keeps(outputs):
    an, rep, _, _ = outputs
    assert "every number in analysis.json carries" not in rep  # the old, unachievable blanket claim
    sec = rep[rep.index("## 7."):]
    assert "source_metric_ids" in sec and "resources.<field>.source" in sec
    st = an["primary_decisions"]["res4_sign_test"]
    assert st["source_metric_id"] == "last_standard.d.res4" and st["integer_numerators"] == an["endpoints"]["last_standard"]["effects"]["d"]["res4"]["integer_numerators"]
    for q in an["endpoints"].values():  # every statistic object names its parents
        for k in ("c", "u", "v", "r"):
            assert q["effects"][k]["source_metric_ids"] and q["effects"][k]["formula_id"]


# ------------------------------------------------------------------ malformed provenance records
def fails(tmp_path, code, **kw):
    st = Study(tmp_path / "proj", **kw)
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, tmp_path / "out", "synthetic")
    assert e.value.obj["code"] == code, e.value.obj
    assert not (tmp_path / "out").exists()
    return e.value.obj


def test_attempt_of_an_unknown_run_is_rejected(tmp_path):
    fails(tmp_path, "E_MANIFEST", attempts=[{**ATTEMPT, "run": "prereg_nope_n1_s100"}])


def test_attempt_without_a_reason_is_rejected(tmp_path):
    o = fails(tmp_path, "E_REQUIRED_FIELD", attempts=[{k: v for k, v in ATTEMPT.items() if k != "reason"}])
    assert o["json_path"] == "$.attempts[0].reason"


def test_declared_deviation_without_a_source_is_rejected(tmp_path):
    o = fails(tmp_path, "E_REQUIRED_FIELD", deviations=[{"id": "D1", "description": "x"}])
    assert o["json_path"] == "$.deviations[0].source"


@pytest.mark.parametrize("bad", ["12", -1, True])
def test_an_ill_typed_optional_resource_field_is_an_error_not_a_guess(tmp_path, bad):
    o = fails(tmp_path, "E_FIELD_TYPE", summary_fn=lambda name, s: s.update(minutes=bad) if name == RUN_B else None)
    assert o["json_path"] == "$.minutes" and o["run_name"] == RUN_B
