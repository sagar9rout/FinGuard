"""P0-3 / ADR 0005: detected-but-unconfirmed recurring income MUST NOT
enter spendable cash. Only explicitly supplied scheduled credits,
confirmed/user-declared commitments and confirmed facts may contribute
future income.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from finguard_core import analyze, forecast
from finguard_core.contracts import (
    AffordabilityStatus,
    CommitmentStatus,
    CommitmentTier,
    EventDirection,
    EventStatus,
    FactConfirmation,
    FactDirection,
    FactKind,
)
from tests.support.builders import (
    AS_OF,
    make_commitment,
    make_event,
    make_fact,
    make_input,
    make_profile,
    make_purchase,
)

# Balance 5,000, reserve 3,000, purchase 4,000 today: unsafe on its own
# (leaves 1,000). A 20,000 salary arriving on day 10 WOULD rescue a later
# payment, but only if that salary is allowed to count.
PROFILE = make_profile(current_available_balance=Decimal("5000"), minimum_balance_to_keep=Decimal("3000"))
PURCHASE = make_purchase(
    amount=Decimal("4000"), desired_completion_date=AS_OF + timedelta(days=60), allows_partial_payment=False
)


def _salary(tier: CommitmentTier):
    return make_commitment(
        "salary",
        direction=EventDirection.CREDIT,
        category="salary",
        tier=tier,
        anchor_day=(AS_OF + timedelta(days=10)).day,
        amount_median=Decimal("20000"),
        amount_most_recent=Decimal("20000"),
        last_seen=AS_OF - timedelta(days=20),
    )


def _analyze_with(*commitments, events=(), facts=()):
    return analyze(
        make_input(
            profile=PROFILE,
            purchase=PURCHASE,
            commitments=tuple(commitments),
            events=tuple(events),
            evidence_facts=tuple(facts),
        )
    )


def test_baseline_without_any_income_cannot_afford_it_now():
    result = _analyze_with()
    assert result.status is AffordabilityStatus.NOT_AFFORDABLE


def test_detected_salary_cannot_make_an_unsafe_purchase_safe():
    result = _analyze_with(_salary(CommitmentTier.DETECTED))
    assert result.status is AffordabilityStatus.NOT_AFFORDABLE
    assert result.chosen is None
    assert result.earliest_full_payment_date is None
    assert result.baseline_summary.lowest is not None
    # No credit of any size ever appears in the baseline.
    series = forecast(
        make_input(profile=PROFILE, purchase=PURCHASE, commitments=(_salary(CommitmentTier.DETECTED),))
    ).baseline_series
    assert all(day.close <= PROFILE.current_available_balance for day in series)
    considered = {c.commitment_id: c for c in result.considered_commitments}
    assert considered["salary"].status is CommitmentStatus.UNCONFIRMED_INCOME_EXCLUDED
    assert considered["salary"].occurrences_projected == 0
    codes = {e.code for e in result.assumptions}
    assert "RECURRING_INCOME_UNCONFIRMED_EXCLUDED" in codes
    assert "RECURRING_INCOME_CONFIRMED_INCLUDED" not in codes


def test_detected_salary_is_reported_as_missing_information_that_could_change_the_decision():
    result = _analyze_with(_salary(CommitmentTier.DETECTED))
    entry = next(e for e in result.missing_information if e.field_name == "commitments.confirmation")
    assert entry.subject_ids == ("salary",)
    assert entry.impact.value == "could_change_decision"


def test_confirmed_and_user_declared_salary_do_count():
    for tier in (CommitmentTier.CONFIRMED, CommitmentTier.USER_DECLARED):
        result = _analyze_with(_salary(tier))
        assert result.status is AffordabilityStatus.AFFORDABLE_LATER, tier
        assert result.earliest_full_payment_date is not None
        assert result.earliest_full_payment_date > AS_OF


def test_explicitly_supplied_scheduled_credit_counts():
    salary = make_event(
        "pay",
        AS_OF + timedelta(days=10),
        Decimal("20000"),
        direction=EventDirection.CREDIT,
        status=EventStatus.SCHEDULED,
        category="salary",
    )
    result = _analyze_with(events=(salary,))
    assert result.status is AffordabilityStatus.AFFORDABLE_LATER


def test_pending_credit_never_counts_even_if_a_detected_commitment_agrees_with_it():
    pending = make_event(
        "bonus",
        AS_OF + timedelta(days=10),
        Decimal("20000"),
        direction=EventDirection.CREDIT,
        status=EventStatus.PENDING,
        category="salary",
    )
    result = _analyze_with(_salary(CommitmentTier.DETECTED), events=(pending,))
    assert result.status is AffordabilityStatus.NOT_AFFORDABLE


def test_unconfirmed_increasing_fact_cannot_manufacture_income_but_confirmed_one_can():
    expected = make_event(
        "pay",
        AS_OF + timedelta(days=10),
        Decimal("1000"),
        direction=EventDirection.CREDIT,
        status=EventStatus.SCHEDULED,
        category="salary",
    )
    raise_fact = lambda confirmation: make_fact(  # noqa: E731
        "raise",
        direction=FactDirection.INCREASING,
        confirmation=confirmation,
        kind=FactKind.AMOUNT_CHANGE,
        target_event_id="pay",
        amount=Decimal("20000"),
    )
    proposed = _analyze_with(events=(expected,), facts=(raise_fact(FactConfirmation.PROPOSED),))
    confirmed = _analyze_with(events=(expected,), facts=(raise_fact(FactConfirmation.CONFIRMED),))
    assert proposed.status is AffordabilityStatus.NOT_AFFORDABLE
    assert "FACT_UNCONFIRMED_IGNORED" in {e.code for e in proposed.assumptions}
    assert confirmed.status is AffordabilityStatus.AFFORDABLE_LATER
