"""Central summary of the window records, their separate seal, and the isolation from the core analysis.

The 30 records are synthetic (the recorder fed with pseudo-random scripts for the real matrix rows); no training, evaluation or real result is
read.  Implementer and test author are the same AI model; expected values are hand-derived or recomputed with the standard library."""
import json
import math
import random
import shutil
import statistics
import subprocess
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


REPO = Path(__file__).resolve().parents[2]


def synthetic_doc(row, F="f" * 40, budget=BUDGET, seed_shift=0):
    rnd = random.Random(row["seed"] * 100 + row["n_step"] + seed_shift + (7 if row["arch"] == "res8" else 0))
    rec = W.WindowRecorder(8, row["n_step"], 0.99, budget)
    rec.hook_attached, rec.hook_emitted = True, 0  # as if the real replay had verified every emission (the wiring tests cover the real hook)
    for t in range(budget // 8):
        rec.begin_batch(8 * t, 0.5, np.array([rnd.random() < 0.3 for _ in range(8)]))
        for i in range(8):
            died = rnd.random() < 0.05
            trunc = (not died) and rnd.random() < 0.02
            rec.step(i, 0, -10.0 if died else 0.0, died, trunc, died, False)
    rec.hook_emitted = rec.emitted
    rec._expected.clear()
    return rec.to_dict({"run_name": row["run_name"], "arch": row["arch"], "n_step": row["n_step"], "run_seed": row["seed"], "git_sha": F})


class FrozenRepo:
    """A throwaway repository: C = the diagnostic code (copies of the real files) + a placeholder python tree, F = C + the freeze manifest that freezes the two code files."""

    def __init__(self, root: Path):
        self.root = Path(root)
        for rel in S.CODE_FILES:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, self.root / rel)
        (self.root / ".gitignore").write_text("results_prereg/\n", newline="\n")
        (self.root / "docs" / "prereg").mkdir(parents=True)
        self.git("init", "-q")
        self.C = self.commit("C")
        self.write_manifest()
        self.F = self.commit("F")
        self.manifest = self.root / "docs/prereg/freeze_manifest.json"

    def git(self, *a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false", *a], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)
        return self.git("rev-parse", "HEAD")

    def write_manifest(self, **over):
        m = {"schema_version": "prereg-freeze-1", "synthetic": False, "complete": True, "spec_version": "0.3.2", "code_commit": self.C,
             "frozen_files": {rel: S.sha256_file(self.root / rel) for rel in S.CODE_FILES}}
        m.update(over)
        (self.root / "docs/prereg/freeze_manifest.json").write_text(json.dumps(m, indent=1, sort_keys=True), newline="\n")

    def context(self, F=None):
        return S.freeze_context(self.manifest, self.root, F or self.F)


def make_results(root: Path, F, mutate=None):
    for r in ROWS:
        d = root / "runs" / r["run_name"]
        d.mkdir(parents=True)
        doc = synthetic_doc(r, F)
        if mutate:
            mutate(r, doc)
        (d / S.DIAG).write_text(json.dumps(doc), encoding="utf-8", newline="\n")
    return root


@pytest.fixture(scope="module")
def frozen(tmp_path_factory):
    repo = FrozenRepo(tmp_path_factory.mktemp("frozen_repo"))
    res = make_results(repo.root / "results_prereg", repo.F)
    return repo, res, repo.context()


@pytest.fixture(scope="module")
def results(frozen):
    return frozen[1]


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
def test_seal_lists_exactly_the_thirty_records_with_hashes_the_frozen_identity_and_the_code_hashes(frozen):
    repo, results, freeze = frozen
    seal = S.build_seal(results, ROWS, freeze, BUDGET)
    assert seal["schema_version"] == "window-diagnostics-seal-1" and seal["runs"] == [r["run_name"] for r in ROWS] and len(seal["files"]) == 30
    assert set(seal["files"]) == {f"{r['run_name']}/window_diagnostics.json" for r in ROWS}
    assert all(seal["files"][k] == S.sha256_file(results / "runs" / k) for k in seal["files"])
    assert set(seal["code_sha256"]) == set(S.CODE_FILES) and seal["matrix_sha256"] == S.MATRIX_SHA256
    assert {k: seal[k] for k in ("code_commit", "freeze_commit", "freeze_manifest_sha256")} == {"code_commit": repo.C, "freeze_commit": repo.F,
                                                                                              "freeze_manifest_sha256": S.sha256_file(repo.manifest)}
    assert seal["code_sha256"] == {rel: S.sha256_file(repo.root / rel) for rel in S.CODE_FILES} == json.loads(repo.manifest.read_text())["frozen_files"]


def test_seal_refuses_missing_incomplete_or_mislabelled_records(frozen, tmp_path):
    repo, _, freeze = frozen
    root = make_results(tmp_path / "a", repo.F)
    (root / "runs" / ROWS[3]["run_name"] / S.DIAG).unlink()
    with pytest.raises(S.DiagError, match="missing"):
        S.build_seal(root, ROWS, freeze, BUDGET)
    bad_integrity = make_results(tmp_path / "b", repo.F, lambda r, d: d["integrity"].update(complete=False, errors=["x"]) if r["run_name"] == ROWS[5]["run_name"] else None)
    with pytest.raises(S.DiagError, match="integrity"):
        S.build_seal(bad_integrity, ROWS, freeze, BUDGET)
    mislabelled = make_results(tmp_path / "c", repo.F, lambda r, d: d["meta"].update(arch="cnn2") if r["run_name"] == ROWS[2]["run_name"] else None)
    with pytest.raises(S.DiagError, match="meta.arch"):
        S.build_seal(mislabelled, ROWS, freeze, BUDGET)
    with pytest.raises(S.DiagError, match="transition_budget|collected"):
        S.build_seal(make_results(tmp_path / "d", repo.F), ROWS, freeze, 300_000)  # the files were made with 400 transitions


def one_bad(frozen, tmp_path, mutate):
    repo, _, freeze = frozen
    target = ROWS[7]["run_name"]
    root = make_results(tmp_path / "x", repo.F, lambda r, d: mutate(d) if r["run_name"] == target else None)
    return root, freeze, target


def test_a_single_record_with_the_wrong_git_sha_is_refused(frozen, tmp_path):
    root, freeze, target = one_bad(frozen, tmp_path, lambda d: d["meta"].update(git_sha="e" * 40))
    with pytest.raises(S.DiagError, match=rf"{target}: meta.git_sha .* the freeze commit F"):
        S.build_seal(root, ROWS, freeze, BUDGET)


def test_a_record_that_was_not_verified_against_the_real_replay_is_refused(frozen, tmp_path):
    root, freeze, target = one_bad(frozen, tmp_path, lambda d: d["integrity"].update(verified_against_replay=False))
    with pytest.raises(S.DiagError, match=rf"{target}: the recorder was not verified against the real replay"):
        S.build_seal(root, ROWS, freeze, BUDGET)


@pytest.mark.parametrize("edit,message", [
    (lambda d: d.update(definition_version="2"), "header definition_version"),
    (lambda d: d.update(definition_version=1), "header definition_version"),
    (lambda d: d.update(counting_source="sampled"), "header counting_source"),
    (lambda d: d.update(indicator="q_value_gap"), "header indicator"),
    (lambda d: d.update(n_envs=4), "header n_envs"),
    (lambda d: d.update(gamma=0.9), "header gamma"),
    (lambda d: d.update(bin_size=10000), "header bin_size"),
    (lambda d: d.update(descriptive_only=False), "header descriptive_only"),
    (lambda d: d["totals"].update(collected_transitions=399), "collected_transitions"),
])
def test_a_wrong_fixed_header_or_budget_field_is_refused(frozen, tmp_path, edit, message):
    root, freeze, target = one_bad(frozen, tmp_path, edit)
    with pytest.raises(S.DiagError, match=message):
        S.build_seal(root, ROWS, freeze, BUDGET)


def test_a_non_finite_or_overflowing_number_anywhere_in_a_record_is_refused(frozen, tmp_path):
    repo, _, freeze = frozen
    for literal in ("NaN", "Infinity", "1e999"):
        root = make_results(tmp_path / f"x{len(literal)}", repo.F)
        f = root / "runs" / ROWS[4]["run_name"] / S.DIAG
        f.write_text(f.read_text().replace('"descriptive_only": true', f'"descriptive_only": true, "extra_value": {literal}', 1), newline="\n")
        with pytest.raises(S.DiagError, match="non-finite|unreadable"):
            S.build_seal(root, ROWS, freeze, BUDGET)


def test_summary_refuses_a_record_changed_after_sealing(frozen, tmp_path):
    repo, results, freeze = frozen
    root = tmp_path / "r"
    shutil.copytree(results, root)
    seal = S.build_seal(root, ROWS, freeze, BUDGET)
    f = root / "runs" / ROWS[0]["run_name"] / S.DIAG
    doc = json.loads(f.read_text())
    doc["pending_total"] += 1
    f.write_text(json.dumps(doc), newline="\n")
    with pytest.raises(S.DiagError, match="differs from the sealed hash"):
        S.summarize(root, seal, ROWS, freeze, BUDGET)
    seal2 = dict(seal, files={k: v for k, v in list(seal["files"].items())[:-1]})
    with pytest.raises(S.DiagError, match="exactly the 30"):
        S.summarize(root, seal2, ROWS, freeze, BUDGET)


# ------------------------------------------------------------------ the frozen identity (C4)
def test_freeze_context_accepts_the_valid_state_and_names_c_f_and_the_manifest(frozen):
    repo, _, freeze = frozen
    assert freeze["code_commit"] == repo.C and freeze["freeze_commit"] == repo.F and freeze["freeze_manifest_sha256"] == S.sha256_file(repo.manifest)


def fresh_repo(tmp_path):
    return FrozenRepo(tmp_path / "fr")


def test_wrong_external_f_or_a_moved_head_is_refused(tmp_path):
    repo = fresh_repo(tmp_path)
    with pytest.raises(S.DiagError, match="not the external freeze commit F"):
        repo.context("e" * 40)
    with pytest.raises(S.DiagError, match="40-hex"):
        repo.context("short")
    repo.git("commit", "-q", "--allow-empty", "-m", "later")
    with pytest.raises(S.DiagError, match="not the external freeze commit F"):
        repo.context(repo.F)


def test_dirty_tree_changed_code_or_non_permitted_f_files_are_refused(tmp_path):
    repo = fresh_repo(tmp_path)
    (repo.root / ".gitignore").write_text("results_prereg/\n# dirty\n", newline="\n")
    with pytest.raises(S.DiagError, match="uncommitted changes"):
        repo.context()
    (repo.root / ".gitignore").write_text("results_prereg/\n", newline="\n")
    code = repo.root / S.CODE_FILES[0]
    code.write_text(code.read_text() + "\n# changed after the freeze\n", newline="\n")
    with pytest.raises(S.DiagError, match="differs from the frozen hash"):
        repo.context()


def test_manifest_defects_are_refused(tmp_path):
    repo = fresh_repo(tmp_path)
    for over, message in (({"complete": False}, "not a complete formal"), ({"synthetic": True}, "not a complete formal"), ({"code_commit": "x"}, "full code_commit"),
                          ({"frozen_files": {S.CODE_FILES[0]: "ab" * 32, S.CODE_FILES[1]: "cd" * 32}}, "differs from the frozen hash"),
                          ({"frozen_files": {S.CODE_FILES[0]: S.sha256_file(repo.root / S.CODE_FILES[0])}}, "does not freeze")):
        repo.write_manifest(**over)
        with pytest.raises(S.DiagError, match=message):
            repo.context()


def test_c_that_is_not_an_ancestor_or_f_with_a_changed_python_tree_is_refused(tmp_path):
    repo = fresh_repo(tmp_path)
    repo.git("checkout", "-q", "-b", "side")
    repo.git("commit", "-q", "--allow-empty", "-m", "side")
    side = repo.git("rev-parse", "HEAD")
    repo.git("checkout", "-q", "-")
    repo.write_manifest(code_commit=side)
    repo.F = repo.commit("F with a manifest naming a non-ancestor C")
    with pytest.raises(S.DiagError, match="not an ancestor"):
        repo.context()
    repo2 = FrozenRepo(tmp_path / "fr2")
    (repo2.root / "python" / "other.py").parent.mkdir(exist_ok=True)
    (repo2.root / "python" / "other.py").write_text("x = 1\n", newline="\n")
    repo2.F = repo2.commit("python changed in F")
    with pytest.raises(S.DiagError, match="python/ tree"):
        repo2.context()


def test_seal_f_wrong_or_sealed_code_hashes_not_matching_the_frozen_ones_are_refused_at_summarize(frozen, tmp_path):
    repo, results, freeze = frozen
    root = tmp_path / "r"
    shutil.copytree(results, root)
    seal = S.build_seal(root, ROWS, freeze, BUDGET)
    S.summarize(root, seal, ROWS, freeze, BUDGET)  # the valid seal passes
    with pytest.raises(S.DiagError, match="freeze_commit"):
        S.summarize(root, {**seal, "freeze_commit": "e" * 40}, ROWS, freeze, BUDGET)
    with pytest.raises(S.DiagError, match="freeze_manifest_sha256"):
        S.summarize(root, {**seal, "freeze_manifest_sha256": "ab" * 32}, ROWS, freeze, BUDGET)
    with pytest.raises(S.DiagError, match="code_commit"):
        S.summarize(root, {**seal, "code_commit": "e" * 40}, ROWS, freeze, BUDGET)
    bad_code = dict(seal["code_sha256"])
    bad_code[S.CODE_FILES[0]] = "ab" * 32  # sealed hash different from the frozen / current code
    with pytest.raises(S.DiagError, match="sealed code hashes"):
        S.summarize(root, {**seal, "code_sha256": bad_code}, ROWS, freeze, BUDGET)


def test_a_record_with_the_wrong_f_is_refused_by_summarize_even_when_the_seal_hash_matches(frozen, tmp_path):
    repo, _, freeze = frozen
    root = make_results(tmp_path / "x", repo.F, lambda r, d: d["meta"].update(git_sha="e" * 40) if r["run_name"] == ROWS[1]["run_name"] else None)
    f = root / "runs" / ROWS[1]["run_name"] / S.DIAG
    seal = {"schema_version": S.SEAL_SCHEMA, "matrix_sha256": S.MATRIX_SHA256, "runs": [r["run_name"] for r in ROWS], "transition_budget": BUDGET, "descriptive_only": True,
            "files": {f"{r['run_name']}/{S.DIAG}": S.sha256_file(root / "runs" / r["run_name"] / S.DIAG) for r in ROWS},
            "code_commit": freeze["code_commit"], "freeze_commit": freeze["freeze_commit"], "freeze_manifest_sha256": freeze["freeze_manifest_sha256"],
            "code_sha256": dict(freeze["frozen_code_sha256"])}  # a hand-made seal that blessed the bad record
    assert f.is_file()
    with pytest.raises(S.DiagError, match="meta.git_sha"):
        S.summarize(root, seal, ROWS, freeze, BUDGET)


# ------------------------------------------------------------------ the summary
def test_summary_per_configuration_matches_a_standard_library_recomputation(frozen):
    repo, results, freeze = frozen
    seal = S.build_seal(results, ROWS, freeze, BUDGET)
    out = S.summarize(results, seal, ROWS, freeze, BUDGET)
    assert out["identity"]["freeze_commit"] == repo.F and out["definition_version"] == "1"
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


def test_the_summary_script_reads_only_the_window_records_the_seal_and_the_matrix(frozen, tmp_path, monkeypatch):
    repo, results, freeze = frozen
    seen = []
    real_text, real_bytes = Path.read_text, Path.read_bytes
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (seen.append(self.name), real_text(self, *a, **k))[1])
    monkeypatch.setattr(Path, "read_bytes", lambda self: (seen.append(self.name), real_bytes(self))[1])
    seal = S.build_seal(results, ROWS, freeze, BUDGET)
    S.summarize(results, seal, ROWS, freeze, BUDGET)
    allowed = {S.DIAG, "matrix.csv", "window_diag.py", "window_diagnostics_summary.py"}  # the last two are hashed into the seal; git is a subprocess
    assert set(seen) <= allowed, set(seen) - allowed
    # a results directory that holds nothing but the records is enough
    assert not any(p.name in ("summary.json", "config.json", "best.pt", "last.pt") for p in results.rglob("*"))


