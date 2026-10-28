"""Hard structural validation (P0-6, ADR 0010)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from finguard_core import analyze, forecast, validate_input
from finguard_core.contracts import (
    CandidateType,
    EngineConfig,
    EvidenceFact,
    FactConfirmation,
    FactDirection,
    FactKind,
    PaymentOption,
    PaymentOptionSchedule,
)
from finguard_core.validation import InputValidationError
from tests.support.builders import (
    AS_OF,
    make_commitment,
    make_event,
    make_fact,
    make_fx_rate,
    make_input,
    make_installment_option,
    make_minimal_input,
    make_preferences,
    make_profile,
    make_purchase,
)


def violations(inp):
    with pytest.raises(InputValidationError) as info:
        validate_input(inp)
    return info.value.violations


def test_well_formed_input_passes():
    assert validate_input(make_minimal_input()) == ()


def test_analyze_and_forecast_both_validate():
    bad = make_input(events=(make_event("a", AS_OF, Decimal("1")), make_event("a", AS_OF, Decimal("2"))))
    with pytest.raises(InputValidationError):
        analyze(bad)
    with pytest.raises(InputValidationError):
        forecast(bad)


def test_duplicate_ids_are_rejected_for_every_collection():
    fact = make_fact(
        "f", direction=FactDirection.REDUCING, confirmation=FactConfirmation.CONFIRMED,
        kind=FactKind.EXCLUSION, target_event_id="e1",
    )
    option = make_installment_option("o", ((AS_OF + timedelta(days=1), Decimal("10")),))
    inp = make_input(
        events=(make_event("e1", AS_OF, Decimal("1")), make_event("e1", AS_OF, Decimal("1"))),
        commitments=(make_commitment("c"), make_commitment("c", category="other")),
        evidence_facts=(fact, fact),
        payment_options=(option, option),
    )
    found = violations(inp)
    expected_rules = (
        "event_id_duplicate:e1",
        "commitment_id_duplicate:c",
        "fact_id_duplicate:f",
        "option_id_duplicate:o",
    )
    for expected in expected_rules:
        assert expected in found


def test_empty_ids_are_rejected():
    assert "event_id_empty:" in violations(make_input(events=(make_event("", AS_OF, Decimal("1")),)))


def test_conflicting_duplicate_fx_rows_are_rejected_identical_ones_are_not():
    a = make_fx_rate("USD", "INR", AS_OF, Decimal("80"))
    b = make_fx_rate("USD", "INR", AS_OF, Decimal("81"))
    assert any(v.startswith("fx_rate_conflict:") for v in violations(make_input(fx_rates=(a, b))))
    assert validate_input(make_input(fx_rates=(a, a))) == ()


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")])
def test_invalid_fx_rates_are_rejected(rate):
    found = violations(make_input(fx_rates=(make_fx_rate("USD", "INR", AS_OF, rate),)))
    assert any(v.startswith("fx_rate_invalid:") for v in found)


def test_fx_rate_between_same_currency_is_rejected():
    found = violations(make_input(fx_rates=(make_fx_rate("INR", "INR", AS_OF, Decimal("1")),)))
    assert any(v.startswith("fx_rate_same_currency:") for v in found)


def test_negative_and_non_finite_monetary_values_are_rejected():
    assert "event_amount_negative:e" in violations(make_input(events=(make_event("e", AS_OF, Decimal("-1")),)))
    assert "event_amount_invalid:e" in violations(make_input(events=(make_event("e", AS_OF, Decimal("NaN")),)))
    assert "purchase_amount_not_positive:purchase" in violations(
        make_input(purchase=make_purchase(amount=Decimal("0")))
    )
    assert "minimum_balance_negative:profile" in violations(
        make_input(profile=make_profile(minimum_balance_to_keep=Decimal("-1")))
    )


def test_a_negative_opening_balance_is_allowed_overdraft_but_non_finite_is_not():
    assert validate_input(make_input(profile=make_profile(current_available_balance=Decimal("-50")))) == ()
    found = violations(make_input(profile=make_profile(current_available_balance=Decimal("Infinity"))))
    assert "balance_invalid:profile" in found


def test_documented_arithmetic_safety_bounds():
    huge = Decimal(10) ** 15
    assert "event_amount_invalid:e" in violations(make_input(events=(make_event("e", AS_OF, huge),)))
    assert "event_amount_invalid:e" in violations(
        make_input(events=(make_event("e", AS_OF, Decimal("0.00000000001")),))
    )


def test_unregistered_currency_is_rejected():
    assert "currency_unregistered:XXX" in violations(
        make_input(events=(make_event("e", AS_OF, Decimal("1"), currency="XXX"),))
    )


def test_invalid_schedules_are_rejected():
    d = AS_OF + timedelta(days=1)

    def option(oid, steps):
        return PaymentOption(
            option_id=oid,
            method=CandidateType.INSTALLMENTS,
            schedule=tuple(PaymentOptionSchedule(due_date=due, amount=amt, currency="INR") for due, amt in steps),
            stated_total=Decimal("10"),
            stated_total_currency="INR",
        )

    empty = option("empty", ())
    zero = option("zero", ((d, Decimal("0")),))
    unordered = option("unordered", ((d + timedelta(days=5), Decimal("5")), (d, Decimal("5"))))
    same_day = option("same_day", ((d, Decimal("5")), (d, Decimal("5"))))
    found = violations(make_input(payment_options=(empty, zero, unordered, same_day)))
    assert "option_schedule_empty:empty" in found
    assert "option_installment_not_positive:zero" in found
    assert "option_dates_not_strictly_increasing:unordered" in found
    assert "option_dates_not_strictly_increasing:same_day" in found


def test_mixed_currency_option_is_rejected():
    d = AS_OF + timedelta(days=1)
    option = PaymentOption(
        option_id="mixed",
        method=CandidateType.INSTALLMENTS,
        schedule=(
            PaymentOptionSchedule(due_date=d, amount=Decimal("5"), currency="INR"),
            PaymentOptionSchedule(due_date=d + timedelta(days=1), amount=Decimal("5"), currency="USD"),
        ),
        stated_total=Decimal("10"),
        stated_total_currency="INR",
    )
    assert "option_mixed_currency:mixed" in violations(make_input(payment_options=(option,)))


def test_negative_installment_term_is_rejected():
    prefs = make_preferences(max_installment_term_days=-1)
    assert "installment_term_negative:preferences" in violations(make_input(preferences=prefs))


def test_invalid_minimum_amounts_are_rejected():
    negative = make_event("n", AS_OF, Decimal("10"), is_reducible=True, minimum_allowed_amount=Decimal("-1"))
    too_big = make_event("b", AS_OF, Decimal("10"), is_reducible=True, minimum_allowed_amount=Decimal("11"))
    orphan = make_event("o", AS_OF, Decimal("10"), minimum_allowed_amount=Decimal("1"))
    found = violations(make_input(events=(negative, too_big, orphan)))
    assert "event_minimum_allowed_negative:n" in found
    assert "event_minimum_allowed_exceeds_amount:b" in found
    assert "event_minimum_allowed_without_reducible:o" in found
    prefs = make_preferences(category_min_allowed=(("x", Decimal("-1")), ("y", Decimal("1")), ("y", Decimal("2"))))
    found = violations(make_input(preferences=prefs))
    assert "category_minimum_negative:x" in found
    assert "category_minimum_duplicate:y" in found


def test_commitment_structural_violations():
    bad = replace(
        make_commitment("c"), confidence=Decimal("1.5"), anchor_day=0, period_days=0, occurrences=-1,
        amount_median=Decimal("-1"),
    )
    found = violations(make_input(commitments=(bad,)))
    for expected in (
        "commitment_confidence_out_of_range:c",
        "commitment_anchor_day_invalid:c",
        "commitment_period_invalid:c",
        "commitment_occurrences_negative:c",
        "commitment_amount_negative:c",
    ):
        assert expected in found


def test_fact_structural_violations():
    base = dict(direction=FactDirection.REDUCING, confirmation=FactConfirmation.CONFIRMED)
    unknown = make_fact("unknown", kind=FactKind.EXCLUSION, target_event_id="missing", **base)
    no_amount = make_fact("noamt", kind=FactKind.AMOUNT_CHANGE, target_event_id="e", **base)
    no_date = make_fact("nodate", kind=FactKind.DATE_CHANGE, target_event_id="e", **base)
    commitment_target = EvidenceFact(
        fact_id="ctarget", direction=FactDirection.REDUCING, confirmation=FactConfirmation.CONFIRMED,
        kind=FactKind.EXCLUSION, target_event_id="e", target_commitment_id="c",
    )
    found = violations(
        make_input(
            events=(make_event("e", AS_OF, Decimal("1")),),
            evidence_facts=(unknown, no_amount, no_date, commitment_target),
        )
    )
    assert "fact_unknown_target:unknown" in found
    assert "fact_amount_change_without_amount:noamt" in found
    assert "fact_date_change_without_date:nodate" in found
    assert "fact_commitment_target_unsupported:ctarget" in found


def test_balance_snapshot_from_the_future_is_rejected():
    profile = make_profile(balance_as_of=AS_OF + timedelta(days=1))
    assert "balance_as_of_after_as_of:profile" in violations(make_input(profile=profile))


def test_inconsistent_recurrence_group_is_rejected():
    a = make_event("a", AS_OF, Decimal("1"), recurrence_group_id="g", category="x")
    b = make_event("b", AS_OF, Decimal("1"), recurrence_group_id="g", category="y")
    assert "recurrence_group_inconsistent:g" in violations(make_input(events=(a, b)))


def test_config_violations():
    cfg = EngineConfig(horizon_days=0, fx_prior_window_days=-1, commitment_overlap_amount_tolerance=Decimal("2"))
    found = violations(make_input(config=cfg))
    assert "config_not_positive:horizon_days" in found
    assert "config_negative:fx_prior_window_days" in found
    assert "config_out_of_range:commitment_overlap_amount_tolerance" in found


def test_violations_are_sorted_and_deterministic():
    inp = make_input(
        events=(make_event("b", AS_OF, Decimal("-1")), make_event("a", AS_OF, Decimal("-1"))),
    )
    assert violations(inp) == tuple(sorted(violations(inp)))
