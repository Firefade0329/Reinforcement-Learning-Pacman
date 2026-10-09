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


def peak_memory(device=None) -> dict:
    """Best-effort peak memory of this process in MB (working set; Windows also peak commit) and the CUDA allocator peaks."""
    out = {"peak_working_set_mb": None, "peak_commit_mb": None, "cuda_max_allocated_mb": None, "cuda_max_reserved_mb": None}
    try:
        import resource  # POSIX

        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        out["peak_working_set_mb"] = round(r / (1024 * 1024 if platform.system() == "Darwin" else 1024), 1)
    except ImportError:
        try:  # Windows
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                out["peak_working_set_mb"] = round(pmc.PeakWorkingSetSize / 2**20, 1)
                out["peak_commit_mb"] = round(pmc.PeakPagefileUsage / 2**20, 1)
        except Exception:  # noqa: BLE001
            pass
    if device is not None and torch.device(device).type == "cuda":
        out["cuda_max_allocated_mb"] = round(torch.cuda.max_memory_allocated(device) / 2**20, 1)
        out["cuda_max_reserved_mb"] = round(torch.cuda.max_memory_reserved(device) / 2**20, 1)
    return out
