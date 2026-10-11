"""F3 (external review of 3337db7): the dependency snapshot was only FORMAT-checked, so any fabricated pins passed.  Both formal entry points
(`prereg.py run` preflight and the final-evaluation preflight) now compare every `name==version` of docs/prereg/dependency_lock.txt with the distribution
installed in the interpreter that is about to train / evaluate (importlib.metadata, names normalised): a mismatch or a missing package refuses and names the
package; the number of compared packages is part of the preflight evidence.  The formal analysis re-validates the snapshot format and records its hash.

The lock content itself is still produced by the local executor; these tests use a fake lock and a replaced version lookup (this module is deliberately NOT
given the conftest default that makes the fake environment match the fake lock).  Synthetic data only."""
import json
import sys
from pathlib import Path

import pytest

from pacman_rl import freeze_binding as FB
from pacman_rl import prereg as PR

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg as runner  # noqa: E402
import prereg_analysis as A  # noqa: E402
from prereg_fixture import Study  # noqa: E402
from test_formal_identity import D  # noqa: E402
from test_freeze_binding import ENTRIES, final_entry, results_for, train_entry  # noqa: E402,F401
from test_freeze_identity import FAKE_LOCK, LOCK_REL, Repo  # noqa: E402

PINS = {"matplotlib": "0.0.0", "numpy": "0.0.0", "pytest": "0.0.0", "torch": "0.0.0"}  # the fake lock of the fixtures


def install(monkeypatch, versions):
    """Replace the version lookup by a dictionary (None = not installed); records the names asked for."""
    asked = []

    def lookup(name):
        asked.append(name)
        return versions.get(name.lower())

    monkeypatch.setattr(FB, "installed_version", lookup)
    return asked


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = Repo(tmp_path / "r")
    monkeypatch.setattr(PR, "MATRIX_FILE", r.root / "docs/prereg/matrix.csv")
    r.freeze()
    return r


# ------------------------------------------------------------------ the comparison
def test_default_lookup_is_importlib_metadata_with_normalised_names():
    assert FB.installed_version("PyTest") == pytest.__version__ and FB.installed_version("py_test_does_not_exist_zz") is None
    import numpy

    assert FB.installed_version("NumPy") == numpy.__version__


def test_matching_environment_has_no_problem_and_every_package_is_compared(monkeypatch):
    asked = install(monkeypatch, PINS)
    assert FB.environment_problems(FAKE_LOCK.encode()) == ([], 4) and sorted(asked) == sorted(PINS)


@pytest.mark.parametrize("have,message", [("0.0.1", r"torch: the snapshot pins 0\.0\.0 but this environment has 0\.0\.1"),
                                          ("0.0.0+cu126", r"torch: the snapshot pins 0\.0\.0 but this environment has 0\.0\.0\+cu126"),
                                          (None, r"torch==0\.0\.0: the package is in the dependency snapshot but not installed")])
def test_one_wrong_or_missing_package_is_a_problem_that_names_it(monkeypatch, have, message):
    install(monkeypatch, {**PINS, "torch": have})
    problems, n = FB.environment_problems(FAKE_LOCK.encode())
    assert len(problems) == 1 and n == 4
    import re

    assert re.search(message, problems[0])


# ------------------------------------------------------------------ both formal entries
@pytest.mark.parametrize("entry", ENTRIES)
def test_the_matching_environment_passes_both_entries_and_the_evidence_counts_the_packages(repo, monkeypatch, entry):
    install(monkeypatch, PINS)
    ev = {}
    if entry is train_entry:
        runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root, evidence=ev)
        binding = ev
    else:
        binding = final_entry(repo)["freeze_binding"]
    assert binding["environment_packages_compared"] == 4 and binding["environment_matches_lock"] is True and binding["binding_passed"] is True
    assert binding["dependency_lock_sha256"] == FB.sha256_bytes_of(repo.root / LOCK_REL)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("package,have", [("torch", "0.0.1"), ("numpy", None), ("matplotlib", "3.9.0"), ("pytest", None)])
def test_a_package_that_differs_from_the_snapshot_or_is_missing_is_refused_by_name(repo, monkeypatch, entry, package, have):
    install(monkeypatch, {**PINS, package: have})
    with pytest.raises(runner.Refused, match=rf"environment differs from the snapshot: {package}\b"):
        entry(repo)


