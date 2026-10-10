"""Acceptance of the analysis script on SYNTHETIC studies only (ANALYSIS_SPEC section 8).  No real result of any kind is
read.  Expected values are hand-derived literals (sections 8.2-8.3 of the specification), binomial sums and closed-form
scalars; nothing is taken from the code under test.  Implementer and test author are the same model: a human reviewer must
still check these fixtures (see the empty sign-off fields in docs/prereg/ at the freeze)."""
import hashlib
import json
import math
import shutil
import subprocess
import sys
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
from prereg_fixture import ARCHS, Study  # noqa: E402

TOL = 1e-12


def const_d(cnn2, res4, res8):
    return {"cnn2": [cnn2] * 5, "res4": [res4] * 5 if not isinstance(res4, list) else res4, "res8": [res8] * 5}


def run(tmp_path, study, name="out"):
    out = tmp_path / name
    A.analyze(study.manifest, study.runs, out, "synthetic")
    return json.loads((out / "analysis.json").read_text()), out


@pytest.fixture(scope="module")
def cache(tmp_path_factory):
    return {}


def get(cache, tmp_path_factory, key, d=None, **kw):
    if key not in cache:
        base = tmp_path_factory.mktemp(key)
        st = Study(base / "proj", d=d, **kw)
        cache[key] = (run(base, st), st)
    return cache[key][0][0], cache[key][0][1], cache[key][1]


def near(a, b, tol=TOL):
    assert abs(a - b) <= tol, (a, b)


def effects(an, q="last_standard"):
    return an["endpoints"][q]["effects"]


# ------------------------------------------------------------------ contracts independent of any study
def test_t_constants_satisfy_the_analytic_df4_cdf():
    getcontext().prec = 60
    F4 = lambda t: Decimal("0.5") + Decimal(t) * (Decimal(t) ** 2 + 6) / (2 * (Decimal(t) ** 2 + 4) ** Decimal("1.5"))  # noqa: E731
    assert abs(F4(A.T95) - Decimal("0.975")) < Decimal("1e-14") and abs(F4(A.T975) - Decimal("0.9875")) < Decimal("1e-14")
    assert (A.T95, A.T975) == (2.7764451051977944, 3.4954059325164377)


def test_bootstrap_index_stream_matches_the_specification():
    """Independent re-generation of the contracted stream: first two rounds, a few J values, and the SHA-256 of all 12,200,000 bytes."""
    rng = np.random.Generator(np.random.PCG64(271828))
    h = hashlib.sha256()
    first = []
    for b in range(10000):
        I = rng.integers(0, 5, size=5, dtype=np.int64, endpoint=False)
        J = rng.integers(0, 300, size=300, dtype=np.int64, endpoint=False)
        if b < 2:
            first.append((I.tolist(), J[:12].tolist(), J[-3:].tolist()))
        h.update(I.astype("<u4").tobytes() + J.astype("<u4").tobytes())
    assert first[0] == ([4, 3, 2, 4, 0], [66, 136, 166, 3, 27, 281, 0, 57, 286, 162, 259, 184], [40, 277, 99])
    assert first[1] == ([4, 0, 2, 3, 1], [68, 44, 215, 23, 198, 263, 116, 26, 292, 237, 173, 150], [175, 261, 212])
    assert h.hexdigest() == A.EXPECTED_INDEX_SHA == "f3c35599fe764bf0a2c124544930609b643c2d5aa33ee0acc5b34454d91c9f69"
    # the script's own generator yields the same bytes
    g = A.bootstrap_stream()
    for _ in range(10000):
        sha = next(g)[2]
    assert sha.hexdigest() == A.EXPECTED_INDEX_SHA


def test_quantile_unit_fixture_type7():
    q = np.quantile(np.arange(1, 10001, dtype=np.float64), [0.025, 0.975], method="linear")
    near(q[0], 250.975)
    near(q[1], 9750.025)


def test_exact_sign_test_counts():
    for num, (neff, k, n, den) in {(1,) * 5: (5, 5, 1, 32), (1, 1, 1, 1, -1): (5, 4, 6, 32), (0, 1, 2, 3, -1): (4, 3, 5, 16), (-1,) * 5: (5, 0, 32, 32)}.items():
        s = A.sign_test(list(num))
        assert (s["n_effective"], s["k_positive"], s["numerator"], s["denominator"]) == (neff, k, n, den) and s["status"] == "ok"
    z = A.sign_test([0] * 5)
    assert z["status"] == "no_effective_samples" and z["p"] == 1.0 and z["n_effective"] == 0 and z["zero_count"] == 5


