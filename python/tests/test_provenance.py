"""Provenance of a run: canonical weight hashes, initial-weight equality across n_step, the privacy-safe
environment record, the code-version record, the de-duplicated final validation and the extra summary fields."""
import getpass
import inspect
import json
import os
import platform
import socket
import subprocess
import sys
import textwrap
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
import torch

import pacman_rl.dqn as dqn
from pacman_rl import provenance as P
from pacman_rl.dqn import TrainConfig, build_initial_models, train

REPO = Path(__file__).resolve().parents[2]
ARCHS = ("cnn2", "res4", "res8")
SEEDS = (100, 101, 102, 103, 104)


def tiny(**kw):
    base = dict(arch="mlp", total_env_steps=640, learn_start=64, eval_every=160, n_envs=4, buffer=2000, batch=8, seed=3, threads=1)
    base.update(kw)
    return TrainConfig(**base)


# ------------------------------------------------------------------ canonical hash
def test_state_hash_is_canonical():
    m = torch.nn.Linear(3, 2)
    h = P.state_hash(m)
    sd = m.state_dict()
    assert P.state_hash(dict(reversed(list(sd.items())))) == h  # key order does not matter
    assert P.state_hash(m) == h and len(h) == 64
    m2 = torch.nn.Linear(3, 2)
    m2.load_state_dict(sd)
    assert P.state_hash(m2) == h
    with torch.no_grad():
        m2.weight[0, 0] += 1e-7
    assert P.state_hash(m2) != h  # a single changed value
    assert P.state_hash({k: v.double() for k, v in sd.items()}) != h  # dtype is part of the hash
    assert P.state_hash({"weight": sd["weight"].reshape(3, 2), "bias": sd["bias"]}) != h  # shape is part of the hash


def test_state_hash_ignores_checkpoint_metadata(tmp_path):
    m = torch.nn.Linear(3, 2)
    torch.save({"state_dict": m.state_dict(), "cfg": {"a": 1}, "note": "x"}, tmp_path / "a.pt")
    torch.save({"state_dict": m.state_dict(), "cfg": {"a": 2}, "extra": list(range(100))}, tmp_path / "b.pt")
    assert P.file_sha256(tmp_path / "a.pt") != P.file_sha256(tmp_path / "b.pt")  # serialised files differ ...
    ha, hb = (P.state_hash(torch.load(tmp_path / f"{n}.pt", weights_only=False)["state_dict"]) for n in "ab")
    assert ha == hb == P.state_hash(m)  # ... the weights' canonical hash does not


# ------------------------------------------------------------------ initial weights
@pytest.mark.parametrize("arch", ARCHS + ("mlp",))
def test_initial_weights_equal_for_n1_and_n3_all_seed_pairs(arch):
    """15 (architecture, seed) pairs for the preregistered matrix (+ mlp): n_step does not touch the initial weights; the
    target is an exact but separate copy; torch's RNG ends in the same state."""
    for seed in SEEDS:
        res = {}
        for n in (1, 3):
            online, target = build_initial_models(tiny(arch=arch, seed=seed, n_step=n), torch.device("cpu"))
            res[n] = (P.state_hash(online), P.state_hash(target), torch.get_rng_state().clone())
            assert res[n][0] == res[n][1]
            assert all(a.data_ptr() != b.data_ptr() for a, b in zip(online.parameters(), target.parameters()))
        assert res[1][0] == res[3][0]
        assert torch.equal(res[1][2], res[3][2])


def test_nothing_else_consumes_torch_rng_between_seeding_and_construction():
    """Seed, build the bare model by hand: the same weights as build_initial_models (so no hidden RNG use in between)."""
    from pacman_rl.models import build_model

    for arch in ARCHS:
        cfg = tiny(arch=arch, seed=100)
        torch.manual_seed(cfg.seed)
        bare = P.state_hash(build_model(cfg.arch, cfg.width, cfg.dueling, dqn.in_ch(cfg)))
        assert P.state_hash(build_initial_models(cfg, torch.device("cpu"))[0]) == bare
    assert P.state_hash(build_initial_models(tiny(arch="cnn2", seed=100), torch.device("cpu"))[0]) != \
        P.state_hash(build_initial_models(tiny(arch="cnn2", seed=101), torch.device("cpu"))[0])  # the seed does matter


