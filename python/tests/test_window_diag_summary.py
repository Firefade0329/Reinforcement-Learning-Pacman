"""Central summary of the window records, their separate seal, and the isolation from the core analysis.

The 30 records are synthetic (the recorder fed with pseudo-random scripts for the real matrix rows); no training, evaluation or real result is
read.  Implementer and test author are the same AI model; expected values are hand-derived or recomputed with the standard library."""
import json
import math
import random
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest

from pacman_rl import window_diag as W

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
import window_diagnostics_summary as S  # noqa: E402
from prereg_fixture import Study  # noqa: E402

BUDGET = 400
ROWS = S.load_matrix()


def synthetic_doc(row, budget=BUDGET, seed_shift=0):
    rnd = random.Random(row["seed"] * 100 + row["n_step"] + seed_shift + (7 if row["arch"] == "res8" else 0))
    rec = W.WindowRecorder(2, row["n_step"], 0.99, budget)
    for t in range(budget // 2):
        rec.begin_batch(2 * t, 0.5, np.array([rnd.random() < 0.3, rnd.random() < 0.3]))
        for i in range(2):
            died = rnd.random() < 0.05
            trunc = (not died) and rnd.random() < 0.02
            rec.step(i, 0, -10.0 if died else 0.0, died, trunc, died, False)
    return rec.to_dict({"run_name": row["run_name"], "arch": row["arch"], "n_step": row["n_step"], "run_seed": row["seed"], "git_sha": "a" * 40})


def make_results(root: Path, mutate=None):
    for r in ROWS:
        d = root / "runs" / r["run_name"]
        d.mkdir(parents=True)
        doc = synthetic_doc(r)
        if mutate:
            mutate(r, doc)
        (d / S.DIAG).write_text(json.dumps(doc), encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    return make_results(tmp_path_factory.mktemp("diag"))


# ------------------------------------------------------------------ statistics
def test_two_runs_one_half_and_nine_tenths_have_mean_point_seven_sd_sqrt_point_08_and_pooled_five_sixths():
    s = S.ratio_summary([(1, 2), (9, 10)])
    assert s["k_defined"] == 2 and math.isclose(s["mean_of_defined"], 0.7, abs_tol=1e-15)
    assert math.isclose(s["sd_ddof1"], math.sqrt(0.08), abs_tol=1e-15) and math.isclose(s["sd_ddof1"], 0.282842712474619, abs_tol=1e-14)
    assert s["pooled"] == {"numerator": 10, "denominator": 12, "rate": 10 / 12, "status": "ok"}
    assert s["pooled"]["rate"] != s["mean_of_defined"]  # two different quantities, never merged


def test_zero_denominator_rules_and_k_of_five():
    s = S.ratio_summary([(1, 2), (0, 0), (3, 4), (0, 0), (0, 0)])
    assert s["k_defined"] == 2 and s["n_runs"] == 5 and s["mean_of_defined"] == 0.625 and s["per_run"][1]["rate"] is None
    assert math.isclose(s["sd_ddof1"], statistics.stdev([0.5, 0.75]), abs_tol=1e-15)
    one = S.ratio_summary([(1, 2), (0, 0)])
    assert one["k_defined"] == 1 and one["sd_ddof1"] is None and one["sd_status"] == "needs_at_least_2_defined_runs" and one["mean_of_defined"] == 0.5
    none = S.ratio_summary([(0, 0)] * 5)
    assert none["k_defined"] == 0 and none["mean_of_defined"] is None and none["mean_status"] == "no_defined_run" and none["pooled"]["rate"] is None
    json.dumps([s, one, none], allow_nan=False)


def test_value_summary_handles_missing_runs():
    v = S.value_summary([None, -9.9, -9.801, None])
    assert v["k_defined"] == 2 and math.isclose(v["mean_of_defined"], (-9.9 - 9.801) / 2, abs_tol=1e-12)


# ------------------------------------------------------------------ seal
def test_seal_lists_exactly_the_thirty_records_with_their_hashes_and_the_code_hashes(results):
    seal = S.build_seal(results, ROWS, BUDGET)
    assert seal["schema_version"] == "window-diagnostics-seal-1" and seal["runs"] == [r["run_name"] for r in ROWS] and len(seal["files"]) == 30
    assert set(seal["files"]) == {f"{r['run_name']}/window_diagnostics.json" for r in ROWS}
    assert all(seal["files"][k] == S.sha256_file(results / "runs" / k) for k in seal["files"])
    assert set(seal["code_sha256"]) == set(S.CODE_FILES) and seal["matrix_sha256"] == S.MATRIX_SHA256


def test_seal_refuses_missing_incomplete_or_mislabelled_records(tmp_path):
    root = make_results(tmp_path / "a")
    (root / "runs" / ROWS[3]["run_name"] / S.DIAG).unlink()
    with pytest.raises(S.DiagError, match="missing"):
        S.build_seal(root, ROWS, BUDGET)
    bad_integrity = make_results(tmp_path / "b", lambda r, d: d["integrity"].update(complete=False, errors=["x"]) if r["run_name"] == ROWS[5]["run_name"] else None)
    with pytest.raises(S.DiagError, match="integrity"):
        S.build_seal(bad_integrity, ROWS, BUDGET)
    mislabelled = make_results(tmp_path / "c", lambda r, d: d["meta"].update(arch="cnn2") if r["run_name"] == ROWS[2]["run_name"] else None)
    with pytest.raises(S.DiagError, match="meta.arch"):
        S.build_seal(mislabelled, ROWS, BUDGET)
    with pytest.raises(S.DiagError, match="transition_budget|collected"):
        S.build_seal(make_results(tmp_path / "d"), ROWS, 300_000)  # the files were made with 400 transitions


def test_summary_refuses_a_record_changed_after_sealing(results, tmp_path):
    root = tmp_path / "r"
    import shutil

    shutil.copytree(results, root)
    seal = S.build_seal(root, ROWS, BUDGET)
    f = root / "runs" / ROWS[0]["run_name"] / S.DIAG
    doc = json.loads(f.read_text())
    doc["pending_total"] += 1
    f.write_text(json.dumps(doc))
    with pytest.raises(S.DiagError, match="differs from the sealed hash"):
        S.summarize(root, seal, ROWS)
    seal2 = dict(seal, files={k: v for k, v in list(seal["files"].items())[:-1]})
    with pytest.raises(S.DiagError, match="exactly the 30"):
        S.summarize(root, seal2, ROWS)


# ------------------------------------------------------------------ the summary
def test_summary_per_configuration_matches_a_standard_library_recomputation(results):
    seal = S.build_seal(results, ROWS, BUDGET)
    out = S.summarize(results, seal, ROWS)
    assert out["descriptive_only"] is True and set(out["configs"]) == {f"{a}.n{n}" for a in ("cnn2", "res4", "res8") for n in (1, 3)}
    text = json.dumps(out, allow_nan=False)  # no NaN / Infinity
    assert "NaN" not in text
    docs = {r["run_name"]: json.loads((results / "runs" / r["run_name"] / S.DIAG).read_text()) for r in ROWS}
    for cfg, c in out["configs"].items():
        arch, n = cfg.split(".n")
        names = [r["run_name"] for r in sorted((r for r in ROWS if r["arch"] == arch and r["n_step"] == int(n)), key=lambda r: r["seed"])]
        assert c["run_names"] == names and c["training_seeds"] == [100, 101, 102, 103, 104]
        for g in c["run_level"]:
            assert g in ([f"h{h}" for h in range(1, int(n) + 1)] + ["all"])
        s = c["run_level"]["all"]["p_later_mismatch"]
        nums = [docs[nm]["rates"]["run"]["all"]["p_later_mismatch"] for nm in names]
        assert [p["numerator"] for p in s["per_run"]] == [x["numerator"] for x in nums]
        rates = [x["numerator"] / x["denominator"] for x in nums]
        assert math.isclose(s["mean_of_defined"], statistics.fmean(rates), abs_tol=1e-12) and math.isclose(s["sd_ddof1"], statistics.stdev(rates), abs_tol=1e-12)
        assert s["pooled"]["numerator"] == sum(x["numerator"] for x in nums) and s["pooled"]["denominator"] == sum(x["denominator"] for x in nums)
        if int(n) == 1:  # no later action exists: the h >= 2 figures are undefined in every run, not zero
            h2 = c["run_level"]["all"]["p_later_mismatch_hge2"]
            assert h2["k_defined"] == 0 and h2["mean_of_defined"] is None and h2["pooled"]["rate"] is None
        assert len(c["by_start_bin_all_h"]) == 15


def test_the_summary_script_reads_only_the_window_records_the_seal_and_the_matrix(results, tmp_path, monkeypatch):
    seen = []
    real_text, real_bytes = Path.read_text, Path.read_bytes
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (seen.append(self.name), real_text(self, *a, **k))[1])
    monkeypatch.setattr(Path, "read_bytes", lambda self: (seen.append(self.name), real_bytes(self))[1])
    seal = S.build_seal(results, ROWS, BUDGET)
    S.summarize(results, seal, ROWS)
    allowed = {S.DIAG, "matrix.csv", "window_diag.py", "window_diagnostics_summary.py"}  # the last two are hashed into the seal
    assert set(seen) <= allowed, set(seen) - allowed
    # a results directory that holds nothing but the records is enough
    assert not any(p.name in ("summary.json", "config.json", "best.pt", "last.pt") for p in results.rglob("*"))


def test_command_line_seal_then_summarize_and_never_overwrite(results, tmp_path, monkeypatch, capsys):
    import shutil

    root = tmp_path / "cli"
    shutil.copytree(results, root)
    monkeypatch.setattr(S, "BUDGET", BUDGET)
    assert S.main(["seal", "--results-dir", str(root)]) == 0
    assert S.main(["seal", "--results-dir", str(root)]) == 2  # sealed once
    assert S.main(["summarize", "--results-dir", str(root), "--out-dir", str(tmp_path / "out")]) == 0
    assert S.main(["summarize", "--results-dir", str(root), "--out-dir", str(tmp_path / "out")]) == 2
    summary = json.loads((tmp_path / "out" / "window_diagnostics_summary.json").read_text())
    assert summary["seal_sha256"] == S.sha256_file(root / "window_diagnostics_seal.json") and "p_value" not in json.dumps(summary)
    md = (tmp_path / "out" / "window_diagnostics_summary.md").read_text()
    assert "Not part of the H1 / H2 decision" in md and "cnn2.n1" in md
    err = capsys.readouterr().err.strip().splitlines()[-1]
    assert "error" in json.loads(err)


# ------------------------------------------------------------------ the core analysis does not notice the records
def strip_volatile(obj):
    if isinstance(obj, dict):
        # the two synthetic projects live in different directories, so the hashes of the manifest / seal that embed that path differ
        return {k: strip_volatile(v) for k, v in obj.items() if k not in ("utc", "project_root", "freeze_manifest_sha256", "evaluation_seal_sha256", "seal_sha256")}
    return [strip_volatile(v) for v in obj] if isinstance(obj, list) else obj


def test_core_analysis_output_is_identical_with_and_without_the_window_sidecar(tmp_path):
    def build(root):
        return Study(root / "proj", d={"cnn2": [10] * 5, "res4": [8, 9, 10, 11, 12], "res8": [20] * 5})

    plain, with_side = build(tmp_path / "plain"), build(tmp_path / "side")
    for r in ROWS:  # records next to the runs, a seal and a summary next to the evaluation seal
        (with_side.runs / r["run_name"] / S.DIAG).write_text(json.dumps(synthetic_doc(r)), encoding="utf-8")
    (with_side.root / "results_prereg" / "window_diagnostics_seal.json").write_text(json.dumps(S.build_seal(with_side.root / "results_prereg", ROWS, BUDGET)))
    out_a, out_b = tmp_path / "out_a", tmp_path / "out_b"
    A.analyze(plain.manifest, plain.runs, out_a, "synthetic")
    A.analyze(with_side.manifest, with_side.runs, out_b, "synthetic")
    a, b = (json.loads((o / "analysis.json").read_text()) for o in (out_a, out_b))
    assert strip_volatile(a) == strip_volatile(b)  # every H1 / H2 number and label, every statistic
    for name in ("REPORT.md", "bootstrap_replicates.csv", "bootstrap_indices.sha256"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), name
    files_b = json.loads((out_b / "input_manifest.json").read_text())["files"]
    assert not any("window_diagnostics" in k for k in files_b) and set(files_b) == set(json.loads((out_a / "input_manifest.json").read_text())["files"])
    assert "window" not in (out_b / "REPORT.md").read_text().lower()  # the report does not mention the sidecar either
