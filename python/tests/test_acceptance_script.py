"""acceptance.sh picks its interpreter: $PYTHON, else the first of python3 / python that can run --version (stub interpreters, no real run)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "acceptance.sh"
pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash on a POSIX path layout")


def stub(dir_: Path, name: str, works: bool):
    f = dir_ / name
    log = dir_ / f"{name}.log"
    f.write_text(f'#!/bin/sh\necho "{name} $@" >> "{log}"\n' + ("exit 0\n" if works else "exit 9\n"))
    f.chmod(0o755)
    return log


def run(tmp_path, env_python=None):
    env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}", "HOME": str(tmp_path)}
    if env_python:
        env["PYTHON"] = env_python
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env)


def calls(log):
    return log.read_text().splitlines() if log.exists() else []


def test_falls_back_to_python_when_python3_is_a_broken_alias(tmp_path):
    bad, good = stub(tmp_path, "python3", False), stub(tmp_path, "python", True)
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert calls(bad) == ["python3 --version"]  # probed, rejected, never used to run the checks
    assert any("scripts/check_acceptance.py --run-tests" in c for c in calls(good))


def test_python3_is_preferred_when_it_works(tmp_path):
    p3, p = stub(tmp_path, "python3", True), stub(tmp_path, "python", True)
    assert run(tmp_path).returncode == 0
    assert any("check_acceptance.py" in c for c in calls(p3)) and calls(p) == []


def test_the_PYTHON_variable_wins_without_probing(tmp_path):
    p3, p = stub(tmp_path, "python3", True), stub(tmp_path, "python", True)
    mine_log = stub(tmp_path, "mine", True)
    assert run(tmp_path, env_python=str(tmp_path / "mine")).returncode == 0
    assert any("check_acceptance.py" in c for c in calls(mine_log)) and calls(p3) == [] and calls(p) == []


def test_no_working_interpreter_is_a_clear_error(tmp_path):
    stub(tmp_path, "python3", False)
    stub(tmp_path, "python", False)
    r = run(tmp_path)
    assert r.returncode == 1 and "no working Python found" in r.stderr
