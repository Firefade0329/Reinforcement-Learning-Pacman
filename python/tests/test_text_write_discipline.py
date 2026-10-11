"""Static guard: a text-mode write must state its newline.

`Path.write_text(...)` and `open(..., "w" / "a" / "x")` without `newline=` write CRLF on Windows and LF elsewhere.  A file that is hashed, sealed, format-checked or
compared byte for byte must not depend on that, so every such call in the sources (production and tests) either passes `newline=` or is listed below with the reason it
does not matter.  Binary writes (`write_bytes`, "wb") are fine.  See tests/test_lf_bytes.py for the behavioural check of each producer."""
import ast
from pathlib import Path

PY = Path(__file__).resolve().parents[1]

# file (relative to python/) -> reason: text outputs that are never hashed, sealed or compared byte for byte
ALLOWED = {
    "scripts/run_experiments.py": "console log of the old experiment launcher and the pid file of its lock",
    "scripts/make_comparison.py": "human-readable report (Markdown), not hashed",
    "scripts/make_report.py": "human-readable report (Markdown), not hashed",
    "scripts/nstep_oracle_report.py": "human-readable evidence report, not hashed",
    "pacman_rl/tabular.py": "legacy tabular-Q result of the old experiment, not part of the preregistered study",
    "tests/conftest.py": "defines the CRLF simulation itself",
}


def _mode_constants(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _mode_constants(node.body) + _mode_constants(node.orelse)
    return []


def unsafe_text_writes(source: str) -> list[tuple[int, str]]:
    out = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        kws = {k.arg for k in node.keywords}
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "write_text" and "newline" not in kws:
            out.append((node.lineno, "write_text without newline="))
        is_builtin_open = isinstance(f, ast.Name) and f.id == "open"
        is_io_open = isinstance(f, ast.Attribute) and f.attr == "open" and isinstance(f.value, ast.Name) and f.value.id == "io"
        is_path_open = isinstance(f, ast.Attribute) and f.attr == "open" and not is_io_open and not (isinstance(f.value, ast.Name) and f.value.id in ("os", "tarfile", "zipfile", "webbrowser"))
        if is_builtin_open or is_io_open or is_path_open:
            mode_node = next((k.value for k in node.keywords if k.arg == "mode"), None)
            if mode_node is None:
                idx = 1 if (is_builtin_open or is_io_open) else 0
                mode_node = node.args[idx] if len(node.args) > idx else None
            modes = _mode_constants(mode_node) if mode_node is not None else []
            if any("b" not in m and any(c in m for c in "wax") for m in modes) and "newline" not in kws:
                out.append((node.lineno, "text-mode open for writing without newline="))
    return out


def test_the_guard_recognises_the_risky_forms_and_accepts_the_safe_ones():
    bad = '''
from pathlib import Path
Path("a").write_text("x")
Path("a").write_text("x", encoding="utf-8")
open("a", "w")
open("a", "a", encoding="utf-8")
open("a", mode="x")
open("a", "a" if resumed else "w")
io.open("a", "w")
p.open("w")
'''
    assert [what for _, what in unsafe_text_writes(bad)].count("write_text without newline=") == 2
    assert len(unsafe_text_writes(bad)) == 8
    good = '''
Path("a").write_text("x", newline="\\n")
Path("a").write_bytes(b"x")
open("a", "wb")
open("a", "r")
open("a")
open("a", "w", newline="\\n")
open("a", "a" if resumed else "w", newline="\\n")
open("a", newline="")
os.open("a", os.O_WRONLY)
'''
    assert unsafe_text_writes(good) == []


def test_no_python_source_writes_text_without_stating_the_newline():
    offenders = []
    for path in sorted(PY.rglob("*.py")):
        rel = path.relative_to(PY).as_posix()
        if rel in ALLOWED:
            continue
        for lineno, what in unsafe_text_writes(path.read_text(encoding="utf-8")):
            offenders.append(f"{rel}:{lineno}: {what}")
    assert offenders == [], "\n".join(offenders)


def test_every_allowed_exception_still_exists_and_still_needs_the_exception():
    for rel in ALLOWED:
        path = PY / rel
        assert path.is_file(), f"{rel} no longer exists: remove it from ALLOWED"
    for rel in ALLOWED:
        if rel == "tests/conftest.py":
            continue
        assert unsafe_text_writes((PY / rel).read_text(encoding="utf-8")), f"{rel} has no unsafe write any more: remove it from ALLOWED"