# ------------------------------------------------------------------ valid statistical fixtures F1-F8
def test_F1_constant_differences(cache, tmp_path_factory):
    an, out, _ = get(cache, tmp_path_factory, "F1", const_d(10, 20, 30))
    L, P = effects(an), an["primary_decisions"]
    for a, v in (("cnn2", 10), ("res4", 20), ("res8", 30)):
        st = L["d"][a]
        assert st["raw_values"] == [v] * 5 and st["sd_ddof1"] == 0 and st["positive_count"] == 5 and st["degenerate"] is True
        assert st["ci95_t"] == [v, v] and st["ci975_t"] == [v, v] and st["ci95_cross_bootstrap"] == [v, v]
    for k, v in (("c", 20), ("u", 10), ("v", 10), ("r", 20)):
        assert L[k]["raw_values"] == [v] * 5 and L[k]["sd_ddof1"] == 0 and L[k]["ci95_cross_bootstrap"] == [v, v]
    assert (P["H1"]["label"], P["H2"]["label"]) == ("supported", "supported")
    assert set(P["direction_signal"].values()) == {"supported_signal"} and P["interaction_signal"] == "supported_signal"
    s = P["res4_sign_test"]
    assert (s["n_effective"], s["k_positive"], s["numerator"], s["denominator"]) == (5, 5, 1, 32) and s["p"] == 1 / 32
    m = an["endpoints"]["last_standard"]["model_metrics"]
    assert m["cnn2.n1"]["raw_values"] == [110] * 5 and m["cnn2.n3"]["raw_values"] == [100] * 5 and m["res8.n1"]["raw_values"] == [130] * 5
    rt = an["endpoints"]["last_standard"]["rates_steps"]["cnn2.n1"]
    assert rt["died_rate"]["mean"] == 1 and rt["won_rate"]["mean"] == 0 and rt["truncated_rate"]["mean"] == 0 and rt["steps_mean"]["mean"] == 100
    best = an["exploratory"]["best_minus_last"]
    assert all(st["raw_values"] == [0] * 5 and st["ci95_cross_bootstrap"] == [0, 0] for st in list(best["b"].values()) + list(best["g"].values()))


def test_F2_zero_interaction(cache, tmp_path_factory):
    an, _, _ = get(cache, tmp_path_factory, "F2", const_d(20, 20, 20))
    L, P = effects(an), an["primary_decisions"]
    for k in ("c", "u", "v", "r"):
        assert L[k]["raw_values"] == [0] * 5 and L[k]["ci95_t"] == [0, 0] and L[k]["ci95_cross_bootstrap"] == [0, 0]
    assert (P["H1"]["label"], P["H2"]["label"]) == ("supported", "refuted")
    assert set(P["direction_signal"].values()) == {"supported_signal"} and P["interaction_signal"] == "insufficient_evidence"
    assert P["res4_sign_test"]["p"] == 1 / 32


def test_F3_reversed_sign(cache, tmp_path_factory):
    an, _, _ = get(cache, tmp_path_factory, "F3", const_d(-10, -20, -30))
    L, P = effects(an), an["primary_decisions"]
    assert L["c"]["raw_values"] == [-20] * 5 and L["u"]["raw_values"] == [-10] * 5 and L["v"]["raw_values"] == [-10] * 5 and L["r"]["raw_values"] == [-20] * 5
    assert P["H1"]["label"] == "refuted" and P["H1"]["positive_gain_refuted"] is True and P["H2"]["label"] == "supported"
    assert set(P["direction_signal"].values()) == {"insufficient_evidence"} and P["interaction_signal"] == "supported_signal"
    s = P["res4_sign_test"]
    assert (s["n_effective"], s["k_positive"], s["numerator"], s["denominator"], s["p"]) == (5, 0, 32, 32, 1.0)
    assert all(L["d"][a]["positive_count"] == 0 and L["d"][a]["negative_count"] == 5 for a in ARCHS)