def test_train_logs_the_initial_hash_and_it_matches_for_n1_n3(tmp_path):
    rows = {}
    for n in (1, 3):
        run = tmp_path / f"n{n}"
        train(tiny(arch="cnn2", seed=100, n_step=n, total_env_steps=96, eval_every=48), run, log=lambda *_: None)
        log = [json.loads(x) for x in (run / "train_log.jsonl").read_text().splitlines()]
        assert log[0]["type"] == "init" and log[0]["online_hash"] == log[0]["target_hash"]
        rows[n] = log[0]
    assert rows[1]["online_hash"] == rows[3]["online_hash"]
    expected = P.state_hash(build_initial_models(tiny(arch="cnn2", seed=100), torch.device("cpu"))[0])
    assert rows[1]["online_hash"] == expected


# ------------------------------------------------------------------ environment.json
def test_environment_info_is_an_allowlist_without_identifying_information():
    info = P.environment_info(torch.device("cpu"))
    assert set(info) == set(P.ENV_KEYS)
    text = json.dumps(info)
    forbidden = {socket.gethostname(), getpass.getuser(), platform.node(), str(Path.home()), os.getcwd(), str(REPO),
                 platform.processor(), platform.machine()} - {"", None}
    for f in forbidden:
        assert f not in text, f"environment info leaks {f!r}"
    assert not any(c in text for c in ("\\", "C:", "/home", "/root", "/Users"))


def test_train_writes_environment_and_code_version_without_paths(tmp_path):
    run = tmp_path / "run"
    train(tiny(), run, log=lambda *_: None)
    env = json.loads((run / "environment.json").read_text())
    assert set(env) == set(P.ENV_KEYS) and env["device_type"] == "cpu" and env["gpu_name"] is None and env["torch_threads"] == 1
    cv = json.loads((run / "code_version.json").read_text())
    assert set(cv) == {"git_sha", "git_dirty", "git_diff_sha256", "python_tree_sha256", "files"}
    blob = (run / "environment.json").read_text() + (run / "code_version.json").read_text()
    for f in {socket.gethostname(), getpass.getuser(), str(tmp_path), str(REPO), str(Path.home())} - {""}:
        assert f not in blob


# ------------------------------------------------------------------ code_version
def _git(cwd, *a):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], cwd=cwd, check=True, capture_output=True)


def test_code_version_tracks_sha_dirtiness_and_tree_contents(tmp_path):
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "m.py").write_text("x = 1\n", newline="\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "matrix.csv").write_text("a,b\n", newline="\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "c")
    v = P.code_version(tmp_path, {"docs/matrix.csv": "", "docs/missing.json": ""})
    assert len(v["git_sha"]) == 40 and v["git_dirty"] is False and v["git_diff_sha256"] is None
    assert v["files"]["docs/matrix.csv"] == P.file_sha256(tmp_path / "docs" / "matrix.csv") and v["files"]["docs/missing.json"] is None
    (tmp_path / "python" / "m.py").write_text("x = 2\n", newline="\n")
    d = P.code_version(tmp_path)
    assert d["git_sha"] == v["git_sha"] and d["git_dirty"] is True and d["git_diff_sha256"]
    assert d["python_tree_sha256"] != v["python_tree_sha256"]  # contents, not just the commit
    assert P.code_version(tmp_path / "nope")["git_sha"] is None  # not a repository: recorded as unknown


