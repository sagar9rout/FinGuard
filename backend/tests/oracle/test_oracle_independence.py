"""Verifies the oracle genuinely never imports production code, and
genuinely isn't imported by it — both directions of ADR 0001's oracle-
independence requirement.
"""

from __future__ import annotations

import ast
from pathlib import Path

ORACLE_FILE = Path(__file__).resolve().parent / "reference_safety.py"
CORE_ROOT = Path(__file__).resolve().parents[2] / "finguard_core"

FORBIDDEN_ORACLE_IMPORTS = {
    "finguard_core",
    "finguard_core.forecast",
    "finguard_core.safety",
    "finguard_core.decision",
    "finguard_core.fx",
    "finguard_core.candidates",
    "finguard_core.commitments",
}


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_oracle_does_not_import_any_production_module():
    imported = _imported_names(ORACLE_FILE)
    violations = {name for name in imported if name in FORBIDDEN_ORACLE_IMPORTS or name.startswith("finguard_core.")}
    assert not violations, f"oracle imports production code: {violations}"


def test_no_production_module_imports_the_oracle_or_test_tree():
    violations: list[str] = []
    for path in sorted(CORE_ROOT.rglob("*.py")):
        for name in _imported_names(path):
            if name.startswith("tests.") or name == "tests":
                violations.append(f"{path.name} imports {name!r}")
    assert not violations, "production code imports the test tree:\n" + "\n".join(violations)
