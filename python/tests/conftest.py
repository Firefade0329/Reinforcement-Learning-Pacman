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