def test_F4_variance_and_boundaries(cache, tmp_path_factory):
    an, out, _ = get(cache, tmp_path_factory, "F4", const_d(10, [8, 9, 10, 11, 12], 20))
    L, P = effects(an), an["primary_decisions"]
    d4 = L["d"]["res4"]
    near(d4["mean"], 10)
    near(d4["sd_ddof1"], math.sqrt(2.5))
    near(d4["se"], 1 / math.sqrt(2))
    near(d4["ci95_t"][0], 8.036756838522442, 1e-11)
    near(d4["ci95_t"][1], 11.963243161477558, 1e-11)
    near(d4["ci975_t"][0], 7.528374762117939, 1e-11)
    near(d4["ci975_t"][1], 12.471625237882061, 1e-11)
    assert P["H1"]["label"] == "uncertain" and P["direction_signal"]["res4"] == "supported_signal"
    assert L["c"]["raw_values"] == [10] * 5 and P["H2"]["label"] == "uncertain" and P["interaction_signal"] == "supported_signal"
    assert L["u"]["raw_values"] == [-2, -1, 0, 1, 2] and L["u"]["positive_count"] == 2 and L["u"]["mean"] == 0
    assert L["v"]["raw_values"] == [12, 11, 10, 9, 8] and L["v"]["positive_count"] == 5 and L["v"]["mean"] == 10
    near(L["u"]["sd_ddof1"], math.sqrt(2.5))
    # bootstrap: per round d.res4* = 8 + (sum I)/5, u* = -2 + (sum I)/5, v* = 12 - (sum I)/5, c* = 10 -- compared round by round
    rng = np.random.Generator(np.random.PCG64(271828))
    rows = [line.split(",") for line in (out / "bootstrap_replicates.csv").read_text().splitlines()]
    head = rows[0]
    col = {k: head.index(k) for k in ("last_standard.d.res4", "last_standard.u", "last_standard.v", "last_standard.c")}
    for b in range(200):
        I = rng.integers(0, 5, size=5, dtype=np.int64, endpoint=False)
        rng.integers(0, 300, size=300, dtype=np.int64, endpoint=False)
        s = int(I.sum())
        near(float(rows[b + 1][col["last_standard.d.res4"]]), 8 + s / 5, 1e-12)
        near(float(rows[b + 1][col["last_standard.u"]]), -2 + s / 5, 1e-12)
        near(float(rows[b + 1][col["last_standard.v"]]), 12 - s / 5, 1e-12)
        near(float(rows[b + 1][col["last_standard.c"]]), 10, 1e-12)


def test_F5_zero_difference_sign_test(cache, tmp_path_factory):
    an, _, _ = get(cache, tmp_path_factory, "F5", {"cnn2": [0] * 5, "res4": [0, 1, 2, 3, -1], "res8": [0] * 5})
    d4, P = effects(an)["d"]["res4"], an["primary_decisions"]
    near(d4["mean"], 1)
    near(d4["sd_ddof1"], math.sqrt(2.5))
    assert (d4["positive_count"], d4["negative_count"], d4["zero_count"]) == (3, 1, 1)
    s = P["res4_sign_test"]
    assert (s["n_effective"], s["k_positive"], s["numerator"], s["denominator"], s["p"]) == (4, 3, 5, 16, 0.3125)
    assert P["H1"]["label"] == "refuted" and P["direction_signal"]["res4"] == "insufficient_evidence"


def test_F6_all_zero(cache, tmp_path_factory):
    an, _, _ = get(cache, tmp_path_factory, "F6", const_d(0, 0, 0))
    P = an["primary_decisions"]
    s = P["res4_sign_test"]
    assert (s["n_effective"], s["k_positive"], s["zero_count"], s["p"], s["status"]) == (0, 0, 5, 1.0, "no_effective_samples")
    assert (P["H1"]["label"], P["H2"]["label"]) == ("refuted", "refuted")
    assert set(P["direction_signal"].values()) == {"insufficient_evidence"} and P["interaction_signal"] == "insufficient_evidence"


def test_F8_degenerate_boundary_and_negative_interaction(cache, tmp_path_factory):
    an, _, _ = get(cache, tmp_path_factory, "F8", const_d(0, 10, -10))
    L, P = effects(an), an["primary_decisions"]
    assert L["d"]["res4"]["ci975_t"] == [10, 10] and P["H1"]["label"] == "uncertain"
    assert L["c"]["ci975_t"] == [-10, -10] and P["H2"]["label"] == "uncertain"
    assert P["direction_signal"] == {"cnn2": "insufficient_evidence", "res4": "supported_signal", "res8": "insufficient_evidence"}
    assert P["interaction_signal"] == "supported_signal" and L["u"]["raw_values"] == [10] * 5 and L["v"]["raw_values"] == [-20] * 5
    assert P["res4_sign_test"]["numerator"] == 1 and P["res4_sign_test"]["denominator"] == 32


