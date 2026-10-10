"""The freeze binding check: do the frozen configuration, the freeze manifest and the ACTUAL files agree?

One function used by every formal entry (``prereg.py run``, ``prereg.py final-eval``) BEFORE anything is started or unsealed, and by the
manifest generator on the manifest it is about to write.  Standard library only; no git, no torch.  The only data sources are
``docs/prereg/frozen_config_v0.3.2.json`` and ``docs/prereg/freeze_manifest.json`` under an explicit project root; nothing is guessed,
generated or repaired.  Hashes are SHA-256 of the raw working-tree bytes (no newline normalisation, no BOM stripping).

The manifest does not list itself (no self reference); its own hash is kept by the external freeze record.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

CONFIG_REL = "docs/prereg/frozen_config_v0.3.2.json"
MANIFEST_REL = "docs/prereg/freeze_manifest.json"
MATRIX_REL = "docs/prereg/matrix.csv"
MATRIX_SHA256 = "5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe"
PREREG_REL = "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md"
SPEC_REL = "docs/prereg/ANALYSIS_SPEC_v0.3.2.md"
ATTR_REL = ".gitattributes"
FREEZE_SCHEMA = "prereg-freeze-1"
SPEC_VERSION = "0.3.2"
# files that must be listed (and are then hashed) in every formal manifest, besides manifest.analysis_script_path / dependency_lock_path
REQUIRED_FROZEN = (MATRIX_REL, CONFIG_REL, PREREG_REL, SPEC_REL, ATTR_REL)  # .gitattributes: the -text rules are part of the byte contract
HEX64 = set("0123456789abcdef")


def is_hex64(x) -> bool:
    return isinstance(x, str) and len(x) == 64 and set(x) <= HEX64


def sha256_bytes_of(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate JSON key {k!r}")
        d[k] = v
    return d


def load_json_strict(path):
    def bad(c):
        raise ValueError(f"non-finite JSON constant {c}")

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_no_dupes, parse_constant=bad)


def safe_relative(root: Path, rel) -> Path | None:
    """The file ``rel`` names under ``root``, or None if it is not a plain relative path that stays inside the root."""
    if not isinstance(rel, str) or not rel or "\\" in rel:
        return None
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or (len(rel) > 1 and rel[1] == ":"):
        return None
    full = (Path(root) / rel).resolve()
    try:
        full.relative_to(Path(root).resolve())
    except ValueError:
        return None
    return full


def check_binding(root: Path, config, manifest, *, require_complete: bool = True) -> list[str]:
    """Problems of an already parsed (config, manifest) pair against the files under ``root``.  Empty list = bound."""
    root = Path(root)
    problems: list[str] = []
    if not isinstance(config, dict) or not isinstance(manifest, dict):
        return ["the frozen configuration and the manifest must both be JSON objects"]
    if manifest.get("schema_version") != FREEZE_SCHEMA or manifest.get("spec_version") != SPEC_VERSION:
        problems.append(f"{MANIFEST_REL}: schema_version / spec_version are {manifest.get('schema_version')!r} / {manifest.get('spec_version')!r}, expected {FREEZE_SCHEMA!r} / {SPEC_VERSION!r}")
    if manifest.get("synthetic") is not False:
        problems.append(f"{MANIFEST_REL}: synthetic must be false for a formal run (is {manifest.get('synthetic')!r})")
    if require_complete and manifest.get("complete") is not True:
        problems.append(f"{MANIFEST_REL}: complete must be true (is {manifest.get('complete')!r})")
    c_cfg, c_man = config.get("code_commit"), manifest.get("code_commit")
    if not (isinstance(c_cfg, str) and len(c_cfg) == 40 and set(c_cfg) <= HEX64):
        problems.append(f"{CONFIG_REL}: code_commit {c_cfg!r} is not a full 40-hex commit")
    if c_cfg != c_man:
        problems.append(f"{MANIFEST_REL}: code_commit {c_man!r} differs from the frozen configuration's {c_cfg!r}")
    if manifest.get("config_path") != CONFIG_REL or manifest.get("matrix_path") != MATRIX_REL:
        problems.append(f"{MANIFEST_REL}: config_path / matrix_path must be {CONFIG_REL} / {MATRIX_REL}")
    files = manifest.get("frozen_files")
    if not isinstance(files, dict):
        problems.append(f"{MANIFEST_REL}: frozen_files must be an object path -> sha256")
        return problems
    needed = list(REQUIRED_FROZEN) + [manifest.get("analysis_script_path"), manifest.get("dependency_lock_path")]
    for rel in needed:
        if not isinstance(rel, str) or rel not in files:
            problems.append(f"{MANIFEST_REL}: required frozen file {rel!r} is not listed in frozen_files")
    for rel, want in files.items():
        full = safe_relative(root, rel)
        if full is None:
            problems.append(f"{MANIFEST_REL}: frozen file path {rel!r} is not a relative path inside the project")
            continue
        if not is_hex64(want):
            problems.append(f"{rel}: recorded hash {want!r} is not 64 lower-case hex characters")
            continue
        if not full.is_file():
            problems.append(f"{rel}: listed in frozen_files but the file is missing")
            continue
        got = sha256_bytes_of(full)
        if got != want:
            problems.append(f"{rel}: the file's SHA-256 {got} differs from the frozen {want}")
    if files.get(MATRIX_REL) != MATRIX_SHA256 and MATRIX_REL in files:
        problems.append(f"{MATRIX_REL}: the frozen hash is not the registered matrix hash {MATRIX_SHA256}")
    fill = config.get("to_fill_at_freeze")
    fill = fill if isinstance(fill, dict) else {}
    for field, target in (("analysis_script_sha256", manifest.get("analysis_script_path")), ("preregistration_document_sha256", PREREG_REL),
                          ("dependency_lock_sha256", manifest.get("dependency_lock_path"))):
        have = fill.get(field)
        if not is_hex64(have) or set(have) == {"0"}:
            problems.append(f"{CONFIG_REL}: to_fill_at_freeze.{field} is not a real SHA-256 ({have!r})")
        elif files.get(target) != have:
            problems.append(f"{CONFIG_REL}: to_fill_at_freeze.{field} {have} differs from the manifest entry for {target} ({files.get(target)!r})")
    return problems


def binding_check(root: Path) -> tuple[list[str], dict]:
    """Load config and manifest from ``root`` and check them.  Returns (problems, evidence); evidence is only meaningful when no problem."""
    root = Path(root)
    cfg_file, man_file = root / CONFIG_REL, root / MANIFEST_REL
    if not man_file.is_file():
        return [f"{MANIFEST_REL}: missing (the freeze manifest must be committed in the freeze commit)"], {}
    if not cfg_file.is_file():
        return [f"{CONFIG_REL}: missing"], {}
    try:
        config, manifest = load_json_strict(cfg_file), load_json_strict(man_file)
    except (ValueError, OSError) as e:
        return [f"freeze material is not valid JSON: {e}"], {}
    problems = check_binding(root, config, manifest)
    evidence = {"checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "freeze_manifest_sha256": sha256_bytes_of(man_file),
                "code_commit": manifest.get("code_commit"), "files_checked": len(manifest.get("frozen_files") or {}), "binding_passed": not problems}
    return problems, evidence
