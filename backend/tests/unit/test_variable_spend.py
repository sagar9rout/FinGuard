"""P0-4: weekly_p75_nearest_rank_v1 (docs/engine/semantics.md Section 5
step 5; ADR 0010): complete 7-day blocks only, zero-spend weeks count,
under 4 weeks uses the max weekly total, under 14 days no estimate, and
the actual parameters are exposed.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from finguard_core import analyze, forecast
from finguard_core.contracts import EngineConfig, EventStatus
from finguard_core.currency import default_currency_registry
from finguard_core.variable_spend import METHOD, estimate_variable_spend
from tests.support.builders import AS_OF, make_event, make_input, make_preferences

HOME = default_currency_registry()["INR"]
CONFIG = EngineConfig()


def spend(day_back, amount, category="groceries", **kw):
    return make_event(
        f"s{day_back}-{category}", AS_OF - timedelta(days=day_back), Decimal(amount), category=category, **kw
    )


def anchor(days_back):
    """A settled, non-variable event that fixes how much history exists."""
    return make_event(f"anchor{days_back}", AS_OF - timedelta(days=days_back), Decimal("1"), category="other")


def estimate(events, categories=("groceries",), config=CONFIG):
    return estimate_variable_spend(events, categories, AS_OF, "INR", HOME, config)


def test_under_14_days_of_history_produces_no_estimate():
    result = estimate([anchor(13), spend(3, "700")])
    assert result.info.estimated is False
    assert result.daily_amount is None
    assert result.info.history_days == 13
    assert {c.value for c in result.reason_codes} == {"VARIABLE_SPEND_INSUFFICIENT_HISTORY", "INSUFFICIENT_HISTORY"}


def test_exactly_14_days_gives_two_complete_weeks_and_uses_the_maximum():
    result = estimate([anchor(14), spend(2, "700"), spend(9, "70")])
    info = result.info
    assert info.estimated and info.complete_weeks_used == 2
    assert info.statistic == "max_weekly_total"
    assert info.weekly_totals == (Decimal("700"), Decimal("70"))
    assert info.weekly_value == Decimal("700")
    assert info.daily_amount == Decimal("100.00")


def test_only_complete_seven_day_blocks_are_used():
    # 20 days of history = 2 complete weeks; the 6 leftover days are ignored
    # even though they contain a large spend.
    result = estimate([anchor(20), spend(2, "70"), spend(9, "70"), spend(18, "99999")])
    assert result.info.complete_weeks_used == 2
    assert result.info.weekly_totals == (Decimal("70"), Decimal("70"))


def test_zero_spend_weeks_count_and_are_included_in_weeks_used():
    # 5 complete weeks; only the most recent week has spending.
    result = estimate([anchor(35), spend(2, "700")])
    info = result.info
    assert info.complete_weeks_used == 5
    assert info.zero_weeks == 4
    assert info.weekly_totals == (Decimal("700"), 0, 0, 0, 0)
    # nearest-rank P75 over [0,0,0,0,700]: rank ceil(0.75*5)=4 -> 0
    assert info.statistic == "p75_nearest_rank"
    assert info.weekly_value == 0
    assert info.daily_amount == Decimal("0.00")


def test_fewer_than_four_weeks_uses_max_even_when_zero_weeks_exist():
    result = estimate([anchor(21), spend(2, "700")])
    assert result.info.complete_weeks_used == 3
    assert result.info.zero_weeks == 2
    assert result.info.statistic == "max_weekly_total"
    assert result.info.weekly_value == Decimal("700")


def test_four_or_more_weeks_uses_nearest_rank_p75():
    amounts = ("10", "20", "30", "40")  # weekly totals, most recent first
    events = [anchor(28)] + [spend(2 + 7 * i, a) for i, a in enumerate(amounts)]
    info = estimate(events).info
    assert info.complete_weeks_used == 4
    assert info.statistic == "p75_nearest_rank"
    # sorted [10,20,30,40]; rank ceil(0.75*4)=3 -> 30
    assert info.weekly_value == Decimal("30")
    assert info.daily_amount == Decimal("4.29")  # 30/7 rounded UP to the minor unit


def test_lookback_caps_the_weeks_considered():
    config = EngineConfig(variable_spend_lookback_days=28)
    info = estimate([anchor(200), spend(2, "70")], config=config).info
    assert info.complete_weeks_used == 4
    assert info.lookback_days == 28
    assert info.history_days == 200


def test_week_boundaries_are_anchored_to_as_of():
    # day_back 7 is the last day of block 0 [as_of-7, as_of); day_back 8 starts block 1.
    info = estimate([anchor(14), spend(7, "100"), spend(8, "5")]).info
    assert info.weekly_totals == (Decimal("100"), Decimal("5"))


def test_only_configured_categories_settled_debits_before_as_of_count():
    events = [
        anchor(14),
        spend(2, "100"),
        spend(2, "999", category="other"),
        make_event(
            "pending", AS_OF - timedelta(days=3), Decimal("999"), category="groceries", status=EventStatus.PENDING
        ),
    ]
    assert estimate(events).info.weekly_totals == (Decimal("100"), Decimal("0"))


def test_no_configured_categories_means_no_estimate_and_no_warning():
    result = estimate([anchor(60)], categories=())
    assert result.info.estimated is False
    assert result.reason_codes == ()


def test_parameters_are_exposed_in_forecast_and_analysis_results():
    prefs = make_preferences(variable_spend_categories=("groceries",))
    inp = make_input(events=(anchor(28), spend(2, "70")), preferences=prefs)
    for info in (forecast(inp).variable_spend, analyze(inp).variable_spend):
        assert info.method == METHOD == "weekly_p75_nearest_rank_v1"
        assert info.categories == ("groceries",)
        assert info.lookback_days == CONFIG.variable_spend_lookback_days
        assert info.history_days == 28
        assert info.complete_weeks_used == 4
        assert info.currency == "INR"
        assert info.daily_amount == Decimal("10.00") or info.daily_amount is not None


def test_estimate_is_applied_to_every_day_of_the_window():
    prefs = make_preferences(variable_spend_categories=("groceries",))
    inp = make_input(events=(anchor(14), spend(2, "700")), preferences=prefs)
    series = forecast(inp).baseline_series
    daily = Decimal("100")
    assert series[0].low == inp.profile.current_available_balance - daily
    assert series[1].low == series[0].close - daily


@pytest.mark.parametrize("history", [0, 7, 13])
def test_short_history_never_silently_applies_an_estimate(history):
    prefs = make_preferences(variable_spend_categories=("groceries",))
    events = (anchor(history),) if history else ()
    result = analyze(make_input(events=events, preferences=prefs))
    assert result.variable_spend.estimated is False
    assert result.variable_spend.daily_amount is None
