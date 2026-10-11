"""-text for the frozen files: a fresh checkout gives the committed bytes, whatever core.autocrlf says (temporary git repositories).

The repository's REAL .gitattributes is copied into the fixture; the files are LF documents / scripts / requirement files plus the REAL matrix
(CRLF bytes, registered SHA-256).  Every case clones the committed state into a brand-new directory (as the formal machine must) and compares each file's
bytes with the committed blob and with the original.  Linux with core.autocrlf=true reproduces the Windows conversion; the formal Windows fresh clone
must still be checked by the local executor.  Implementer and test author are the same AI model."""
import hashlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MATRIX_SHA = "5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe"
FILES = {  # path -> bytes (LF text unless noted)
    "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md": "# synthetic fake preregistration\nline two\n".encode(),
    "docs/prereg/ANALYSIS_SPEC_v0.3.2.md": "# synthetic fake specification\n".encode(),
    "docs/prereg/CLAUDE_HANDOFF_v0.3.2.md": "# synthetic fake handoff\n".encode(),
    "docs/prereg/FREEZE_CHECKLIST.md": "| a | b |\n|---|---|\n".encode(),
    "docs/prereg/frozen_config_v0.3.2.json": b'{\n "status": "frozen"\n}\n',
    "docs/prereg/freeze_manifest.json": b'{\n "complete": true\n}\n',
    "docs/prereg/dependency_lock.txt": b"numpy==0.0.0\ntorch==0.0.0\n",
    "python/pacman_rl/window_diag.py": b"x = 1\ny = 2\n",
    "python/scripts/window_diagnostics_summary.py": b"print('a')\n",
    "python/scripts/prereg_analysis.py": b"print('b')\n",
    "python/scripts/prereg_analysis.requirements.txt": b"numpy==0.0.0\n",
    "python/requirements.txt": b"numpy>=1\n",
}


def git(cwd, *a):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], cwd=cwd, check=True, capture_output=True).stdout


def make_origin(tmp_path, with_attributes=True):
    o = tmp_path / "origin"
    o.mkdir()
    git(o, "init", "-q")
    git(o, "config", "core.autocrlf", "false")  # the committer stores the bytes as they are
    files = dict(FILES)
    files["docs/prereg/matrix.csv"] = (ROOT / "docs/prereg/matrix.csv").read_bytes()  # the REAL registered bytes (CRLF)
    if with_attributes:
        files[".gitattributes"] = (ROOT / ".gitattributes").read_bytes()
    for rel, data in files.items():
        (o / rel).parent.mkdir(parents=True, exist_ok=True)
        (o / rel).write_bytes(data)
    git(o, "add", "-A")
    git(o, "commit", "-qm", "C")
    return o, files


def fresh_clone(tmp_path, origin, autocrlf, name):
    dest = tmp_path / name
    git(tmp_path, "clone", "-q", "-c", f"core.autocrlf={autocrlf}", str(origin), str(dest))
    return dest


@pytest.mark.parametrize("autocrlf", ["true", "false"])
def test_fresh_checkout_returns_the_committed_bytes_for_every_frozen_file(tmp_path, autocrlf):
    origin, files = make_origin(tmp_path)
    clone = fresh_clone(tmp_path, origin, autocrlf, "clone")
    assert files["docs/prereg/matrix.csv"].count(b"\r\n") > 0 and hashlib.sha256(files["docs/prereg/matrix.csv"]).hexdigest() == MATRIX_SHA
    for rel, data in files.items():
        got = (clone / rel).read_bytes()
        blob = git(origin, "show", f"HEAD:{rel}")
        assert got == data == blob, f"{rel} (core.autocrlf={autocrlf})"  # working tree bytes == original == committed blob
        assert hashlib.sha256(got).hexdigest() == hashlib.sha256(blob).hexdigest()
    assert hashlib.sha256((clone / "docs/prereg/matrix.csv").read_bytes()).hexdigest() == MATRIX_SHA  # the matrix keeps its registered CRLF bytes


def test_without_the_attributes_file_autocrlf_true_changes_the_bytes(tmp_path):
    """Control: this is the rehearsal's finding R2 -- the LF documents are checked out as CRLF and their hashes change."""
    origin, files = make_origin(tmp_path, with_attributes=False)
    clone = fresh_clone(tmp_path, origin, "true", "clone")
    changed = [rel for rel, data in files.items() if (clone / rel).read_bytes() != data and rel != "docs/prereg/matrix.csv"]
    assert "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md" in changed and "python/scripts/prereg_analysis.py" in changed
    assert clone.joinpath("docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md").read_bytes().count(b"\r\n") == 2


def test_the_real_rules_unset_text_for_every_kind_of_frozen_file():
    files = list(FILES) + ["docs/prereg/matrix.csv", ".gitattributes", "python/pacman_rl/window_diag.py"]
    for rel in files:
        out = subprocess.run(["git", "check-attr", "text", "--", rel], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        assert out.endswith("text: unset"), (rel, out)


def test_the_registered_matrix_in_this_repository_is_untouched():
    data = (ROOT / "docs/prereg/matrix.csv").read_bytes()
    assert hashlib.sha256(data).hexdigest() == MATRIX_SHA and b"\r\n" in data
    blob = subprocess.run(["git", "show", "HEAD:docs/prereg/matrix.csv"], cwd=ROOT, capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == MATRIX_SHA  # the committed blob, not only the working copy


def test_binding_check_hashes_agree_in_a_fresh_checkout_under_both_settings(tmp_path):
    """The check reads raw working-tree bytes: a fresh clone with either autocrlf setting reproduces the recorded hashes (manifest computed from the origin)."""
    from pacman_rl import freeze_binding as FB

    origin, files = make_origin(tmp_path)
    recorded = {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()}
    for autocrlf in ("true", "false"):
        clone = fresh_clone(tmp_path, origin, autocrlf, f"c_{autocrlf}")
        for rel, want in recorded.items():
            assert FB.sha256_bytes_of(clone / rel) == want, (rel, autocrlf)
