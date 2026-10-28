"""Helpers translating core test inputs into API wire JSON."""

from __future__ import annotations

import json
from typing import Any

from finguard_core.canonical import canonical_dict
from finguard_core.contracts import AnalysisInput


def to_wire(inp: AnalysisInput) -> dict[str, Any]:
    doc = canonical_dict(inp)
    prefs = doc["preferences"]
    prefs["category_min_allowed"] = [{"category": c, "minimum": m} for c, m in prefs["category_min_allowed"]]
    doc["currencies"] = [v for _k, v in sorted(doc.pop("currency_registry").items())]
    return doc  # type: ignore[no-any-return]


def to_body(inp: AnalysisInput) -> bytes:
    return json.dumps(to_wire(inp)).encode("utf-8")
