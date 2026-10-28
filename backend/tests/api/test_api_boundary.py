"""Architecture boundary for PR-2: the API is a thin, stateless layer.
The core never depends on the API; the API has no persistence,
authentication or AI dependency (those are separate, later PRs).
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
CORE, API = BACKEND / "finguard_core", BACKEND / "finguard_api"

FORBIDDEN_IN_API = (
    "sqlalchemy",
    "psycopg2",
    "asyncpg",
    "alembic",
    "sqlite3",
    "jwt",
    "jose",
    "authlib",
    "clerk",
    "openai",
    "anthropic",
    "langchain",
    "tests",
)


def imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_core_never_imports_the_api_or_any_web_framework():
    for path in CORE.rglob("*.py"):
        for name in imports(path):
            root = name.split(".")[0]
            assert root not in {"finguard_api", "starlette", "fastapi", "pydantic", "uvicorn"}, (path.name, name)


def test_api_has_no_persistence_auth_or_ai_dependency():
    for path in API.rglob("*.py"):
        for name in imports(path):
            assert name.split(".")[0] not in FORBIDDEN_IN_API, (path.name, name)


def test_api_reaches_the_core_only_through_its_public_modules():
    allowed = {
        "finguard_core",
        "finguard_core.canonical",
        "finguard_core.contracts",
        "finguard_core.currency",
        "finguard_core.engine",
        "finguard_core.reason_codes",
        "finguard_core.validation",
    }
    for path in API.rglob("*.py"):
        for name in imports(path):
            if name.split(".")[0] == "finguard_core":
                assert name in allowed, (path.name, name)


def test_api_does_no_financial_computation():
    """The API must serialize the core's verdict, never derive one."""

    forbidden_calls = {"round_money", "resolve_fx", "convert_amount", "rank_candidates", "map_status"}
    for path in API.rglob("*.py"):
        names = {n.id for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Name)} | {
            n.attr for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Attribute)
        }
        assert not (names & forbidden_calls), (path.name, names & forbidden_calls)


def test_api_has_no_wall_clock_or_randomness():
    for path in API.rglob("*.py"):
        text = path.read_text()
        for needle in ("datetime.now", "date.today", "time.time", "uuid", "random."):
            assert needle not in text, (path.name, needle)
