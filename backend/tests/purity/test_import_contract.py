"""Static purity enforcement for ``finguard_core`` (ADR 0001).

The specification calls for an import-linter contract. ``import-linter``
could not be installed in this environment (no network access to PyPI
from this session — see the PR-1 report's deviations section), so this
test enforces the identical rule by statically walking every module's
AST and checking its imports, without needing the package installed.
If import-linter becomes available later, this test and its forbidden
list should be kept in sync with ``backend/pyproject.toml``'s
``[[tool.importlinter.contracts]]`` entry (already present and ready to
run once the tool can be installed).
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_MODULES = {
    "os.path",
    "pathlib",
    "socket",
    "requests",
    "httpx",
    "urllib",
    "urllib.request",
    "sqlalchemy",
    "psycopg2",
    "fastapi",
    "flask",
    "openai",
    "anthropic",
}

# Modules that are themselves fine, but whose only legitimate use in this
# codebase is filesystem/network access; forbidding the parent above
# already catches `import os.path`, but bare `import os` is pervasive for
# things like `os.PathLike` type hints without doing I/O, so it isn't
# blanket-forbidden — this test instead asserts no I/O happens at runtime
# (see test_no_filesystem_or_socket_access.py).

CORE_ROOT = Path(__file__).resolve().parents[2] / "finguard_core"


def _iter_imported_module_names(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module


def test_core_package_exists():
    assert CORE_ROOT.is_dir(), f"expected finguard_core at {CORE_ROOT}"
    assert any(CORE_ROOT.glob("*.py"))


def test_no_forbidden_imports_anywhere_in_core():
    violations: list[str] = []
    for path in sorted(CORE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _iter_imported_module_names(tree):
            for forbidden in FORBIDDEN_MODULES:
                if name == forbidden or name.startswith(forbidden + "."):
                    violations.append(f"{path.relative_to(CORE_ROOT.parent)}: imports {name!r}")
    assert not violations, "forbidden imports found in finguard_core:\n" + "\n".join(violations)


def test_no_wall_clock_reads():
    """``date.today()`` / ``datetime.now()`` would read the wall clock;
    ``as_of`` must always be caller-supplied instead.
    """

    violations: list[str] = []
    for path in sorted(CORE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"today", "now", "utcnow"}:
                    violations.append(f"{path.name}:{node.lineno} calls .{node.func.attr}(...)")
    assert not violations, "wall-clock reads found in finguard_core:\n" + "\n".join(violations)


def test_no_random_or_uuid_usage():
    """Canonical output must never depend on ``random`` or ``uuid`` —
    both would break byte-identical determinism for identical inputs.
    """

    violations: list[str] = []
    for path in sorted(CORE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _iter_imported_module_names(tree):
            if name in {"random", "uuid"} or name.startswith(("random.", "uuid.")):
                violations.append(f"{path.name}: imports {name!r}")
    assert not violations, "non-deterministic imports found in finguard_core:\n" + "\n".join(violations)
