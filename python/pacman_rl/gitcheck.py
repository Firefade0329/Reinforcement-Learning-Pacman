"""Changes that ``git status`` cannot see (standard library only, so the stdlib-only scripts can carry a copy of the same logic).

``git update-index --skip-worktree`` and ``--assume-unchanged`` make git stop comparing a tracked file with the index: the file can
be edited and ``git status --porcelain``, ``git diff`` and ``git diff-index`` still report a clean tree.  A "clean tree" check that
relies on them alone therefore proves nothing about the bytes that will actually be executed.  Two independent defences:

* every tracked file must carry the plain ``H`` flag in ``git ls-files -v`` (``S`` = skip-worktree, a lower-case letter = assume-unchanged);
* the working-tree bytes of the files that matter (``python/`` and the frozen documents) must equal the blobs of ``HEAD`` -- the git
  objects themselves, which neither flag can touch.  The comparison is on raw bytes; ``.gitattributes`` keeps those paths ``-text``.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def _run(root: Path, *args: str, stdin: bytes | None = None):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, input=stdin, timeout=120)


def index_flag_problems(root: Path) -> list[str]:
    """Tracked files whose ``git ls-files -v`` flag is not ``H`` (skip-worktree, assume-unchanged, unmerged, ...)."""
    r = _run(root, "ls-files", "-v", "-z")
    if r.returncode != 0:
        return ["git ls-files -v failed: " + r.stderr.decode("utf-8", "replace").strip()[:200]]
    bad = sorted(f"{e[2:].decode('utf-8', 'replace')} [{e[:1].decode('ascii', 'replace')}]" for e in r.stdout.split(b"\0") if e and e[:1] != b"H")
    return [f"{len(bad)} tracked file(s) carry a skip-worktree / assume-unchanged index flag, which hides working-tree edits from `git status`: {bad[:5]}"] if bad else []


def committed_blobs(root: Path, prefixes: tuple[str, ...], rev: str = "HEAD") -> dict[str, bytes] | None:
    """{path: bytes} of every blob of ``rev`` under the given path prefixes (symlinks and submodules excluded); None if git fails."""
    t = _run(root, "ls-tree", "-r", "-z", rev, "--", *[p.rstrip("/") for p in prefixes])
    if t.returncode != 0:
        return None
    entries = []
    for e in t.stdout.split(b"\0"):
        if not e:
            continue
        meta, path = e.split(b"\t", 1)
        mode, typ, sha = meta.split()
        if typ == b"blob" and mode != b"120000":
            entries.append((path.decode("utf-8", "replace"), sha))
    if not entries:
        return {}
    r = _run(root, "cat-file", "--batch", stdin=b"".join(sha + b"\n" for _, sha in entries))
    if r.returncode != 0:
        return None
    out, pos = {}, 0
    for path, sha in entries:
        end = r.stdout.index(b"\n", pos)
        head = r.stdout[pos:end].split()
        if len(head) != 3 or head[0] != sha or head[1] != b"blob":
            return None
        size = int(head[2])
        out[path] = r.stdout[end + 1:end + 1 + size]
        pos = end + 1 + size + 1
    return out


def tree_sha256(files: dict[str, bytes]) -> str:
    """The ``python_tree_sha256`` algorithm (provenance.code_version): sha256 over ``rel \\0 sha256(bytes) \\n`` in sorted path order."""
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode() + b"\0" + hashlib.sha256(files[rel]).hexdigest().encode() + b"\n")
    return h.hexdigest()


def worktree_mismatches(root: Path, prefixes: tuple[str, ...], skip=(), extra: tuple[str, ...] = ()) -> list[str] | None:
    """Paths (under ``prefixes``, plus the tracked ``extra`` paths) whose working-tree bytes differ from the HEAD blob; None if git fails."""
    blobs = committed_blobs(root, tuple(prefixes) + tuple(extra))
    if blobs is None:
        return None
    root = Path(root)
    bad = []
    for path, data in sorted(blobs.items()):
        if path in skip:
            continue
        p = root / path
        if not p.is_file() or p.read_bytes() != data:
            bad.append(path)
    return bad


def hidden_change_problems(root: Path, prefixes: tuple[str, ...] = ("python", "docs/prereg"), skip=(), extra: tuple[str, ...] = ()) -> list[str]:
    """Problems of the two defences above (empty = nothing hidden).  ``skip``: paths allowed to differ (freeze files being prepared)."""
    problems = index_flag_problems(root)
    bad = worktree_mismatches(root, prefixes, skip, extra)
    if bad is None:
        problems.append("the committed blobs could not be read from git")
    elif bad:
        problems.append(f"{len(bad)} file(s) differ between the working tree and the committed git blob (git status may be blinded): {bad[:5]}")
    return problems