# ------------------------------------------------------------------ de-duplicated final validation
def test_final_validation_is_not_repeated_and_selection_is_unchanged(tmp_path):
    """Budget ends on an evaluation boundary: one validation per boundary (15 at 300000/20000).  The old behaviour
    (an extra 'final' validation of the same weights) is rebuilt by patching the source: best.pt, last.pt and the
    selected step must be identical."""
    cfg = tiny(arch="cnn2")
    a = tmp_path / "dedup"
    sa = train(cfg, a, log=lambda *_: None)
    rows = [json.loads(x) for x in (a / "train_log.jsonl").read_text().splitlines()]
    evals = [r["env_steps"] for r in rows if r["type"] == "eval"]
    assert evals == [160, 320, 480, 640] and evals == sorted(set(evals))
    # old behaviour: unconditional final validation
    src = textwrap.dedent(inspect.getsource(dqn.train))
    anchor = '    if last_eval_step != env_steps:  # the budget ended on an evaluation boundary: that evaluation is the final one\n        do_eval("final")'
    assert anchor in src
    ns = dict(vars(dqn))
    exec(compile(src.replace(anchor, '    do_eval("final")'), "<old train>", "exec"), ns)
    b = tmp_path / "old"
    sb = ns["train"](cfg, b, log=lambda *_: None)
    old_evals = [json.loads(x)["env_steps"] for x in (b / "train_log.jsonl").read_text().splitlines() if '"eval"' in x]
    assert old_evals == [160, 320, 480, 640, 640]  # the duplicate the change removes
    for k in ("best_val_score", "best_env_steps", "updates"):
        assert sa[k] == sb[k]
    for f in ("best.pt", "last.pt"):
        ha = P.state_hash(torch.load(a / f, weights_only=False)["state_dict"])
        hb = P.state_hash(torch.load(b / f, weights_only=False)["state_dict"])
        assert ha == hb, f


def test_final_validation_still_runs_when_the_budget_is_not_a_multiple(tmp_path):
    run = tmp_path / "run"
    train(tiny(total_env_steps=600, eval_every=160), run, log=lambda *_: None)
    evals = [json.loads(x)["env_steps"] for x in (run / "train_log.jsonl").read_text().splitlines() if '"eval"' in x]
    assert evals == [160, 320, 480, 600]


def test_best_is_the_first_strict_maximum_of_the_validation_rows(tmp_path):
    run = tmp_path / "run"
    s = train(tiny(arch="cnn2", seed=5), run, log=lambda *_: None)
    ev = [(json.loads(x)["env_steps"], json.loads(x)["val_score"]) for x in (run / "train_log.jsonl").read_text().splitlines() if '"eval"' in x]
    best = max(v for _, v in ev)
    assert s["best_val_score"] == best and s["best_env_steps"] == next(st for st, v in ev if v == best)
    assert torch.load(run / "best.pt", weights_only=False)["env_steps"] == s["best_env_steps"]


# ------------------------------------------------------------------ extra summary fields
def test_summary_records_replay_size_episodes_and_finiteness(tmp_path):
    run = tmp_path / "run"
    s = train(tiny(), run, log=lambda *_: None)
    assert s["env_steps"] == 640 and 0 < s["replay_size"] <= 640 and s["episodes_started"] >= 4
    assert s["weights_finite"] is True and s["nonfinite_loss_updates_this_session"] == 0
    assert set(P.peak_memory()) <= set(s)
    rows = [json.loads(x) for x in (run / "train_log.jsonl").read_text().splitlines()]
    assert all(r.get("weights_finite") is True for r in rows if r["type"] == "eval")
    # n-step bookkeeping: with n=3 at most (n-1) pending samples per environment are not stored yet
    assert 640 - 2 * 4 <= s["replay_size"] <= 640


def test_replay_size_differs_by_at_most_the_unflushed_tail_between_n1_and_n3(tmp_path):
    sizes = {}
    for n in (1, 3):
        sizes[n] = train(tiny(n_step=n), tmp_path / f"n{n}", log=lambda *_: None)["replay_size"]
    assert 0 <= sizes[1] - sizes[3] <= 2 * 4


# ------------------------------------------------------------------ peak memory (Windows pseudo-handle regression)
class _Fn:
    """Stand-in for a ctypes foreign function.  Like the real thing on 64-bit Windows, a function whose ``argtypes`` were never
    declared converts Python ints to a plain C int and overflows on the 64-bit pseudo-handle; declared ``argtypes`` pass it on."""

    def __init__(self, impl):
        self.impl, self.argtypes, self.restype = impl, None, None

    def __call__(self, *args):
        if self.argtypes is None:
            for a in args:
                if isinstance(a, int) and not -(2**31) <= a < 2**31:
                    raise OverflowError("int too long to convert")
        else:
            assert len(args) == len(self.argtypes)
        return self.impl(*args)