def test_F7_shared_pairing_and_test_axis_resampling(cache, tmp_path_factory):
    """n=1 score = 100 + B_a + i + h(e), h = 1 for e >= 150.  d[a,s] = B_a + i + 1/2.  Bootstrap d* = B_a + (sum I)/5 + #{J>=150}/300."""
    B = {"cnn2": 10, "res4": 20, "res8": 30}
    an, out, _ = get(cache, tmp_path_factory, "F7", score_fn=lambda a, n, si, e: 100 if n == 3 else 100 + B[a] + si + (1 if e >= 150 else 0))
    L = effects(an)
    for a in ARCHS:
        st = L["d"][a]
        assert st["raw_values"] == [B[a] + i + 0.5 for i in range(5)]
        near(st["mean"], B[a] + 2.5)
        near(st["sd_ddof1"], math.sqrt(2.5))
        # closed-form scalar oracle: T_b = 60*sum(I) + #{J >= 150}; type-7 positions 249/250 and 9749/9750 are 384/385 and 1116/1116
        near(st["ci95_cross_bootstrap"][0], B[a] + 5133 / 4000, 1e-12)
        near(st["ci95_cross_bootstrap"][1], B[a] + 93 / 25, 1e-12)
    for k, v in (("c", 20), ("r", 20)):
        assert L[k]["raw_values"] == [v] * 5 and L[k]["ci95_cross_bootstrap"] == [v, v]
    assert L["u"]["raw_values"] == [10] * 5 and L["v"]["raw_values"] == [10] * 5 and L["u"]["ci95_cross_bootstrap"] == [10, 10]
    rows = [line.split(",") for line in (out / "bootstrap_replicates.csv").read_text().splitlines()]
    col = rows[0].index("last_standard.d.res4")
    near(float(rows[1][col]), 6931 / 300)  # replicate 0: sum I = 13, 151 test indices in the second half
    near(float(rows[2][col]), 6742 / 300)  # replicate 1: sum I = 10, 142
    cc = rows[0].index("last_standard.c")
    assert all(float(r[cc]) == 20.0 for r in rows[1:])


def test_independent_scalar_oracle_for_all_ten_thousand_rounds():
    """T_b = 60*sum(I) + #{J>=150} for every round, from the contracted stream, without loading any Y."""
    rng = np.random.Generator(np.random.PCG64(271828))
    T = []
    for _ in range(10000):
        I = rng.integers(0, 5, size=5, dtype=np.int64, endpoint=False)
        J = rng.integers(0, 300, size=300, dtype=np.int64, endpoint=False)
        T.append(60 * int(I.sum()) + int((J >= 150).sum()))
    Ts = sorted(T)
    assert (Ts[249], Ts[250], Ts[9749], Ts[9750]) == (384, 385, 1116, 1116)
    assert Fraction_eq((384 + 39 * 385), 40 * 300, 5133, 4000)


def Fraction_eq(a, b, c, d):
    return a * d == b * c


# ------------------------------------------------------------------ outputs
def test_outputs_are_complete_atomic_and_never_overwritten(cache, tmp_path_factory, tmp_path):
    an, out, st = get(cache, tmp_path_factory, "F1", const_d(10, 20, 30))
    assert sorted(p.name for p in out.iterdir()) == ["REPORT.md", "analysis.json", "bootstrap_indices.sha256", "bootstrap_replicates.csv", "input_manifest.json"]
    assert len((out / "bootstrap_replicates.csv").read_text().splitlines()) == 10001
    assert an["mode"] == "synthetic" and an["complete"] is True and an["analysis_spec_version"] == "0.3.2"
    assert an["parameters"]["bootstrap"]["index_stream_sha256"] == A.EXPECTED_INDEX_SHA and (out / "bootstrap_indices.sha256").read_text().startswith(A.EXPECTED_INDEX_SHA)
    assert an["integrity"]["initial_hash_pairs_equal"] == 15 and len(an["resource_records"]) == 30
    assert "SYNTHETIC DATA" in (out / "REPORT.md").read_text()
    for key in ("provenance", "integrity", "parameters", "endpoints", "primary_decisions", "exploratory", "resource_records", "deviations", "limitations"):
        assert key in an
    st0 = an["endpoints"]["last_standard"]["effects"]["d"]["res4"]
    for f in ("metric_id", "training_seeds", "raw_values", "mean", "sd_ddof1", "se", "positive_count", "zero_count", "negative_count", "ci95_t", "ci975_t",
              "ci95_cross_bootstrap", "degenerate", "source_metric_ids", "formula_id"):
        assert f in st0
    again = tmp_path / "again"
    with pytest.raises(A.AnalysisError, match="already exists"):
        A.analyze(st.manifest, st.runs, out, "synthetic")
    assert not list(out.parent.glob(".analysis_tmp_*"))


def test_best_minus_last_uses_the_same_resampling_and_hard_is_optional(tmp_path):
    # hard enabled: all 30 last/hard files, own endpoint; scores differ from standard so the endpoint is distinguishable
    st = Study(tmp_path / "p", d=const_d(10, 20, 30), hard=True, hard_d=const_d(1, 2, 3))
    an, _ = run(tmp_path, st)
    assert "last_hard" in an["endpoints"] and effects(an, "last_hard")["d"]["res4"]["raw_values"] == [2] * 5
    assert "last_hard" not in json.dumps(an["primary_decisions"])  # no second confirmatory verdict
    assert an["integrity"]["hard_enabled"] is True


