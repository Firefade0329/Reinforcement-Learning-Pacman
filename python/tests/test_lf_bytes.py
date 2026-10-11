"""Every file that is hashed, sealed, format-checked or compared byte for byte is written with LF only, whatever the platform's text mode does.

Each producer runs under the `windows_text_mode` fixture (conftest.py), which makes every text write that does not give `newline` produce CRLF, as Windows does.  The
produced bytes must then contain no CR: a producer that relies on the platform default would write CRLF here and fail on Linux as well.  (bootstrap_replicates.csv is the one
documented exception: the csv module's fixed "\\r\\n" row terminator, identical on every platform.)  Same-AI implementer and test author; synthetic material only."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

import pacman_rl.dqn as dqn
from pacman_rl import evaluate as ev
from pacman_rl import prereg as PR
from pacman_rl import seal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402
import prereg_analysis as A  # noqa: E402
import test_seal as TS  # noqa: E402
import test_window_diag_summary as TW  # noqa: E402
import window_diagnostics_summary as S  # noqa: E402
from prereg_fixture import Study  # noqa: E402
from test_freeze_identity import ANALYSIS_REL, CFG_REL, LOCK_REL, Repo, prepare  # noqa: E402

BINARY = (".pt", ".npz")


def assert_lf(path: Path):
    data = Path(path).read_bytes()
    assert data and b"\r" not in data, f"{path.name} contains CR bytes (count {data.count(b'\r')})"


def all_text_files(root: Path):
    return [p for p in Path(root).rglob("*") if p.is_file() and p.suffix not in BINARY and ".lock" not in p.parts]


# ------------------------------------------------------------------ the training / evaluation / sealing chain
@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """Tiny in-process trainings (the subprocess of run_matrix would not see the simulation), finalize, pre-test manifest, final evaluation,
    evaluation seal, an archived attempt and a smoke report -- all under CRLF text mode."""
    import conftest

    mp = pytest.MonkeyPatch()
    for var in runner.FORBIDDEN_ENV:
        mp.delenv(var, raising=False)
    conftest.install_windows_text_mode(mp)
    mp.setattr(PR, "load_freeze", lambda path=None: TS.FREEZE)
    mp.setitem(ev.SEED_SETS, "prereg_test", list(range(50000, 50005)))
    results = tmp_path_factory.mktemp("lf_chain")
    for i, row in enumerate(TS.ROWS):
        cfg = PR.train_config(row, TS.FREEZE, **TS.TINY)
        run_dir = results / "runs" / row["run_name"]
        dqn.train(cfg, run_dir, log=lambda *_: None, resume=False, window_diagnostics=(i == 0))
        assert runner.finalize(run_dir, row["run_name"], cfg, 1, row["order"]) == []
    script = results / "analysis.py"
    script.write_bytes(b"# placeholder analysis script\n")
    pre = results / "m.json"
    seal.write_manifest(pre, TS.build(results, script))
    TS.final(results, script, unseal=True)
    fm = results / "freeze_manifest.json"
    fm.write_bytes(b"{}")
    runner.make_evaluation_seal(results, pre, fm, rows=TS.ROWS, freeze=TS.FREEZE, allow_unfrozen=True)
    (results / "runs" / "scratch_run").mkdir()
    (results / "runs" / "scratch_run" / "x.txt").write_bytes(b"x")
    runner.archive_incomplete(results, "scratch_run", "synthetic reason")
    smoke_dir = tmp_path_factory.mktemp("lf_smoke")
    runner.smoke("quick", "cpu", smoke_dir, steps=1200, pairs=[("cnn2", 1, 900)], resume_check=False)
    mp.undo()  # the simulation and the throw-away partition must not leak into the other tests of this module
    return results, smoke_dir


def test_every_file_of_a_run_is_written_with_lf_only(chain):
    results, smoke_dir = chain
    run = results / "runs" / TS.ROWS[0]["run_name"]
    expected = ["config.json", "train_config.json", "summary.json", "train_log.jsonl", "code_version.json", "environment.json", "run_complete.json", "window_diagnostics.json",
                "last/standard.json", "best/standard.json"]
    for rel in expected:
        assert_lf(run / rel)
    assert not (run / "window_diagnostics.partial.json").exists()


def test_every_file_of_the_final_evaluation_and_the_seals_is_lf_only(chain):
    results, _ = chain
    for name in ("m.json", "unseal_log.jsonl", "final_eval_index.json", "final_eval_environment.json", "evaluation_seal.json", "attempts.jsonl"):
        assert_lf(results / name)


def test_nothing_text_in_the_results_tree_or_the_smoke_directory_has_a_carriage_return(chain):
    results, smoke_dir = chain
    bad = [p.relative_to(results).as_posix() for p in all_text_files(results) if p.name != "stdout.log" and b"\r" in p.read_bytes() and p.name != "analysis.py"]
    bad += [p.relative_to(smoke_dir).as_posix() for p in all_text_files(smoke_dir) if p.name != "stdout.log" and b"\r" in p.read_bytes()]
    assert bad == []
    assert (smoke_dir / "smoke_report_quick.json").is_file()


# ------------------------------------------------------------------ freeze-manifest command and preflight log
def point_cli_at(repo, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", repo.root)
    monkeypatch.setattr(PR, "FREEZE_FILE", repo.root / CFG_REL)
    monkeypatch.setattr(PR, "ROOT", repo.root)


def test_freeze_manifest_command_writes_lf_only(tmp_path, monkeypatch, windows_text_mode):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    prepare(r)
    point_cli_at(r, monkeypatch)
    out = tmp_path / "freeze_manifest.json"
    assert runner.main(["freeze-manifest", "--analysis-script", ANALYSIS_REL, "--dependency-lock", LOCK_REL, "--out", str(out)]) == 0
    assert_lf(out)
    assert json.loads(out.read_text())["complete"] is True


def test_preflight_log_and_environment_evidence_are_lf_only(tmp_path, monkeypatch, windows_text_mode):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    r.freeze()
    point_cli_at(r, monkeypatch)
    monkeypatch.setattr(PR, "load_freeze", lambda path=None: r.cfg)
    monkeypatch.setattr(runner, "execute", lambda *a, **k: "done")
    assert runner.main(["run", "--workers", "2", "--results-dir", str(r.root / "results_prereg")]) == 0
    assert_lf(r.root / "results_prereg" / "preflight_log.jsonl")
    res = r.root / "results_prereg"
    runner.save_final_eval_environment(res, r.cfg, {"head": r.git("rev-parse", "HEAD")}, root=r.root)
    assert_lf(res / "final_eval_environment.json")


# ------------------------------------------------------------------ the diagnostic summary and its seal
def test_diagnostic_seal_and_summary_are_lf_only(tmp_path, windows_text_mode):
    repo = TW.FrozenRepo(tmp_path / "fr")
    results = TW.make_results(tmp_path / "res", repo.F)
    import shutil

    root = tmp_path / "cli"
    shutil.copytree(results, root)
    ident = ["--freeze-manifest", str(repo.manifest), "--freeze-commit", repo.F, "--project-root", str(repo.root)]
    S.BUDGET = TW.BUDGET
    try:
        assert S.main(["seal", "--results-dir", str(root), *ident]) == 0
        assert S.main(["summarize", "--results-dir", str(root), "--out-dir", str(tmp_path / "out"), *ident]) == 0
    finally:
        S.BUDGET = 300_000
    assert_lf(root / "window_diagnostics_seal.json")
    assert_lf(tmp_path / "out" / "window_diagnostics_summary.json")
    assert_lf(tmp_path / "out" / "window_diagnostics_summary.md")


def test_recorder_snapshot_writer_is_lf_only(tmp_path, windows_text_mode):
    from pacman_rl import window_diag as W

    rec = W.WindowRecorder(1, 3, 0.99, 100)
    W.write_atomic(tmp_path / "d.json", rec.to_dict({}))
    assert_lf(tmp_path / "d.json")


# ------------------------------------------------------------------ the analysis outputs
def test_analysis_outputs_are_lf_only_and_the_csv_has_the_csv_modules_fixed_row_terminator(tmp_path, windows_text_mode):
    st = Study(tmp_path / "p", d={"cnn2": [10] * 5, "res4": [20] * 5, "res8": [30] * 5})
    out = tmp_path / "out"
    A.analyze(st.manifest, st.runs, out, "synthetic")
    for name in ("analysis.json", "REPORT.md", "bootstrap_indices.sha256", "input_manifest.json"):
        assert_lf(out / name)
    csv_bytes = (out / "bootstrap_replicates.csv").read_bytes()
    assert csv_bytes.count(b"\r\n") == 10001 and csv_bytes.replace(b"\r\n", b"").count(b"\n") == 0 and b"\r" not in csv_bytes.replace(b"\r\n", b"")  # fixed on every platform
