"""Canonical serialization and input hashing (ADR 0001; docs/engine/
semantics.md, "canonical serialization and an input hash, so identical
inputs (regardless of collection ordering) produce identical,
comparable output").

Rules that make this deterministic and byte-identical for equal inputs:

- No wall-clock reads, no random UUIDs, no non-deterministic ordering of
  any kind appear anywhere in this module.
- Dataclasses are converted field-by-field, in declaration order, which
  is fixed by the source code rather than by dict/set iteration order.
- ``Decimal`` values are rendered through :func:`canonical_decimal`,
  which normalizes before formatting, so ``Decimal("1.50")`` and
  ``Decimal("1.5")`` (equal in value) serialize identically.
- Collections whose order is not semantically meaningful are sorted by
  their own canonical JSON text before being joined, so the same set of
  events in a different list order hashes identically. Collections whose
  order *is* meaningful (a payment schedule, a candidate list) are left
  as given.
- The resulting JSON text uses sorted object keys and no insignificant
  whitespace, then is hashed with SHA-256.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from finguard_core.contracts import AnalysisInput

# Dataclass fields that hold an unordered collection: sort these by their
# own canonical representation before serializing. Fields not listed here
# keep caller-supplied order because that order is semantically meaningful
# (a payment schedule, a list of candidates, a list of breach days).
_UNORDERED_COLLECTION_FIELDS = frozenset(
    {
        "events",
        "commitments",
        "evidence_facts",
        "payment_options",
        "fx_rates",
        "accepted_methods",
        "stoppable_categories",
        "reducible_categories",
        "protected_categories",
        "category_min_allowed",
        "variable_spend_categories",
    }
)


def canonical_decimal(value: Decimal) -> str:
    """A decimal's canonical text form: the same for any two ``Decimal``
    instances of equal mathematical value, never using exponential
    notation.
    """

    if value == 0:
        return "0"
    normalized = value.normalize()
    return format(normalized, "f")


def _canonical_value(value: Any, field_name: str | None = None) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if dataclasses.is_dataclass(value):
        return {
            f.name: _canonical_value(getattr(value, f.name), f.name)
            for f in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        # Only currency_registry is a Mapping in the contracts; it's keyed
        # by currency code, so sorting by key is both deterministic and
        # meaningful (not merely order-independent-by-accident).
        return {
            str(k): _canonical_value(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, (tuple, list)):
        items = [_canonical_value(item) for item in value]
        if field_name in _UNORDERED_COLLECTION_FIELDS:
            items.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        return items
    raise TypeError(f"Cannot canonicalize value of type {type(value)!r}")


def canonical_dict(value: Any) -> Any:
    """The canonical, JSON-compatible structure of ``value`` (the exact
    structure ``canonical_json`` serializes): plain dicts, lists, strings,
    ints, bools and None only. Money is canonical decimal text.
    """

    return _canonical_value(value)


def canonical_json(value: Any) -> str:
    """Render any contract object (or nested structure of them) as
    canonical JSON text: sorted keys, no whitespace, deterministic
    ordering for unordered collections.
    """

    canonical = _canonical_value(value)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def input_hash(analysis_input: Any) -> str:
    """SHA-256 hex digest of ``analysis_input``'s canonical JSON text.
    Identical canonical inputs (including re-ordered unordered
    collections) always produce the same digest; no field of this
    computation is a timestamp, a random value, or otherwise
    non-deterministic.
    """

    text = canonical_json(analysis_input)
    return sha256(text.encode("utf-8")).hexdigest()


def result_hash(result: Any) -> str:
    """SHA-256 hex digest of a result's canonical JSON text. A result
    contains no timestamps, random identifiers, or unordered iteration,
    so equal canonical inputs yield byte-identical canonical results.
    """

    return sha256(canonical_json(result).encode("utf-8")).hexdigest()


def normalize_input(analysis_input: AnalysisInput) -> AnalysisInput:
    """Return ``analysis_input`` with every unordered collection put in
    its canonical order, so no downstream emission order (reasons,
    assumptions, candidates, fx usage) can depend on caller ordering.
    Ordered collections (payment schedules, ``fx_pivot_currencies``,
    whose order is a documented tie-break) are left untouched.
    Identifiers must already be unique (see ``validation``).
    """

    prefs = analysis_input.preferences
    return dataclasses.replace(
        analysis_input,
        events=tuple(sorted(analysis_input.events, key=lambda e: e.event_id)),
        commitments=tuple(sorted(analysis_input.commitments, key=lambda c: c.commitment_id)),
        evidence_facts=tuple(sorted(analysis_input.evidence_facts, key=lambda f: f.fact_id)),
        payment_options=tuple(sorted(analysis_input.payment_options, key=lambda o: o.option_id)),
        fx_rates=tuple(
            sorted(
                analysis_input.fx_rates,
                key=lambda r: (r.base_currency, r.quote_currency, r.rate_date, canonical_decimal(r.rate)),
            )
        ),
        preferences=dataclasses.replace(
            prefs,
            accepted_methods=tuple(sorted(set(prefs.accepted_methods), key=lambda m: m.value)),
            stoppable_categories=tuple(sorted(set(prefs.stoppable_categories))),
            reducible_categories=tuple(sorted(set(prefs.reducible_categories))),
            protected_categories=tuple(sorted(set(prefs.protected_categories))),
            variable_spend_categories=tuple(sorted(set(prefs.variable_spend_categories))),
            category_min_allowed=tuple(
                sorted(prefs.category_min_allowed, key=lambda p: (p[0], canonical_decimal(p[1])))
            ),
        ),
    )