def test_record_order_in_the_files_is_irrelevant(cache, tmp_path_factory, tmp_path):
    """Every file's 300 records are shuffled independently.  Scores depend on the test index (F7), so a script that aligned
    episodes by file row instead of by seed would pair different episodes and change the bootstrap intervals."""
    B_ = {"cnn2": 10, "res4": 20, "res8": 30}
    fn = lambda a, n, si, e: 100 if n == 3 else 100 + B_[a] + si + (1 if e >= 150 else 0)  # noqa: E731
    an, out, _ = get(cache, tmp_path_factory, "F7", score_fn=fn)
    st = Study(tmp_path / "shuf", score_fn=fn)
    rng = np.random.default_rng(5)
    for r in st.rows:
        for rel in ("last/standard.json", "best/standard.json"):
            st.edit_json(r["run_name"], rel, lambda d: d.update(records=[d["records"][i] for i in rng.permutation(300)]), reseal=False)
    st.reseal()
    an2, out2 = run(tmp_path, st)

    def strip(o):  # file hashes are allowed to differ; every number must be identical
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k != "sha256"}
        return [strip(v) for v in o] if isinstance(o, list) else o

    assert strip(an["endpoints"]) == strip(an2["endpoints"]) and an["primary_decisions"] == an2["primary_decisions"]
    assert an["exploratory"] == an2["exploratory"]
    assert (out / "bootstrap_replicates.csv").read_text() == (out2 / "bootstrap_replicates.csv").read_text()


# ------------------------------------------------------------------ malformed inputs E1-E13 (one fault each, seal re-hashed)
@pytest.fixture()
def study(tmp_path):
    return Study(tmp_path / "proj", d=const_d(10, 20, 30))


def fail(tmp_path, st, code, **expect):
    out = tmp_path / "out_fail"
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, out, "synthetic")
    assert e.value.obj["code"] == code, e.value.obj
    for k, v in expect.items():
        assert e.value.obj[k] == v or (v in str(e.value.obj[k])), (k, e.value.obj)
    assert not out.exists() and not list(tmp_path.glob(".analysis_tmp_*"))
    json.dumps(e.value.obj, allow_nan=False)  # the error object itself carries no NaN
    return e.value.obj


R0 = "prereg_res4_n1_s100"


def test_E1_missing_file(study, tmp_path):
    study.path(R0, "best/standard.json").unlink()
    fail(tmp_path, study, "E_MISSING_FILE", run_name=R0, path=f"{R0}/best/standard.json")


def test_E2_duplicate_seed(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][-1].update(seed=30298))
    fail(tmp_path, study, "E_DUPLICATE_SEED", seed=30298)


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "1e999"])
def test_E3_nonfinite_numbers(study, tmp_path, literal):
    p = study.path(R0, "last/standard.json")
    import re

    text = re.sub(r'"score": \d+,', f'"score": {literal},', p.read_text(), count=1)
    assert literal in text
    p.write_text(text)
    study.reseal()
    fail(tmp_path, study, "E_NONFINITE")


def test_E4_wrong_seed_set(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][-1].update(seed=30300))
    obj = fail(tmp_path, study, "E_TEST_SEED_SET")
    assert obj["expected"] == {"missing": [30299]} and obj["actual"] == {"unexpected": [30300]}


def test_E5_too_few_episodes(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"].pop())
    obj = fail(tmp_path, study, "E_EPISODE_COUNT")
    assert (obj["expected"], obj["actual"]) == (300, 299)


def test_E6_validation_seed_in_test_records(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update(seed=21000))
    fail(tmp_path, study, "E_VAL_TEST_MIXED", seed=21000)


@pytest.mark.parametrize("seed,part", [(40000, "smoke"), (20000, "equiv"), (5000, "old_val"), (10000, "old_test")])
def test_reserved_partitions_are_rejected(study, tmp_path, seed, part):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update(seed=seed))
    obj = fail(tmp_path, study, "E_RESERVED_SEED_MIXED", seed=seed)
    assert part.split("_")[0] in obj["message"]


def test_E7_missing_truncated_field(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][3].pop("truncated"))
    fail(tmp_path, study, "E_REQUIRED_FIELD", record_index=3)


def test_E8_impossible_win(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update(score=376, won=True, died=False, truncated=False))
    fail(tmp_path, study, "E_WON_SCORE")


@pytest.mark.parametrize("field,value,code", [("score", 378, "E_SCORE_RANGE"), ("steps", 0, "E_STEPS_RANGE")])
def test_E9_score_and_steps_ranges(study, tmp_path, field, value, code):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update({field: value}))
    fail(tmp_path, study, code)


def test_E10_incomplete_hard(tmp_path):
    st = Study(tmp_path / "proj", d=const_d(10, 20, 30), hard=True)
    st.path(R0, "last/hard.json").unlink()
    fail(tmp_path, st, "E_MISSING_FILE", path=f"{R0}/last/hard.json")


def test_E11_configuration_drift(study, tmp_path):
    study.edit_json(R0, "config.json", lambda d: d.update(tau=0.02))
    fail(tmp_path, study, "E_CONFIG_MISMATCH", run_name=R0)


