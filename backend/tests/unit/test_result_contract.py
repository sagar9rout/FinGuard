"""P0-2: the complete locked result contract — certification window,
baseline summary, considered commitments, engine-config echo and FX
usage — present, correct, and consistent with the series.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from finguard_core import analyze, forecast
from finguard_core.contracts import (
    CommitmentStatus,
    CommitmentTier,
    EngineConfig,
    EventStatus,
)
from tests.support.builders import (
    AS_OF,
    make_commitment,
    make_event,
    make_fx_rate,
    make_input,
    make_preferences,
    make_profile,
    make_purchase,
)
from tests.support.scenarios import rich_scenario

NO_VAR = make_preferences(variable_spend_categories=())


def test_certification_window_has_every_locked_field():
    deadline = AS_OF + timedelta(days=20)
    result = analyze(make_input(purchase=make_purchase(desired_completion_date=deadline), preferences=NO_VAR))
    w = result.certifiable_window
    assert w.start == AS_OF
    assert w.horizon_end == AS_OF + timedelta(days=90)
    assert w.deadline == deadline
    assert w.effective_end == AS_OF + timedelta(days=90)  # max(horizon_end, deadline)
    assert w.truncated is False
    assert w.max_window_days == 180


def test_deadline_beyond_max_window_is_truncated_and_reported():
    deadline = AS_OF + timedelta(days=400)
    result = analyze(make_input(purchase=make_purchase(desired_completion_date=deadline), preferences=NO_VAR))
    w = result.certifiable_window
    assert w.effective_end == AS_OF + timedelta(days=180)
    assert w.truncated is True and w.deadline == deadline
    assert "DEADLINE_BEYOND_CERTIFIABLE_WINDOW" in {e.code for e in result.issues}
    assert "CERTIFICATION_LIMITED_TO_WINDOW" in {e.code for e in result.assumptions}


def test_absent_deadline_is_none_and_defaulted():
    result = analyze(make_input(preferences=NO_VAR))
    assert result.certifiable_window.deadline is None
    assert "DEADLINE_DEFAULTED" in {e.code for e in result.assumptions}


def test_forecast_result_carries_the_same_contract_fields():
    inp = rich_scenario()
    fc, an = forecast(inp), analyze(inp)
    assert fc.certifiable_window == an.certifiable_window
    assert fc.baseline_summary == an.baseline_summary
    assert fc.considered_commitments == an.considered_commitments
    assert fc.engine_config_echo == an.engine_config_echo
    assert fc.fx_usage == an.fx_usage
    assert fc.variable_spend == an.variable_spend


def test_baseline_summary_matches_the_series_exactly():
    inp = rich_scenario()
    series = forecast(inp).baseline_series
    reserve = inp.profile.minimum_balance_to_keep
    s = analyze(inp).baseline_summary
    below = [d for d in series if d.low < reserve]
    assert s.below_reserve == bool(below)
    assert s.days_below == len(below)
    assert s.first_breach_date == (below[0].day if below else None)
    assert s.last_breach_date == (below[-1].day if below else None)
    lowest = min(series, key=lambda d: (d.low, d.day))
    assert s.lowest is not None and (s.lowest.day, s.lowest.balance) == (lowest.day, lowest.low)
    assert s.max_shortfall == max(Decimal(0), reserve - lowest.low)


def test_baseline_summary_when_never_below_reserve():
    s = analyze(make_input(preferences=NO_VAR)).baseline_summary
    assert (s.below_reserve, s.first_breach_date, s.last_breach_date, s.days_below) == (False, None, None, 0)
    assert s.max_shortfall == 0
    assert s.lowest is not None


def test_baseline_summary_when_below_reserve_from_day_one():
    inp = make_input(profile=make_profile(current_available_balance=Decimal("2000")), preferences=NO_VAR)
    s = analyze(inp).baseline_summary
    assert s.below_reserve and s.first_breach_date == AS_OF
    assert s.last_breach_date == AS_OF + timedelta(days=90)
    assert s.days_below == 91
    assert s.max_shortfall == Decimal("1000")


def test_considered_commitments_report_every_status():
    lapsed = make_commitment(
        "c-lapsed", category="gym", anchor_day=3, tier=CommitmentTier.DETECTED, last_seen=AS_OF - timedelta(days=400)
    )
    base = rich_scenario()
    from dataclasses import replace

    inp = replace(base, commitments=(*base.commitments, lapsed))
    by_id = {c.commitment_id: c for c in analyze(inp).considered_commitments}
    assert set(by_id) == {c.commitment_id for c in inp.commitments}
    assert by_id["c-rent"].status is CommitmentStatus.APPLIED
    assert by_id["c-rent-dup"].status is CommitmentStatus.SUPPRESSED_OVERLAP
    assert by_id["c-rent-dup"].suppressed_by == "c-rent"
    assert by_id["c-sal-detected"].status is CommitmentStatus.UNCONFIRMED_INCOME_EXCLUDED
    assert by_id["c-sal-confirmed"].status is CommitmentStatus.APPLIED
    assert by_id["c-gym-rejected"].status in (CommitmentStatus.REJECTED, CommitmentStatus.SUPPRESSED_BY_USER_REJECTION)
    assert by_id["c-lapsed"].status is CommitmentStatus.LAPSED
    for c in by_id.values():
        if c.status is not CommitmentStatus.APPLIED:
            assert c.occurrences_projected == 0
    assert by_id["c-rent"].occurrences_projected >= 1
    assert by_id["c-net"].amount_per_occurrence == Decimal("650")  # debit: higher of median/recent
    assert by_id["c-sal-confirmed"].amount_per_occurrence == Decimal("450")  # credit: lower


def test_engine_config_is_echoed_verbatim():
    config = EngineConfig(horizon_days=45, max_window_days=120, fx_prior_window_days=30)
    result = analyze(make_input(config=config, preferences=NO_VAR))
    assert result.engine_config_echo == config
    assert result.certifiable_window.horizon_end == AS_OF + timedelta(days=45)
    assert result.certifiable_window.max_window_days == 120
    assert analyze(make_input(preferences=NO_VAR)).engine_config_echo == EngineConfig()


def test_fx_usage_reports_pair_stage_count_and_worst_age():
    events = (
        make_event("u1", AS_OF + timedelta(days=2), Decimal("10"), currency="USD", status=EventStatus.SCHEDULED),
        make_event("u2", AS_OF + timedelta(days=5), Decimal("10"), currency="USD", status=EventStatus.SCHEDULED),
    )
    rates = (make_fx_rate("USD", "INR", AS_OF - timedelta(days=10), Decimal("83")),)
    result = analyze(make_input(events=events, fx_rates=rates, preferences=NO_VAR))
    usage = [u for u in result.fx_usage if (u.base_currency, u.quote_currency) == ("USD", "INR")]
    assert len(usage) == 1
    u = usage[0]
    assert u.stage == "prior"
    assert u.count == 2 and u.direction == "debit"
    assert u.worst_age_days == 15  # conversion on day +5 using the day -10 rate
    assert u.window_days is None and u.candidates_considered is None


def test_pessimistic_usage_reports_window_candidates_and_worst_rate():
    events = (make_event("u1", AS_OF + timedelta(days=2), Decimal("10"), currency="USD", status=EventStatus.SCHEDULED),)
    rates = (
        make_fx_rate("USD", "INR", AS_OF - timedelta(days=100), Decimal("80")),
        make_fx_rate("USD", "INR", AS_OF - timedelta(days=90), Decimal("86")),
    )
    result = analyze(make_input(events=events, fx_rates=rates, preferences=NO_VAR))
    pess = [u for u in result.fx_usage if u.stage == "pessimistic_bound"]
    assert len(pess) == 1
    u = pess[0]
    assert (u.base_currency, u.quote_currency, u.direction) == ("USD", "INR", "debit")
    assert u.window_days == 180
    assert u.candidates_considered == 2
    assert u.worst_rate == Decimal("86")  # least favourable for a debit
    assert "FX_PESSIMISTIC_BOUND_USED" in {e.code for e in result.assumptions}
    assert result.data_quality.value == "low"


def test_exact_and_identity_conversions_are_not_listed_as_fallbacks():
    result = analyze(make_input(preferences=NO_VAR))
    assert result.fx_usage == ()