def _fake_windows(ws_mb=321, commit_mb=654, ok=True):
    import ctypes
    from ctypes import wintypes

    k32, psapi = type("Kernel32", (), {})(), type("Psapi", (), {})()
    k32.GetCurrentProcess = _Fn(lambda: 2**64 - 1 if k32.GetCurrentProcess.restype is wintypes.HANDLE else -1)  # (HANDLE)-1 read as c_void_p

    def info(handle, ref, cb):
        if ok:
            ref._obj.PeakWorkingSetSize, ref._obj.PeakPagefileUsage = ws_mb * 2**20, commit_mb * 2**20
        return 1 if ok else 0

    psapi.GetProcessMemoryInfo = _Fn(info)
    return ctypes, wintypes, k32, psapi


def _legacy_windows_peak(apis):
    """The statements of the implementation before the fix, verbatim: restype set, argtypes NOT declared."""
    ctypes, wintypes, k32, psapi = apis

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    return psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)


def test_the_stand_in_reproduces_the_reported_overflow_with_the_old_statements():
    """Documents the failure on Linux: old code + a function without argtypes + the 64-bit pseudo-handle -> OverflowError."""
    with pytest.raises(OverflowError, match="int too long to convert"):
        _legacy_windows_peak(_fake_windows())


def test_windows_peak_declares_signatures_and_reports_positive_values():
    out = P._windows_peak(_fake_windows(321, 654))
    assert out == {"peak_working_set_mb": 321.0, "peak_commit_mb": 654.0}


def test_windows_peak_reports_a_false_return_instead_of_zeros():
    with pytest.raises(OSError, match="GetProcessMemoryInfo returned FALSE"):
        P._windows_peak(_fake_windows(ok=False))


def test_peak_memory_goes_through_the_windows_path_on_windows(monkeypatch):
    monkeypatch.setattr(P.platform, "system", lambda: "Windows")
    monkeypatch.setattr(P, "_windows_apis", lambda: _fake_windows(111, 222))
    out = P.peak_memory()
    assert out["peak_working_set_mb"] == 111.0 and out["peak_commit_mb"] == 222.0 and out["peak_memory_error"] is None


def test_a_failure_is_recorded_not_swallowed(monkeypatch):
    monkeypatch.setattr(P.platform, "system", lambda: "Windows")
    monkeypatch.setattr(P, "_windows_apis", lambda: _fake_windows(ok=False))
    out = P.peak_memory()
    assert out["peak_working_set_mb"] is None and out["peak_commit_mb"] is None
    assert out["peak_memory_error"].startswith("process memory: OSError: GetProcessMemoryInfo returned FALSE")
    monkeypatch.setattr(P, "_windows_apis", lambda: (_ for _ in ()).throw(OSError("psapi missing")))
    assert "psapi missing" in P.peak_memory()["peak_memory_error"]


def test_peak_memory_on_this_platform_is_measured_without_error():
    out = P.peak_memory()
    assert out["peak_memory_error"] is None and out["peak_working_set_mb"] > 0
    if sys.platform == "win32":
        assert out["peak_commit_mb"] > 0  # Windows reports both numbers, and both must be positive


@pytest.mark.skipif(sys.platform != "win32", reason="real Win32 call: only meaningful on Windows")
def test_real_windows_peak_memory_is_positive():
    out = P._windows_peak(P._windows_apis())
    assert out["peak_working_set_mb"] > 0 and out["peak_commit_mb"] > 0


def test_summary_and_smoke_report_carry_the_memory_error_field(tmp_path):
    s = train(tiny(total_env_steps=96, eval_every=48), tmp_path / "r", log=lambda *_: None)
    assert "peak_memory_error" in s and s["peak_memory_error"] is None