def test_E12_sixteen_validations(study, tmp_path):
    study.edit_json(R0, "summary.json", lambda d: d["validation_steps"].append(300000))
    fail(tmp_path, study, "E_VALIDATION_SCHEDULE")


def test_E13_undeclared_hard(study, tmp_path):
    h = study.path(R0, "last/hard.json")
    h.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(study.path(R0, "last/standard.json"), h)
    fail(tmp_path, study, "E_UNDECLARED_HARD", run_name=R0)


# ---- further integrity checks beyond the numbered list
def test_hash_mismatch_when_a_sealed_file_changes_afterwards(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update(score=99), reseal=False)
    fail(tmp_path, study, "E_HASH_MISMATCH", run_name=R0)


def test_frozen_file_changed_after_the_freeze(study, tmp_path):
    (study.prereg / "requirements.lock").write_text("numpy==9\n")
    fail(tmp_path, study, "E_HASH_MISMATCH")


def test_extra_run_directory_and_wrong_matrix(study, tmp_path):
    (study.runs / "prereg_res4_n1_s999").mkdir()
    fail(tmp_path, study, "E_RUN_SET")


def test_matrix_that_is_not_the_registered_file(study, tmp_path):
    m = study.prereg / "matrix.csv"
    m.write_text(m.read_text().replace("prereg_res4_n1_s100", "prereg_res4_n1_s100 ", 1))
    study.write_manifest_and_seal()
    fail(tmp_path, study, "E_HASH_MISMATCH")


def test_initial_weights_must_match_for_n1_and_n3(study, tmp_path):
    study.edit_json("prereg_res4_n1_s103", "summary.json", lambda d: d.update(initial_state_dict_sha256="b" * 64))
    fail(tmp_path, study, "E_INIT_PAIR_MISMATCH")


def test_metadata_must_match_run_path_and_summary(study, tmp_path):
    study.edit_json(R0, "best/standard.json", lambda d: d["meta"].update(checkpoint_step=40000))
    fail(tmp_path, study, "E_METADATA_MISMATCH", run_name=R0)


def test_json_syntax_duplicate_keys_and_wrong_types(study, tmp_path):
    p = study.path(R0, "last/standard.json")
    p.write_text(p.read_text()[:100])
    study.reseal()
    fail(tmp_path, study, "E_JSON_PARSE")


def test_duplicate_json_key(study, tmp_path):
    p = study.path(R0, "summary.json")
    p.write_text(p.read_text().replace('"run_name"', '"actual_updates": 1, "actual_updates"', 1))
    study.reseal()
    fail(tmp_path, study, "E_JSON_DUPLICATE_KEY")


@pytest.mark.parametrize("fn,code", [
    (lambda d: d["records"][0].update(score="100"), "E_FIELD_TYPE"),
    (lambda d: d["records"][0].update(seed=30000.0), "E_FIELD_TYPE"),
    (lambda d: d["records"][0].update(died="true"), "E_FIELD_TYPE"),
    (lambda d: d["records"][0].update(died=False, truncated=True, steps=999), "E_END_FLAGS"),
    (lambda d: d["records"][0].update(died=False), "E_END_FLAGS"),
])
def test_record_level_type_and_end_flag_rules(study, tmp_path, fn, code):
    study.edit_json(R0, "last/standard.json", fn)
    fail(tmp_path, study, code, record_index=0)


def test_integer_valued_float_score_is_accepted(cache, tmp_path_factory, tmp_path):
    st = Study(tmp_path / "p", d=const_d(10, 20, 30))
    st.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update(score=110.0))
    an, _ = run(tmp_path, st)
    assert an["complete"] is True


def test_formal_mode_rejects_a_synthetic_manifest(study, tmp_path):
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(study.manifest, study.runs, tmp_path / "o", "formal")
    assert e.value.obj["code"] == "E_MANIFEST" and not (tmp_path / "o").exists()


def test_relative_project_root_needs_an_explicit_root(study, tmp_path):
    m = json.loads(study.manifest.read_text())
    m["project_root"] = "."
    study.manifest.write_text(json.dumps(m))
    study.reseal()  # the seal records the manifest hash
    with pytest.raises(A.AnalysisError, match="explicit --project-root"):
        A.analyze(study.manifest, study.runs, tmp_path / "o", "synthetic")
    an = A.analyze(study.manifest, study.runs, tmp_path / "o2", "synthetic", project_root=study.root)
    assert an["complete"] is True


