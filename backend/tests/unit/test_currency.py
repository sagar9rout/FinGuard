"""Directional rounding (ADR 0006) and the currency registry (ADR 0009)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from finguard_core.currency import (
    Currency,
    RoundingDirection,
    default_currency_registry,
    higher_of,
    lower_of,
    round_money,
)


def test_default_registry_contains_the_five_starting_currencies():
    registry = default_currency_registry()
    assert set(registry) == {"INR", "USD", "EUR", "ZAR", "IDR"}
    assert all(c.exponent == 2 for c in registry.values())


def test_registry_is_not_an_invariant_a_custom_one_works_too():
    custom = {"JPY": Currency(code="JPY", exponent=0), "BHD": Currency(code="BHD", exponent=3)}
    assert round_money(Decimal("101.4"), custom["JPY"], RoundingDirection.UP) == Decimal("102")
    assert round_money(Decimal("101.4"), custom["BHD"], RoundingDirection.DOWN) == Decimal("101.400")


INR = Currency(code="INR", exponent=2)


def test_debit_conversion_rounds_up():
    assert round_money(Decimal("100.001"), INR, RoundingDirection.UP) == Decimal("100.01")


def test_credit_conversion_rounds_down():
    assert round_money(Decimal("100.009"), INR, RoundingDirection.DOWN) == Decimal("100.00")


def test_rounding_at_exact_boundary_is_unchanged():
    assert round_money(Decimal("100.00"), INR, RoundingDirection.UP) == Decimal("100.00")
    assert round_money(Decimal("100.00"), INR, RoundingDirection.DOWN) == Decimal("100.00")


def test_negative_currency_exponent_is_rejected():
    with pytest.raises(ValueError):
        Currency(code="XXX", exponent=-1)


def test_empty_currency_code_is_rejected():
    with pytest.raises(ValueError):
        Currency(code="", exponent=2)


def test_higher_of_and_lower_of():
    assert higher_of(Decimal("3"), Decimal("5")) == Decimal("5")
    assert higher_of(Decimal("5"), Decimal("3")) == Decimal("5")
    assert lower_of(Decimal("3"), Decimal("5")) == Decimal("3")
    assert lower_of(Decimal("5"), Decimal("3")) == Decimal("3")
