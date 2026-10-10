"""Complete hand-derived expectations for the valid synthetic fixtures F1-F6, F8 (every score, effect, count, interval and secondary
endpoint) and a fixture with a nonzero best-minus-last difference that checks the paired resampling of b, g and the best-based effects.

Expected numbers are written out by hand (constants) or derived in this file with plain Python from the contracted index stream (the
bootstrap oracle sorts the sums itself and interpolates type-7 positions by hand); nothing is taken from the analysis script's output."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
from prereg_fixture import ARCHS, Study  # noqa: E402

T95, T975 = 2.7764451051977944, 3.4954059325164377  # spec constants (df = 4)
R5 = math.sqrt(5)


def near(a, b, tol=1e-11):
    assert abs(a - b) <= tol, (a, b)


def d_of(cnn2, res4, res8):
    return {"cnn2": [cnn2] * 5 if not isinstance(cnn2, list) else cnn2, "res4": [res4] * 5 if not isinstance(res4, list) else res4,
            "res8": [res8] * 5 if not isinstance(res8, list) else res8}


# fixture -> (d per architecture, then by hand: per-seed raw values, mean, sd of each vector).  m[n1] = 100 + d, m[n3] = 100.
# d, c = d.res8 - d.cnn2, u = d.res4 - d.cnn2, v = d.res8 - d.res4, r = (100 + d.res8) - (100 + d.cnn2) = c.
SQ = math.sqrt(2.5)
CASES = {
    "F1": dict(d=d_of(10, 20, 30), vec={"d.cnn2": [10] * 5, "d.res4": [20] * 5, "d.res8": [30] * 5, "c": [20] * 5, "u": [10] * 5, "v": [10] * 5, "r": [20] * 5},
               sd={"d.res4": 0, "c": 0}, pos={"d.cnn2": (5, 0, 0), "c": (5, 0, 0)}),
    "F2": dict(d=d_of(20, 20, 20), vec={"d.cnn2": [20] * 5, "d.res4": [20] * 5, "d.res8": [20] * 5, "c": [0] * 5, "u": [0] * 5, "v": [0] * 5, "r": [0] * 5},
               sd={"d.res4": 0, "c": 0}, pos={"d.cnn2": (5, 0, 0), "c": (0, 5, 0)}),
    "F3": dict(d=d_of(-10, -20, -30), vec={"d.cnn2": [-10] * 5, "d.res4": [-20] * 5, "d.res8": [-30] * 5, "c": [-20] * 5, "u": [-10] * 5, "v": [-10] * 5, "r": [-20] * 5},
               sd={"d.res4": 0, "c": 0}, pos={"d.cnn2": (0, 0, 5), "c": (0, 0, 5)}),
    "F4": dict(d=d_of(10, [8, 9, 10, 11, 12], 20), vec={"d.cnn2": [10] * 5, "d.res4": [8, 9, 10, 11, 12], "d.res8": [20] * 5, "c": [10] * 5, "u": [-2, -1, 0, 1, 2],
                                                         "v": [12, 11, 10, 9, 8], "r": [10] * 5}, sd={"d.res4": SQ, "u": SQ, "v": SQ, "c": 0}, pos={"d.res4": (5, 0, 0), "u": (2, 1, 2), "v": (5, 0, 0)}),
    "F5": dict(d=d_of(0, [0, 1, 2, 3, -1], 0), vec={"d.cnn2": [0] * 5, "d.res4": [0, 1, 2, 3, -1], "d.res8": [0] * 5, "c": [0] * 5, "u": [0, 1, 2, 3, -1],
                                                     "v": [0, -1, -2, -3, 1], "r": [0] * 5}, sd={"d.res4": SQ, "u": SQ, "v": SQ, "c": 0}, pos={"d.res4": (3, 1, 1), "v": (1, 1, 3)}),
    "F6": dict(d=d_of(0, 0, 0), vec={k: [0] * 5 for k in ("d.cnn2", "d.res4", "d.res8", "c", "u", "v", "r")}, sd={"d.res4": 0, "c": 0}, pos={"d.res4": (0, 5, 0)}),
    "F8": dict(d=d_of(0, 10, -10), vec={"d.cnn2": [0] * 5, "d.res4": [10] * 5, "d.res8": [-10] * 5, "c": [-10] * 5, "u": [10] * 5, "v": [-20] * 5, "r": [-10] * 5},
               sd={"d.res4": 0, "c": 0}, pos={"d.res4": (5, 0, 0), "c": (0, 0, 5)}),
}


@pytest.fixture(scope="module")
def analyses(tmp_path_factory):
    out = {}
    for name, c in CASES.items():
        base = tmp_path_factory.mktemp(name)
        st = Study(base / "proj", d=c["d"])
        A.analyze(st.manifest, st.runs, base / "o", "synthetic")
        out[name] = (json.loads((base / "o" / "analysis.json").read_text()), base / "o")
    return out


def stats_of(vals):
    m = sum(vals) / 5
    sd = math.sqrt(sum((x - m) ** 2 for x in vals) / 4)
    return m, sd


@pytest.mark.parametrize("name", list(CASES))
def test_every_effect_vector_has_its_hand_derived_values_and_intervals(analyses, name):
    an, _ = analyses[name]
    c = CASES[name]
    E = an["endpoints"]["last_standard"]["effects"]
    got = {"d.cnn2": E["d"]["cnn2"], "d.res4": E["d"]["res4"], "d.res8": E["d"]["res8"], "c": E["c"], "u": E["u"], "v": E["v"], "r": E["r"]}
    for key, vals in c["vec"].items():
        st = got[key]
        m, sd = stats_of(vals)
        assert st["raw_values"] == vals and st["training_seeds"] == [100, 101, 102, 103, 104]
        near(st["mean"], m)
        near(st["sd_ddof1"], sd)
        near(st["se"], sd / R5)
        assert (st["positive_count"], st["zero_count"], st["negative_count"]) == (sum(x > 0 for x in vals), sum(x == 0 for x in vals), sum(x < 0 for x in vals))
        near(st["ci95_t"][0], m - T95 * sd / R5)
        near(st["ci95_t"][1], m + T95 * sd / R5)
        near(st["ci975_t"][0], m - T975 * sd / R5)
        near(st["ci975_t"][1], m + T975 * sd / R5)
        assert st["degenerate"] is (sd == 0)
    for key, trip in c["pos"].items():
        assert (got[key]["positive_count"], got[key]["zero_count"], got[key]["negative_count"]) == trip


@pytest.mark.parametrize("name", list(CASES))
def test_model_metrics_and_configuration_summaries_are_the_hand_sums(analyses, name):
    an, _ = analyses[name]
    d = CASES[name]["d"]
    ep = an["endpoints"]["last_standard"]
    for a in ARCHS:
        n1, n3 = ep["model_metrics"][f"{a}.n1"], ep["model_metrics"][f"{a}.n3"]
        assert n1["raw_values"] == [100 + x for x in d[a]] and n3["raw_values"] == [100] * 5
        assert n1["integer_numerators"] == [300 * (100 + x) for x in d[a]] and n3["integer_numerators"] == [30000] * 5
        m, sd = stats_of([100 + x for x in d[a]])
        near(ep["config_summaries"][f"{a}.n1"]["mean"], m)
        near(ep["config_summaries"][f"{a}.n1"]["sd_ddof1"], sd)
        near(ep["config_summaries"][f"{a}.n3"]["mean"], 100)
        assert ep["config_summaries"][f"{a}.n1"]["source_metric_id"] == f"last_standard.m.{a}.n1"
        rt = ep["rates_steps"][f"{a}.n1"]  # every episode is a death after 100 steps in the fixtures
        assert (rt["died_rate"]["mean"], rt["won_rate"]["mean"], rt["truncated_rate"]["mean"], rt["steps_mean"]["mean"]) == (1, 0, 0, 100)
        assert rt["died_rate"]["integer_numerators"] == [300] * 5 and rt["steps_mean"]["integer_numerators"] == [30000] * 5


@pytest.mark.parametrize("name", list(CASES))
def test_secondary_endpoints_are_reported_and_best_equals_last_when_the_checkpoints_are_the_same(analyses, name):
    an, _ = analyses[name]
    assert set(an["endpoints"]) == {"last_standard", "best_standard"}  # hard not enabled -> not run, not an empty endpoint
    last, best = an["endpoints"]["last_standard"], an["endpoints"]["best_standard"]
    for k in ("d", "c", "u", "v", "r"):
        pairs = [(last["effects"][k][a], best["effects"][k][a]) for a in ARCHS] if k == "d" else [(last["effects"][k], best["effects"][k])]
        for lo, bo in pairs:
            assert lo["raw_values"] == bo["raw_values"] and lo["ci95_cross_bootstrap"] == bo["ci95_cross_bootstrap"]
            assert bo["metric_id"].startswith("best_standard.") and lo["metric_id"].startswith("last_standard.")
    bl = an["exploratory"]["best_minus_last"]
    for st in list(bl["b"].values()) + list(bl["g"].values()):
        assert st["raw_values"] == [0] * 5 and st["ci95_t"] == [0, 0] and st["ci95_cross_bootstrap"] == [0, 0] and st["zero_count"] == 5
    assert all(st["best_selected_steps"] == [20000] * 5 for st in bl["b"].values())
    assert all(st["direction_of_mean"] == "zero" for st in bl["g"].values())


# ------------------------------------------------------------------ independent bootstrap oracle
def stream_sums(rounds):
    """(S_b, K_b) per round from the contracted stream: S = sum of the 5 resampled training-seed indices, K = #{J >= 150} among the 300
    resampled test indices."""
    rng = np.random.Generator(np.random.PCG64(271828))
    S, K = [], []
    for _ in range(rounds):
        I = rng.integers(0, 5, size=5, dtype=np.int64, endpoint=False)
        J = rng.integers(0, 300, size=300, dtype=np.int64, endpoint=False)
        S.append(int(I.sum()))
        K.append(int((J >= 150).sum()))
    return S, K


def type7(values, p):
    """Type-7 quantile by hand: sorted position p*(n-1), linear interpolation (no numpy.quantile)."""
    xs = sorted(values)
    pos = p * (len(xs) - 1)
    lo = math.floor(pos)
    frac = pos - lo
    return xs[lo] if frac == 0 else xs[lo] + frac * (xs[lo + 1] - xs[lo])


@pytest.fixture(scope="module")
def sums():
    return stream_sums(10000)


def test_F4_bootstrap_intervals_of_all_four_vectors_from_the_contracted_stream(analyses, sums):
    """d.res4* = 8 + S/5, u* = -2 + S/5, v* = 12 - S/5, c* = 10 (spec 8.2): intervals are hand quantiles of these 10000 values."""
    an, _ = analyses["F4"]
    S, _ = sums
    E = an["endpoints"]["last_standard"]["effects"]
    for key, fn in (("d", lambda s: 8 + s / 5), ("u", lambda s: -2 + s / 5), ("v", lambda s: 12 - s / 5)):
        vals = [fn(s) for s in S]
        st = E["d"]["res4"] if key == "d" else E[key]
        near(st["ci95_cross_bootstrap"][0], type7(vals, 0.025), 1e-12)
        near(st["ci95_cross_bootstrap"][1], type7(vals, 0.975), 1e-12)
    assert E["c"]["ci95_cross_bootstrap"] == [10, 10]


# ------------------------------------------------------------------ nonzero best - last
B_ = {"cnn2": 10, "res4": 20, "res8": 30}


def last_fn(a, n, si, e):  # as F7: n=1 gains B_a + seed index + h(e), n=3 is flat
    return 100 if n == 3 else 100 + B_[a] + si + (1 if e >= 150 else 0)


def best_fn(a, n, si, e):  # best = last + 7 + h(e) for n=1, last + 2 for n=3  (h(e) = 1 for e >= 150)
    return last_fn(a, n, si, e) + ((7 + (1 if e >= 150 else 0)) if n == 1 else 2)


@pytest.fixture(scope="module")
def nonzero_bl(tmp_path_factory, sums):
    base = tmp_path_factory.mktemp("bl")
    st = Study(base / "proj", score_fn=last_fn, best_fn=best_fn, best_step_fn=lambda a, n, si: 60000 + 20000 * si)
    A.analyze(st.manifest, st.runs, base / "o", "synthetic")
    rows = [line.split(",") for line in (base / "o" / "bootstrap_replicates.csv").read_text().splitlines()]
    return json.loads((base / "o" / "analysis.json").read_text()), rows


def test_b_g_and_best_effects_have_their_hand_derived_per_seed_values(nonzero_bl):
    an, _ = nonzero_bl
    bl = an["exploratory"]["best_minus_last"]
    for a in ARCHS:
        b1, b3, g = bl["b"][f"{a}.n1"], bl["b"][f"{a}.n3"], bl["g"][a]
        assert b1["raw_values"] == [7.5] * 5 and b1["mean"] == 7.5 and b1["sd_ddof1"] == 0 and b1["positive_count"] == 5  # 7 + mean(h) = 7.5
        assert b3["raw_values"] == [2.0] * 5 and b3["ci95_t"] == [2.0, 2.0]
        assert g["raw_values"] == [5.5] * 5 and g["direction_of_mean"] == "positive"  # (7.5) - (2)
        assert b1["best_selected_steps"] == [60000, 80000, 100000, 120000, 140000]
    best = an["endpoints"]["best_standard"]["effects"]
    for a in ARCHS:  # d_best = d_last + g: last d = B + si + 0.5
        assert best["d"][a]["raw_values"] == [B_[a] + i + 6.0 for i in range(5)]
    assert best["c"]["raw_values"] == [20.0] * 5 and best["u"]["raw_values"] == [10.0] * 5


def test_b_g_and_best_effects_resample_the_same_training_and_test_indices(nonzero_bl, sums):
    """Per round: b[n1]* = 7 + K/300, b[n3]* = 2, g* = 5 + K/300 (K = #{J >= 150}); d_best* = B_a + S/5 + 5 + 2K/300, d_last* = B_a + S/5 + K/300.
    A resampling that drew separate indices for best and last (unpaired) would break these identities round by round."""
    an, rows = nonzero_bl
    S, K = sums
    col = {k: rows[0].index(k) for k in rows[0]}
    for b in range(300):
        for a in ARCHS:
            near(float(rows[b + 1][col[f"best_minus_last.b.{a}.n1"]]), 7 + K[b] / 300, 1e-12)
            assert float(rows[b + 1][col[f"best_minus_last.b.{a}.n3"]]) == 2.0
            near(float(rows[b + 1][col[f"best_minus_last.g.{a}"]]), 5 + K[b] / 300, 1e-12)
            near(float(rows[b + 1][col[f"best_standard.d.{a}"]]), B_[a] + S[b] / 5 + 5 + 2 * K[b] / 300, 1e-12)
            near(float(rows[b + 1][col[f"last_standard.d.{a}"]]), B_[a] + S[b] / 5 + K[b] / 300, 1e-12)
    # the intervals are the hand quantiles of the same per-round values
    bl = an["exploratory"]["best_minus_last"]
    for a in ARCHS:
        vals = [7 + k / 300 for k in K]
        near(bl["b"][f"{a}.n1"]["ci95_cross_bootstrap"][0], type7(vals, 0.025), 1e-12)
        near(bl["b"][f"{a}.n1"]["ci95_cross_bootstrap"][1], type7(vals, 0.975), 1e-12)
        gv = [5 + k / 300 for k in K]
        near(bl["g"][a]["ci95_cross_bootstrap"][0], type7(gv, 0.025), 1e-12)
        near(bl["g"][a]["ci95_cross_bootstrap"][1], type7(gv, 0.975), 1e-12)
        assert bl["b"][f"{a}.n3"]["ci95_cross_bootstrap"] == [2.0, 2.0]