def test_command_line_exit_code_and_stderr_json(study, tmp_path):
    study.path(R0, "best/standard.json").unlink()
    r = subprocess.run([sys.executable, str(Path(A.__file__)), "analyze", "--mode", "synthetic", "--manifest", str(study.manifest), "--input-root", str(study.runs),
                        "--output-dir", str(tmp_path / "cli_out")], capture_output=True, text=True)
    assert r.returncode == 2 and not (tmp_path / "cli_out").exists()
    obj = json.loads(r.stderr, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert obj["code"] == "E_MISSING_FILE" and obj["run_name"] == R0 and "REPORT" not in r.stdout


def test_the_script_never_reads_old_result_directories_or_checkpoints():
    import ast

    tree = ast.parse(Path(A.__file__).read_text())
    docstring = ast.get_docstring(tree, clean=False)
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value != docstring]
    for forbidden in ("results_gpu", "results/", ".pt", "train_log", "val_standard", "test_standard"):
        assert not [c for c in consts if forbidden in c], forbidden
    imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "torch" not in imports and "pacman_rl" not in imports  # numpy + stdlib only


def test_E9b_finite_non_integer_score_is_a_score_range_error(study, tmp_path):
    """The specification files a finite non-integer score (100.5) under E_SCORE_RANGE; strings and booleans stay E_FIELD_TYPE."""
    study.edit_json(R0, "last/standard.json", lambda d: d["records"][0].update(score=100.5))
    fail(tmp_path, study, "E_SCORE_RANGE", record_index=0)


# ------------------------------------------------------------------ error contract: containers, missing keys, float identities (P2-1)
def cli(study, tmp_path):
    r = subprocess.run([sys.executable, str(Path(A.__file__)), "analyze", "--mode", "synthetic", "--manifest", str(study.manifest), "--input-root", str(study.runs),
                        "--output-dir", str(tmp_path / "cli_out")], capture_output=True, text=True)
    assert not (tmp_path / "cli_out").exists() and "Traceback" not in r.stderr, r.stderr[-400:]
    return r.returncode, json.loads(r.stderr, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))


def test_cli_missing_records_key(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d.pop("records"))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_REQUIRED_FIELD" and obj["json_path"] == "$.records" and obj["run_name"] == R0


@pytest.mark.parametrize("fn,code,jp", [
    (lambda d: d.update(records={"a": 1}), "E_SCHEMA", "$.records"),
    (lambda d: d.update(meta=[1]), "E_SCHEMA", "$.meta"),
])
def test_cli_wrong_container_types_in_an_evaluation_file(study, tmp_path, fn, code, jp):
    study.edit_json(R0, "last/standard.json", fn)
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == code and obj["json_path"] == jp


def test_cli_frozen_files_must_be_an_object_and_path_fields_strings(study, tmp_path):
    m = json.loads(study.manifest.read_text())
    m["frozen_files"] = ["docs/prereg/matrix.csv"]
    study.manifest.write_text(json.dumps(m))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_SCHEMA" and obj["json_path"] == "$.frozen_files"
    m["frozen_files"] = {}
    m["config_path"] = 5
    study.manifest.write_text(json.dumps(m))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_FIELD_TYPE" and obj["json_path"] == "$.config_path"


def test_cli_float_identities_are_rejected(study, tmp_path):
    study.edit_json(R0, "config.json", lambda d: d.update(seed=100.0))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_FIELD_TYPE" and obj["json_path"] == "$.seed" and obj["run_name"] == R0


def test_cli_float_validation_step_is_rejected(study, tmp_path):
    study.edit_json(R0, "summary.json", lambda d: d["validation_steps"].__setitem__(0, 20000.0))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_FIELD_TYPE" and obj["json_path"] == "$.validation_steps[0]"


def test_cli_float_in_other_integer_fields(study, tmp_path):
    study.edit_json(R0, "last/standard.json", lambda d: d["meta"].update(train_seed=100.0))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_METADATA_MISMATCH"
    study.edit_json(R0, "last/standard.json", lambda d: d["meta"].update(train_seed=100))
    study.edit_json(R0, "summary.json", lambda d: d["replay"].update(size=100000.0))
    rc, obj = cli(study, tmp_path)
    assert rc == 2 and obj["code"] == "E_FIELD_TYPE"


