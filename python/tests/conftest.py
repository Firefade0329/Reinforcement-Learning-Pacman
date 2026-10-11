"""Hermetic environment for the preregistration tests.

`acceptance.sh --quick` exports PACMAN_RESULTS_DIR (and a developer may have other PACMAN_* overrides set); the preregistration runner
refuses to start while any of those is present, by design.  The tests of the runner / freeze / seal machinery must therefore not inherit them;
tests that check the refusal set the variables themselves."""
import pytest

PREREG_MODULES = {"test_freeze_identity", "test_freeze_binding", "test_seal", "test_prereg", "test_prereg_analysis", "test_prereg_analysis_outputs",
                  "test_prereg_analysis_expected", "test_analysis_error_order", "test_formal_identity", "test_protocol_evidence", "test_provenance",
                  "test_window_diag", "test_window_diag_wiring", "test_window_diag_summary", "test_death_penalty_contract", "test_gitattributes"}
OVERRIDES = ("PACMAN_TRAIN_EXTRA", "PACMAN_STEPS", "PACMAN_DEVICE", "PACMAN_WORKERS", "PACMAN_SKIP_ALGO", "PACMAN_RESULTS_DIR")


@pytest.fixture(autouse=True)
def _no_pacman_overrides(request, monkeypatch):
    if request.module.__name__.split(".")[-1] in PREREG_MODULES:
        for var in OVERRIDES:
            monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------------------------- Windows text-mode simulation
# On Windows a text-mode write turns "\n" into "\r\n".  The simulation reproduces that on any platform: every text write (Path.write_text, open(..., "w"), io.open)
# whose `newline` is not given writes CRLF.  Anything that is hashed, format-checked or compared byte for byte must therefore be written with newline="\n" or as
# bytes.  Two uses: the `windows_text_mode` fixture (tests/test_lf_bytes.py runs each producer under it and asserts the produced bytes contain no CR), and the
# opt-in whole-suite run PACMAN_SIMULATE_WINDOWS_TEXT=1 (tests/test_text_write_discipline.py guards the sources statically).
import builtins  # noqa: E402
import io  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402

_REAL_OPEN, _REAL_WRITE_TEXT = io.open, pathlib.Path.write_text


def _crlf_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, *a, **k):
    if "b" not in mode and any(c in mode for c in "wax") and newline is None:
        newline = "\r\n"
    return _REAL_OPEN(file, mode, buffering, encoding, errors, newline, *a, **k)


def _crlf_write_text(self, data, encoding=None, errors=None, newline=None):
    return _REAL_WRITE_TEXT(self, data, encoding=encoding, errors=errors, newline="\r\n" if newline is None else newline)


def install_windows_text_mode(mp) -> None:
    mp.setattr(builtins, "open", _crlf_open)
    mp.setattr(io, "open", _crlf_open)
    mp.setattr(pathlib.Path, "write_text", _crlf_write_text)


@pytest.fixture()
def windows_text_mode(monkeypatch):
    install_windows_text_mode(monkeypatch)


if os.environ.get("PACMAN_SIMULATE_WINDOWS_TEXT") == "1":
    builtins.open = io.open = _crlf_open
    pathlib.Path.write_text = _crlf_write_text
