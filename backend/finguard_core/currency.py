"""Currency registry and directional rounding (docs/engine/semantics.md
Section 2; ADR 0006; ADR 0009).

Currency is a registered ``(code, exponent)`` pair, never a hardcoded
enumeration. No other module in this package may reference a specific
currency code in a conditional — that would violate ADR 0009's
extensibility decision and is checked by
``backend/tests/contract/test_no_hardcoded_currency.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Currency:
    """A registered currency: an ISO-style code and its minor-unit exponent.

    ``exponent`` is the number of digits after the decimal point in the
    currency's minor unit (2 for cents-style currencies). It is a registry
    property, not a core-logic assumption.
    """

    code: str
    exponent: int

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Currency code must be non-empty")
        if self.exponent < 0:
            raise ValueError("Currency exponent must be >= 0")


def default_currency_registry() -> Mapping[str, Currency]:
    """The default registry contents (ADR 0009): a starting set, not an
    invariant of the engine. Callers may supply any registry via
    ``AnalysisInput.currency_registry``.
    """

    codes = ("INR", "USD", "EUR", "ZAR", "IDR")
    return {code: Currency(code=code, exponent=2) for code in codes}


class RoundingDirection(StrEnum):
    """Which way a monetary boundary rounds (ADR 0006). Every rounding
    decision in the system is pessimistic: it never makes a plan look
    more affordable than it is.
    """

    UP = "up"
    DOWN = "down"


def round_money(amount: Decimal, currency: Currency, direction: RoundingDirection) -> Decimal:
    """Round ``amount`` to ``currency``'s minor unit in the given
    direction. This is the *only* rounding function in the engine; it is
    called only at the documented output boundaries listed in
    docs/engine/semantics.md Section 2 — never at intermediate steps.
    """

    quantum = Decimal(1).scaleb(-currency.exponent)
    rounding = ROUND_UP if direction is RoundingDirection.UP else ROUND_DOWN
    return amount.quantize(quantum, rounding=rounding)


def higher_of(a: Decimal, b: Decimal) -> Decimal:
    return a if a >= b else b


def lower_of(a: Decimal, b: Decimal) -> Decimal:
    return a if a <= b else b