def test_no_single_key_replacement_or_deletion_escapes_as_an_unwrapped_exception(study, tmp_path):
    """Property check: replace or delete every top-level key (and the nested meta / replay / checkpoints keys) of the manifest, the
    seal and the files of one run with values of the wrong type -- the analyzer must answer with an AnalysisError, never with a
    KeyError / TypeError / AttributeError (we do not catch generic exceptions to hide such defects)."""
    vals = [[], "x", 5, None, {}, 1.5]
    targets = [(study.manifest, []), (study.root / "results_prereg/evaluation_seal.json", [])]
    for rel in ("config.json", "summary.json", "last/standard.json", "best/standard.json"):
        targets.append((study.path(R0, rel), []))
    targets += [(study.path(R0, "last/standard.json"), ["meta"]), (study.path(R0, "summary.json"), ["replay"]), (study.path(R0, "summary.json"), ["checkpoints"])]
    escaped, n = [], 0
    for path, prefix in targets:
        original = path.read_text()
        d = json.loads(original)
        t = d
        for k in prefix:
            t = t[k]
        for i, key in enumerate(list(t)):
            for action in (vals[i % len(vals)], "__delete__"):
                dd = json.loads(original)
                tt = dd
                for k in prefix:
                    tt = tt[k]
                if action == "__delete__":
                    del tt[key]
                else:
                    tt[key] = action
                path.write_text(json.dumps(dd))
                if study.runs in path.parents:
                    study.reseal()  # run files: keep the seal consistent so the fault is reached; manifest / seal faults are tested as they are
                n += 1
                try:
                    A.analyze(study.manifest, study.runs, tmp_path / f"fz{n}", "synthetic")
                except A.AnalysisError:
                    pass
                except Exception as e:  # noqa: BLE001 - this IS the defect the test looks for
                    escaped.append(f"{path.name}{prefix}.{key} <- {action!r}: {type(e).__name__}")
                finally:
                    shutil.rmtree(tmp_path / f"fz{n}", ignore_errors=True)
        path.write_text(original)
        if study.runs in path.parents:
            study.reseal()
    assert n > 150 and not escaped, escaped[:8]


# ------------------------------------------------------------------ formal-mode gates (P2-2); the DATA are invented, only the labels are formal
def run_formal(tmp_path, st, name="formal_out"):
    out = tmp_path / name
    A.analyze(st.manifest, st.runs, out, "formal")
    return json.loads((out / "analysis.json").read_text()), out


def test_a_valid_formal_labelled_study_passes_all_gates(tmp_path):
    st = Study(tmp_path / "p", d=const_d(10, 20, 30), formal=True)
    an, out = run_formal(tmp_path, st)
    assert an["mode"] == "formal" and "FORMAL ANALYSIS" in (out / "REPORT.md").read_text()
    assert effects(an)["d"]["res4"]["raw_values"] == [20] * 5


def test_formal_mode_requires_both_texts_in_the_frozen_hashes(tmp_path):
    st = Study(tmp_path / "p", d=const_d(10, 20, 30), formal=True)
    m = json.loads(st.manifest.read_text())
    del m["frozen_files"]["docs/prereg/ANALYSIS_SPEC_v0.3.2.md"]
    st.manifest.write_text(json.dumps(m))
    st.reseal()
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, tmp_path / "o", "formal")
    assert e.value.obj["code"] == "E_MANIFEST" and "ANALYSIS_SPEC" in e.value.obj["message"] and not (tmp_path / "o").exists()
    # the synthetic mode of the same study does not demand them
    st2 = Study(tmp_path / "q", d=const_d(10, 20, 30))
    m2 = json.loads(st2.manifest.read_text())
    del m2["frozen_files"]["docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md"]
    st2.manifest.write_text(json.dumps(m2))
    st2.reseal()
    assert A.analyze(st2.manifest, st2.runs, tmp_path / "o2", "synthetic")["complete"] is True


def test_running_a_different_script_than_the_frozen_one_is_rejected(tmp_path, monkeypatch):
    st = Study(tmp_path / "p", d=const_d(10, 20, 30))
    other = tmp_path / "other_script.py"
    other.write_text(Path(A.__file__).read_text() + "\n# a modified copy\n")
    monkeypatch.setattr(A, "SCRIPT_PATH", other)
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, tmp_path / "o", "synthetic")
    assert e.value.obj["code"] == "E_HASH_MISMATCH" and "not the frozen one" in e.value.obj["message"] and not (tmp_path / "o").exists()


def test_a_draft_configuration_cannot_pose_as_formal_or_synthetic(tmp_path):
    st = Study(tmp_path / "p", d=const_d(10, 20, 30), formal=True)
    cfgp = st.prereg / "frozen_config_v0.3.2.json"
    cfg = json.loads(cfgp.read_text())
    cfg["status"] = "draft"
    cfgp.write_text(json.dumps(cfg))
    st.write_manifest_and_seal()  # hashes follow the edit: only the status is wrong
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, tmp_path / "o", "formal")
    assert e.value.obj["code"] == "E_CONFIG_MISMATCH" and e.value.obj["json_path"] == "$.status" and e.value.obj["actual"] == "draft"
    st2 = Study(tmp_path / "q", d=const_d(10, 20, 30))
    c2 = st2.prereg / "frozen_config_v0.3.2.json"
    d2 = json.loads(c2.read_text())
    d2["status"] = "frozen"  # a "frozen" configuration is not a synthetic one either
    c2.write_text(json.dumps(d2))
    st2.write_manifest_and_seal()
    with pytest.raises(A.AnalysisError) as e2:
        A.analyze(st2.manifest, st2.runs, tmp_path / "o2", "synthetic")
    assert e2.value.obj["code"] == "E_CONFIG_MISMATCH"
