"""No calculation, FX stage, or decision rule may reference a specific
currency code by name (ADR 0009's currency-extensibility decision).

Statically scans finguard_core for string literals that look like a
3-4 letter currency code compared with ``==``/``!=``/``in`` against a
currency-shaped expression, outside the registry module itself (which
is where registering default currencies legitimately happens).
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parents[2] / "finguard_core"

# currency.py is the registry: it is the one place allowed to name the
# *default* registry's contents, per ADR 0009 ("the five currencies
# currently in use... are the default registry contents, not an
# invariant of the core logic"). contracts.py's EngineConfig.
# fx_pivot_currencies default ("USD", "EUR", per ADR 0003's stated
# default pivot order) is the same kind of thing: an overridable
# default *value*, not a currency-code check baked into any
# calculation, FX stage, or decision rule.
ALLOWED_FILES = {"currency.py", "contracts.py"}

KNOWN_CODES = {"INR", "USD", "EUR", "ZAR", "IDR"}


def _string_literals(tree: ast.AST) -> list[tuple[str, int]]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.value, node.lineno))
    return out


def test_no_currency_code_literals_outside_the_registry_module():
    violations: list[str] = []
    for path in sorted(CORE_ROOT.rglob("*.py")):
        if path.name in ALLOWED_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for value, lineno in _string_literals(tree):
            if value in KNOWN_CODES:
                violations.append(f"{path.name}:{lineno}: literal currency code {value!r}")
    assert not violations, (
        "a specific currency code is referenced outside currency.py, "
        "violating ADR 0009's extensibility decision:\n" + "\n".join(violations)
    )
