"""Run provenance: canonical weight hashes, the code version and a PRIVACY-SAFE description of the software / GPU.

``environment_info`` is an allow-list: only the keys in ``ENV_KEYS`` can ever appear in ``environment.json`` (GPU model,
python / torch / CUDA / cuDNN / numpy versions, thread count, determinism switches).  It never records a CPU brand,
host name, user name or any path; tests enforce that.
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
ENV_KEYS = ("python", "torch", "numpy", "cuda_runtime", "cudnn", "device_type", "gpu_name", "torch_threads",
            "deterministic_algorithms", "cudnn_deterministic", "cudnn_benchmark")


def state_hash(obj) -> str:
    """Canonical SHA-256 of model parameters: keys in sorted order, each contributing its name, dtype, shape and raw
    tensor bytes.  Independent of the serialisation format / checkpoint metadata / device the tensors live on."""
    sd = obj.state_dict() if hasattr(obj, "state_dict") else obj
    h = hashlib.sha256()
    for k in sorted(sd):
        t = sd[k].detach().cpu().contiguous()
        h.update(k.encode("utf-8") + b"\0" + str(t.dtype).encode() + b"\0" + str(tuple(t.shape)).encode() + b"\0")
        h.update(t.numpy().tobytes())
    return h.hexdigest()


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def environment_info(device) -> dict:
    device = torch.device(device)
    cuda = device.type == "cuda"
    info = {
        "python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
        "cuda_runtime": torch.version.cuda, "cudnn": torch.backends.cudnn.version() if cuda else None,
        "device_type": device.type, "gpu_name": torch.cuda.get_device_name(device) if cuda else None,
        "torch_threads": torch.get_num_threads(),
        "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic), "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
    }
    assert set(info) == set(ENV_KEYS)
    return info


def _git(root: Path, *args: str):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001 - git missing / not a repository
        return None


def code_version(root: Path | None = None, extra_files: dict[str, str] | None = None) -> dict:
    """Which code produced a run: full git SHA, whether the working tree differed from it (and a hash of that
    difference), a hash over the CURRENT contents of every tracked file under python/, and sha256 of named extra files
    (preregistration matrix, frozen configuration, analysis script ...; paths relative to the repository)."""
    root = Path(root or ROOT)
    sha = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    dirty = None if status is None else bool(status)
    diff = _git(root, "diff", "HEAD") if dirty else None
    h = hashlib.sha256()
    tracked = (_git(root, "ls-files", "python") or "").splitlines()
    for rel in sorted(tracked):
        p = root / rel
        if p.is_file():
            h.update(rel.encode() + b"\0" + file_sha256(p).encode() + b"\n")
    files = {rel: (file_sha256(root / rel) if (root / rel).is_file() else None) for rel in sorted(extra_files or {})}
    return {"git_sha": sha, "git_dirty": dirty,
            "git_diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None,
            "python_tree_sha256": h.hexdigest() if tracked else None, "files": files}


# Files that may differ between the CODE commit C and the FREEZE commit F (the commit the runs are made from).
FREEZE_MATERIALS = ("docs/prereg/frozen_config_v0.3.2.json", "docs/prereg/freeze_manifest.json", "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md",
                    "docs/prereg/ANALYSIS_SPEC_v0.3.2.md", "docs/prereg/CLAUDE_HANDOFF_v0.3.2.md", "docs/prereg/FREEZE_CHECKLIST.md")


def freeze_state(root: Path | None, code_commit: str | None, *, allow_dirty_freeze_files: bool = False, must_exist_in_c: tuple = ()) -> dict:
    """Is this working copy a legitimate FREEZE commit F of the code commit C = ``code_commit``?

    The frozen configuration records C in a tracked file, so it cannot name the commit that contains it.  Hence two commits: C is
    the code, F (= HEAD, any descendant of C) adds only freeze material.  Verifiable conditions: C is a commit and an ancestor of
    (or equal to) HEAD; the ``python/`` tree object is byte-identical at C and HEAD; ``docs/prereg/matrix.csv`` is unchanged; every file
    that differs between C and HEAD is in FREEZE_MATERIALS; no tracked file is modified in the working tree (while the freeze files
    are being prepared, ``allow_dirty_freeze_files`` accepts modifications to FREEZE_MATERIALS only).  Returns
    {"problems": [...], "head": sha-or-None, "code_commit": C}.  ``must_exist_in_c``: paths that must already be in C's tree (files that
    may not first appear in F, e.g. the dependency snapshot)."""
    root = Path(root or ROOT)
    problems: list[str] = []
    head = _git(root, "rev-parse", "HEAD")
    out = {"problems": problems, "head": head, "code_commit": code_commit}
    if head is None:
        problems.append("git is unavailable or this is not a repository")
        return out
    if not (isinstance(code_commit, str) and len(code_commit) == 40 and set(code_commit) <= set("0123456789abcdef")):
        problems.append("code_commit is not a full 40-hex commit id")
        return out
    if _git(root, "rev-parse", "--verify", f"{code_commit}^{{commit}}") != code_commit:
        problems.append("code_commit does not name a commit in this repository")
        return out
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", code_commit, "HEAD"], cwd=root, capture_output=True).returncode == 0
    if not ancestor:
        problems.append("code_commit is not an ancestor of HEAD")
        return out
    if _git(root, "rev-parse", f"{code_commit}:python") != _git(root, "rev-parse", "HEAD:python"):
        problems.append("the python/ tree at HEAD differs from the one at code_commit")
    for rel in must_exist_in_c:
        if subprocess.run(["git", "cat-file", "-e", f"{code_commit}:{rel}"], cwd=root, capture_output=True).returncode != 0:
            problems.append(f"{rel} does not exist in the code commit C (it may not first appear in the freeze commit F)")
    changed = (_git(root, "diff", "--name-only", code_commit, "HEAD") or "").splitlines()
    bad = sorted(f for f in changed if f not in FREEZE_MATERIALS)
    if bad:
        problems.append(f"files changed between code_commit and HEAD that are not freeze material: {bad[:5]}")
    raw = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, capture_output=True, text=True).stdout  # not stripped: column 1 may be a space
    dirty = [line[3:].split(" -> ")[-1] for line in raw.splitlines() if line.strip()]
    bad_dirty = sorted(f for f in dirty if not (allow_dirty_freeze_files and f in FREEZE_MATERIALS))
    if bad_dirty:
        problems.append(f"the working tree has uncommitted changes: {bad_dirty[:5]}")
    return out


def _windows_apis():
    """(ctypes, wintypes, kernel32, psapi) as private WinDLL instances.  ``ctypes.windll`` is a process-wide cache whose
    functions would get our argtypes/restype assignments imposed on every other user of the same DLL; WinDLL is private."""
    import ctypes
    from ctypes import wintypes

    return ctypes, wintypes, ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)


def _windows_peak(apis) -> dict:
    """Peak working set and peak commit of this process in MB via GetProcessMemoryInfo.

    GetCurrentProcess returns the pseudo-handle (HANDLE)-1, which a 64-bit ``c_void_p`` result reads as 18446744073709551615.
    Passed to a ctypes function without declared ``argtypes`` that value is converted as a plain C integer and overflows
    (``OverflowError: int too long to convert``), so BOTH functions get explicit signatures before they are called."""
    ctypes, wintypes, k32, psapi = apis

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]

    k32.GetCurrentProcess.argtypes = []
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        raise OSError(f"GetProcessMemoryInfo returned FALSE (last error {getattr(ctypes, 'get_last_error', lambda: 'n/a')()})")
    return {"peak_working_set_mb": round(pmc.PeakWorkingSetSize / 2**20, 1), "peak_commit_mb": round(pmc.PeakPagefileUsage / 2**20, 1)}


def _posix_peak() -> dict:
    import resource

    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB on Linux, bytes on macOS
    return {"peak_working_set_mb": round(r / (1024 * 1024 if platform.system() == "Darwin" else 1024), 1), "peak_commit_mb": None}


def peak_memory(device=None) -> dict:
    """Peak memory of this process in MB (working set; Windows also peak commit) and the CUDA allocator peaks.

    A failure is never silent: whatever could not be measured stays ``None`` and ``peak_memory_error`` says why
    (``None`` when everything that applies to this platform/device was measured)."""
    out = {"peak_working_set_mb": None, "peak_commit_mb": None, "cuda_max_allocated_mb": None, "cuda_max_reserved_mb": None, "peak_memory_error": None}
    errors = []
    try:
        out.update(_windows_peak(_windows_apis()) if platform.system() == "Windows" else _posix_peak())
    except Exception as e:  # noqa: BLE001 - reported below, not swallowed
        errors.append(f"process memory: {type(e).__name__}: {e}")
    if device is not None and torch.device(device).type == "cuda":
        try:
            out["cuda_max_allocated_mb"] = round(torch.cuda.max_memory_allocated(device) / 2**20, 1)
            out["cuda_max_reserved_mb"] = round(torch.cuda.max_memory_reserved(device) / 2**20, 1)
        except Exception as e:  # noqa: BLE001
            errors.append(f"cuda memory: {type(e).__name__}: {e}")
    out["peak_memory_error"] = "; ".join(errors) or None
    return out