def test_command_line_seal_then_summarize_and_never_overwrite(frozen, tmp_path, monkeypatch, capsys):
    repo, results, freeze = frozen
    root = tmp_path / "cli"
    shutil.copytree(results, root)
    monkeypatch.setattr(S, "BUDGET", BUDGET)
    ident = ["--freeze-manifest", str(repo.manifest), "--freeze-commit", repo.F, "--project-root", str(repo.root)]
    assert S.main(["seal", "--results-dir", str(root), *ident]) == 0
    assert S.main(["seal", "--results-dir", str(root), *ident]) == 2  # sealed once
    assert S.main(["summarize", "--results-dir", str(root), "--out-dir", str(tmp_path / "out"), *ident]) == 0
    assert S.main(["summarize", "--results-dir", str(root), "--out-dir", str(tmp_path / "out"), *ident]) == 2
    assert S.main(["summarize", "--results-dir", str(root), "--out-dir", str(tmp_path / "out2"), "--freeze-manifest", str(repo.manifest), "--freeze-commit", "e" * 40,
                   "--project-root", str(repo.root)]) == 2  # a wrong external F publishes nothing
    assert not (tmp_path / "out2").exists()
    summary = json.loads((tmp_path / "out" / "window_diagnostics_summary.json").read_text())
    assert summary["seal_sha256"] == S.sha256_file(root / "window_diagnostics_seal.json") and "p_value" not in json.dumps(summary)
    assert summary["identity"] == {"code_commit": repo.C, "freeze_commit": repo.F, "freeze_manifest_sha256": S.sha256_file(repo.manifest)}
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


def test_core_analysis_output_is_identical_with_and_without_the_window_sidecar(frozen, tmp_path):
    repo, fresults, freeze = frozen
    def build(root):
        return Study(root / "proj", d={"cnn2": [10] * 5, "res4": [8, 9, 10, 11, 12], "res8": [20] * 5})

    plain, with_side = build(tmp_path / "plain"), build(tmp_path / "side")
    for r in ROWS:  # records next to the runs, a seal next to the evaluation seal
        (with_side.runs / r["run_name"] / S.DIAG).write_text((fresults / "runs" / r["run_name"] / S.DIAG).read_text(), encoding="utf-8", newline="\n")
    (with_side.root / "results_prereg" / "window_diagnostics_seal.json").write_text(json.dumps(S.build_seal(fresults, ROWS, freeze, BUDGET)), newline="\n")
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


def test_the_summary_scripts_mirror_of_the_freeze_materials_equals_the_packages():
    sys.path.insert(0, str(REPO / "python"))
    from pacman_rl import provenance as P

    assert set(S.FREEZE_MATERIALS) == set(P.FREEZE_MATERIALS)
