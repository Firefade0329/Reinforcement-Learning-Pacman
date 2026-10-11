"""Small filesystem helpers for the tests that build throw-away git repositories.

On Windows the objects inside `.git` are read-only, so a plain `shutil.rmtree` raises PermissionError; this removes read-only files too."""
from __future__ import annotations

import os
import shutil
import stat
import sys


def _make_writable_and_retry(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rmtree_force(path, *, ignore_errors: bool = False) -> None:
    """Remove a directory tree, clearing the read-only flag of files that block the removal (git object files on Windows)."""
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_make_writable_and_retry)
        else:
            shutil.rmtree(path, onerror=_make_writable_and_retry)
    except OSError:
        if not ignore_errors:
            raise
