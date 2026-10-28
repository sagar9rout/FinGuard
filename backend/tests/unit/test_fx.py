"""Staged FX resolution (docs/engine/semantics.md Section 7; ADR 0003)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finguard_core.contracts import EngineConfig
from finguard_core.fx import FxStage, resolve_fx
from finguard_core.reason_codes import ReasonCode
from tests.support.builders import make_fx_rate

ON = date(2026, 1, 15)
CONFIG = EngineConfig()


def test_same_currency_is_rate_one_no_lookup_needed():
    result = resolve_fx((), "INR", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.EXACT
    assert result.rate == Decimal(1)


def test_exact_rate_on_the_date_is_used_first():
    rates = (
        make_fx_rate("USD", "INR", ON, Decimal("80")),
        make_fx_rate("USD", "INR", ON - timedelta(days=1), Decimal("79")),
    )
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.EXACT
    assert result.rate == Decimal("80")


def test_exact_rate_uses_inverse_when_only_reverse_pair_is_present():
    rates = (make_fx_rate("INR", "USD", ON, Decimal("0.0125")),)
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.EXACT
    assert result.used_inverse is True
    assert result.rate == Decimal(1) / Decimal("0.0125")
    assert ReasonCode.FX_INVERSE_USED in result.reason_codes


def test_falls_back_to_latest_prior_rate_within_window():
    rates = (make_fx_rate("USD", "INR", ON - timedelta(days=10), Decimal("79")),)
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.PRIOR
    assert result.rate == Decimal("79")
    assert result.age_days == 10
    assert ReasonCode.FX_PRIOR_RATE_USED in result.reason_codes


def test_prior_rate_outside_window_is_not_used():
    too_old = ON - timedelta(days=CONFIG.fx_prior_window_days + 1)
    rates = (make_fx_rate("USD", "INR", too_old, Decimal("79")),)
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is not FxStage.PRIOR


def test_prior_picks_the_most_recent_of_several_candidates():
    rates = (
        make_fx_rate("USD", "INR", ON - timedelta(days=10), Decimal("79")),
        make_fx_rate("USD", "INR", ON - timedelta(days=3), Decimal("81")),
    )
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.rate == Decimal("81")
    assert result.age_days == 3


def test_triangulates_through_pivot_when_no_direct_pair_exists():
    rates = (
        make_fx_rate("ZAR", "USD", ON, Decimal("0.05")),
        make_fx_rate("USD", "INR", ON, Decimal("80")),
    )
    result = resolve_fx(rates, "ZAR", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.TRIANGULATED
    assert result.rate == Decimal("0.05") * Decimal("80")
    assert ReasonCode.FX_TRIANGULATED in result.reason_codes


def test_triangulation_disagreement_resolves_to_less_favorable_for_a_debit():
    # Two pivots give two different implied ZAR->INR rates; for a debit
    # the least favorable (most expensive, i.e. largest) must win.
    config = EngineConfig(fx_pivot_currencies=("USD", "EUR"))
    rates = (
        make_fx_rate("ZAR", "USD", ON, Decimal("0.05")),
        make_fx_rate("USD", "INR", ON, Decimal("80")),  # implies 4.0
        make_fx_rate("ZAR", "EUR", ON, Decimal("0.045")),
        make_fx_rate("EUR", "INR", ON, Decimal("95")),  # implies 4.275
    )
    result = resolve_fx(rates, "ZAR", "INR", ON, config, is_debit=True)
    assert result.rate == Decimal("0.045") * Decimal("95")


def test_triangulation_disagreement_resolves_to_less_favorable_for_a_credit():
    # For a credit, least favorable means the smallest implied rate
    # (the user receives less home currency per unit of foreign credit).
    config = EngineConfig(fx_pivot_currencies=("USD", "EUR"))
    rates = (
        make_fx_rate("ZAR", "USD", ON, Decimal("0.05")),
        make_fx_rate("USD", "INR", ON, Decimal("80")),  # implies 4.0
        make_fx_rate("ZAR", "EUR", ON, Decimal("0.045")),
        make_fx_rate("EUR", "INR", ON, Decimal("95")),  # implies 4.275
    )
    result = resolve_fx(rates, "ZAR", "INR", ON, config, is_debit=False)
    assert result.rate == Decimal("0.05") * Decimal("80")


def test_pessimistic_bound_used_for_debit_when_nothing_else_resolves():
    far_back = ON - timedelta(days=100)
    rates = (make_fx_rate("USD", "INR", far_back, Decimal("70")),)
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.PESSIMISTIC_BOUND
    assert result.rate == Decimal("70")
    assert ReasonCode.FX_PESSIMISTIC_BOUND_USED in result.reason_codes


def test_pessimistic_bound_picks_least_favorable_within_window():
    rates = (
        make_fx_rate("USD", "INR", ON - timedelta(days=100), Decimal("70")),
        make_fx_rate("USD", "INR", ON - timedelta(days=150), Decimal("85")),
    )
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.rate == Decimal("85")


def test_pessimistic_bound_is_never_searched_beyond_its_window():
    beyond_window = ON - timedelta(days=CONFIG.fx_pessimistic_window_days + 1)
    rates = (make_fx_rate("USD", "INR", beyond_window, Decimal("999")),)
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.UNRESOLVED


def test_unresolvable_debit_blocks_certification_and_is_never_silently_dropped():
    result = resolve_fx((), "USD", "INR", ON, CONFIG, is_debit=True)
    assert result.stage is FxStage.UNRESOLVED
    assert result.rate is None
    assert result.blocks_certification is True
    assert ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION in result.reason_codes


def test_unresolvable_credit_is_excluded_not_blocking():
    result = resolve_fx((), "USD", "INR", ON, CONFIG, is_debit=False)
    assert result.stage is FxStage.UNRESOLVED
    assert result.rate is None
    assert result.blocks_certification is False
    assert ReasonCode.UNCONVERTIBLE_CREDIT_EXCLUDED in result.reason_codes


def test_pessimistic_bound_stage_is_never_used_for_a_credit():
    # Section 7, stage 4 is explicitly debit-only; a credit with nothing
    # resolvable in earlier stages goes straight to unresolved/excluded.
    far_back = ON - timedelta(days=100)
    rates = (make_fx_rate("USD", "INR", far_back, Decimal("70")),)
    result = resolve_fx(rates, "USD", "INR", ON, CONFIG, is_debit=False)
    assert result.stage is FxStage.UNRESOLVED
