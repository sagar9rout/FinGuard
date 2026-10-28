"""Carried-forward invariant (PR-1 approval): the core must NEVER consume
an FX rate dated after the conversion date, at any resolution stage.
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from finguard_core import analyze
from finguard_core.canonical import canonical_json
from finguard_core.contracts import EngineConfig, EventStatus, FxRateEntry
from finguard_core.fx import FxStage, resolve_fx
from tests.support.builders import AS_OF, make_event, make_fx_rate, make_input, make_preferences

CONFIG = EngineConfig()
ON = AS_OF + timedelta(days=10)
NO_VAR = make_preferences(variable_spend_categories=())


def _body(result):
    """Canonical result bytes ignoring input_hash (the inputs differ by the future row)."""
    return canonical_json(replace(result, input_hash=""))


def rate(base, quote, days_from_on, value):
    return make_fx_rate(base, quote, ON + timedelta(days=days_from_on), Decimal(value))


def test_only_future_rates_never_resolve_a_debit_or_credit():
    future = (rate("USD", "INR", 1, "1"), rate("USD", "INR", 30, "999"))
    debit = resolve_fx(future, "USD", "INR", ON, CONFIG, True)
    credit = resolve_fx(future, "USD", "INR", ON, CONFIG, False)
    assert debit.stage is FxStage.UNRESOLVED and debit.blocks_certification
    assert credit.stage is FxStage.UNRESOLVED and not credit.blocks_certification


@pytest.mark.parametrize("future_value", ["0.0001", "1", "1000000"])
def test_a_future_rate_never_changes_the_result_at_any_stage(future_value):
    scenarios = {
        "exact": [rate("USD", "INR", 0, "83")],
        "prior": [rate("USD", "INR", -10, "83")],
        "inverse_prior": [rate("INR", "USD", -10, "0.012")],
        "triangulated": [rate("USD", "EUR", -5, "0.9"), rate("EUR", "INR", -5, "90")],
        "pessimistic": [rate("USD", "INR", -100, "80"), rate("USD", "INR", -90, "86")],
        "unresolved": [],
    }
    for name, past in scenarios.items():
        poison = [
            rate("USD", "INR", 1, future_value),
            rate("INR", "USD", 2, future_value),
            rate("USD", "EUR", 3, future_value),
            rate("EUR", "INR", 4, future_value),
            rate("EUR", "USD", 5, future_value),
        ]
        for is_debit in (True, False):
            clean = resolve_fx(tuple(past), "USD", "INR", ON, CONFIG, is_debit)
            dirty = resolve_fx(tuple(past) + tuple(poison), "USD", "INR", ON, CONFIG, is_debit)
            assert clean == dirty, (name, is_debit)


def test_randomized_tables_resolve_identically_with_or_without_future_rows():
    rng = random.Random(20261007)
    codes = ("USD", "EUR", "INR", "ZAR")
    for _ in range(300):
        rows: list[FxRateEntry] = []
        for _ in range(rng.randint(0, 12)):
            base, quote = rng.sample(codes, 2)
            offset = rng.randint(-200, 60)
            rows.append(rate(base, quote, offset, str(Decimal(rng.randint(1, 20000)) / 100)))
        unique: dict[tuple[str, str, object], FxRateEntry] = {}
        for r in rows:
            unique[(r.base_currency, r.quote_currency, r.rate_date)] = r
        table = tuple(unique.values())
        past_only = tuple(r for r in table if r.rate_date <= ON)
        base, quote = rng.sample(codes, 2)
        for is_debit in (True, False):
            assert resolve_fx(table, base, quote, ON, CONFIG, is_debit) == resolve_fx(
                past_only, base, quote, ON, CONFIG, is_debit
            )


def test_end_to_end_future_rate_cannot_make_a_debit_cheaper_or_unblock_certification():
    event = make_event("usd-bill", ON, Decimal("100"), currency="USD", status=EventStatus.SCHEDULED)
    base = make_input(events=(event,), preferences=NO_VAR)
    with_future = replace(base, fx_rates=(make_fx_rate("USD", "INR", ON + timedelta(days=1), Decimal("0.0001")),))
    blocked = analyze(with_future)
    assert blocked.certified is False
    assert _body(blocked) == _body(analyze(base))


def test_end_to_end_future_rate_cannot_inflate_a_credit():
    from finguard_core.contracts import EventDirection

    pay = make_event(
        "pay", ON, Decimal("100"), currency="USD", direction=EventDirection.CREDIT, status=EventStatus.SCHEDULED
    )
    base = make_input(events=(pay,), preferences=NO_VAR)
    with_future = replace(base, fx_rates=(make_fx_rate("USD", "INR", ON + timedelta(days=1), Decimal("1000000")),))
    assert _body(analyze(with_future)) == _body(analyze(base))