def test_the_real_environment_does_not_match_a_fabricated_snapshot(repo):
    """No replacement at all: the production lookup compares the fixture's fake 0.0.0 pins with what is really installed."""
    with pytest.raises(runner.Refused, match="environment differs from the snapshot"):
        train_entry(repo)


def test_a_lock_in_the_wrong_format_is_reported_as_a_format_problem_only(repo, monkeypatch):
    asked = install(monkeypatch, PINS)
    repo.commit_file(LOCK_REL, "numpy>=1\n")
    repo.amend_cfg(lambda c: c["to_fill_at_freeze"].__setitem__("dependency_lock_sha256", FB.sha256_bytes_of(repo.root / LOCK_REL)))
    repo.amend_manifest(lambda m: m["frozen_files"].__setitem__(LOCK_REL, FB.sha256_bytes_of(repo.root / LOCK_REL)))
    with pytest.raises(runner.Refused, match="not an exact") as e:
        train_entry(repo)
    assert "environment differs" not in str(e.value) and asked == []  # an unparsable snapshot is never compared


def test_a_failed_environment_comparison_starts_nothing(repo, monkeypatch):
    install(monkeypatch, {**PINS, "torch": None})
    started = []
    monkeypatch.setattr(runner, "run_matrix", lambda *a, **k: started.append(1))
    with pytest.raises(runner.Refused):
        runner.preflight(repo.cfg, None, allow_unfrozen=False, root=repo.root)
    assert started == []


# ------------------------------------------------------------------ the formal analysis re-validates the snapshot
def formal(tmp_path):
    return Study(tmp_path / "p", d=D, formal=True)


def test_formal_analysis_revalidates_the_snapshot_and_records_its_hash(tmp_path):
    st = formal(tmp_path)
    out = tmp_path / "out"
    A.analyze(st.manifest, st.runs, out, "formal")
    prov = json.loads((out / "analysis.json").read_text())["provenance"]["protocol_evidence"]["dependency_lock"]
    lock = st.root / LOCK_REL
    assert prov == {"path": LOCK_REL, "sha256": FB.sha256_bytes_of(lock), "format_validated": True, "entries": 4}
    rep = (out / "REPORT.md").read_text()
    assert FB.sha256_bytes_of(lock) in rep and "format re-validated" in rep


@pytest.mark.parametrize("text", [b"numpy>=1\n", b"matplotlib==0.0.0\nnumpy==0.0.0\npytest==0.0.0\n", b"\xef\xbb\xbfmatplotlib==0.0.0\nnumpy==0.0.0\npytest==0.0.0\ntorch==0.0.0\n",
                                  b"matplotlib==0.0.0\r\nnumpy==0.0.0\r\npytest==0.0.0\r\ntorch==0.0.0\r\n", b"torch==0.0.0\nnumpy==0.0.0\nmatplotlib==0.0.0\npytest==0.0.0\n"])
def test_formal_analysis_refuses_an_ill_formed_snapshot_even_when_its_hash_is_frozen(tmp_path, text):
    """The snapshot is committed in C and hashed everywhere consistently (manifest, configuration): only the format re-validation can notice it."""
    st = Study(tmp_path / "p", d=D, formal=True, lock_bytes=text)
    out = tmp_path / "out_fail"
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, out, "formal")
    assert e.value.obj["code"] == "E_MANIFEST" and "dependency snapshot" in e.value.obj["message"], e.value.obj
    assert not out.exists()


def test_the_script_copy_of_the_format_check_equals_the_package_function():
    cases = [b"matplotlib==3.9.0\nnumpy==2.0.0\npytest==8.0.0\ntorch==2.5.1+cu121\n", b"", b"\n", b"numpy==2.0.0\n", b"numpy>=1\n", b"\xef\xbb\xbfnumpy==1\n",
             b"matplotlib==1\r\nnumpy==1\r\n", b"\xff\xfe", b"Numpy==1\nnumpy==2\nmatplotlib==1\npytest==1\ntorch==1\n", b"a==1\n\nb==2\n"]
    for data in cases:
        assert A.lock_format_problems(data) == FB.lock_problems(data), data
    assert A.LOCK_REQUIRED_PACKAGES == FB.LOCK_REQUIRED_PACKAGES
