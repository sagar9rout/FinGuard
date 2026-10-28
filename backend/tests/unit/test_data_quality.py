"""P0-5: insufficient variable-spend history is a visible data-quality
limitation and missing-information entry, never a silent assumption
under a ``high`` quality level (docs/engine/semantics.md Section 13;
ADR 0010).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from finguard_core import analyze
from finguard_core.contracts import AffordabilityStatus, DataQualityLevel
from tests.support.builders import AS_OF, make_event, make_input, make_preferences, make_profile, make_purchase


def _short_history_input(**kw):
    prefs = make_preferences(variable_spend_categories=("groceries",))
    events = (make_event("h", AS_OF - timedelta(days=5), Decimal("50"), category="groceries"),)
    return make_input(events=events, preferences=prefs, **kw)


def test_clean_input_with_enough_history_is_high_quality():
    prefs = make_preferences(variable_spend_categories=("groceries",))
    events = (
        make_event("a", AS_OF - timedelta(days=30), Decimal("50"), category="groceries"),
        make_event("b", AS_OF - timedelta(days=3), Decimal("50"), category="groceries"),
    )
    purchase = make_purchase(desired_completion_date=AS_OF + timedelta(days=30))
    result = analyze(make_input(events=events, preferences=prefs, purchase=purchase))
    assert result.data_quality is DataQualityLevel.HIGH
    assert result.missing_information == ()


def test_insufficient_history_lowers_quality_and_is_visible_everywhere():
    result = analyze(_short_history_input())
    assert result.data_quality is DataQualityLevel.LOW
    assumption_codes = {e.code for e in result.assumptions}
    issue_codes = {e.code for e in result.issues}
    assert "VARIABLE_SPEND_INSUFFICIENT_HISTORY" in assumption_codes
    assert "INSUFFICIENT_HISTORY" in issue_codes
    entry = next(e for e in result.missing_information if e.code == "VARIABLE_SPEND_INSUFFICIENT_HISTORY")
    assert entry.subject_ids == ("groceries",)
    assert result.variable_spend.estimated is False


def test_a_certified_affordable_result_still_carries_the_limitation():
    result = analyze(_short_history_input())
    assert result.certified is True
    assert result.status is AffordabilityStatus.AFFORDABLE_NOW
    assert result.data_quality is not DataQualityLevel.HIGH
    entry = next(e for e in result.missing_information if e.code == "VARIABLE_SPEND_INSUFFICIENT_HISTORY")
    assert entry.impact.value == "could_change_decision"


def test_impact_is_informational_once_the_answer_cannot_get_better():
    # A purchase that is unaffordable with zero modelled variable spend
    # stays unaffordable if the unmodelled spend turns out positive.
    inp = _short_history_input(
        profile=make_profile(current_available_balance=Decimal("3100")),
        purchase=make_purchase(amount=Decimal("90000"), allows_partial_payment=False),
    )
    result = analyze(inp)
    assert result.status is AffordabilityStatus.NOT_AFFORDABLE
    entry = next(e for e in result.missing_information if e.code == "VARIABLE_SPEND_INSUFFICIENT_HISTORY")
    assert entry.impact.value == "informational"


def test_baseline_breach_never_lowers_data_quality():
    inp = make_input(
        profile=make_profile(current_available_balance=Decimal("1000")),
        preferences=make_preferences(variable_spend_categories=()),
    )
    result = analyze(inp)
    assert result.baseline_summary.below_reserve
    assert result.data_quality is DataQualityLevel.HIGH


def test_window_truncation_never_lowers_data_quality():
    inp = make_input(
        purchase=make_purchase(desired_completion_date=AS_OF + timedelta(days=400)),
        preferences=make_preferences(variable_spend_categories=()),
    )
    result = analyze(inp)
    assert result.certifiable_window.truncated
    assert result.data_quality is DataQualityLevel.HIGH


def test_blocked_certification_is_insufficient():
    from tests.support.builders import make_input_with_unconvertible_debit

    result = analyze(make_input_with_unconvertible_debit())
    assert result.data_quality is DataQualityLevel.INSUFFICIENT
    assert result.certified is False
