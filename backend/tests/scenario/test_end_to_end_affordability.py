"""End-to-end ``analyze()`` scenarios, synthetic and public-safe.

These mirror the shape of the legacy ``test_financial_engine.py``
projected-balance cases (same-day debit/credit ordering, future debits
and credits affecting safety) but exercise the full Phase 1 pipeline —
classification, FX, the certifiable window, candidate generation,
ranking, and status mapping — end to end. No dataset values are used.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finguard_core import analyze
from finguard_core.contracts import AffordabilityStatus, EventDirection, EventStatus
from tests.support.builders import (
    make_event,
    make_fx_rate,
    make_input,
    make_profile,
    make_purchase,
)

AS_OF = date(2026, 9, 1)


def test_full_payment_today_is_safe_when_balance_comfortably_covers_it():
    profile = make_profile(current_available_balance=Decimal("10000"), minimum_balance_to_keep=Decimal("3000"))
    purchase = make_purchase(amount=Decimal("1000"), currency="INR")
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase))

    assert result.status is AffordabilityStatus.AFFORDABLE_NOW
    assert result.chosen is not None
    assert result.chosen.safe is True
    assert result.chosen.first_payment_date == AS_OF


def test_full_payment_today_is_rejected_when_it_would_breach_the_reserve():
    profile = make_profile(current_available_balance=Decimal("10000"), minimum_balance_to_keep=Decimal("3000"))
    purchase = make_purchase(amount=Decimal("8000"), currency="INR")
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase))

    full_payment_today = next(
        c for c in result.candidates if c.candidate_type.value == "full_payment"
    )
    assert full_payment_today.safe is False
    assert any(code.code == "PURCHASE_CAUSES_BREACH" for code in full_payment_today.reasons)


def test_future_debit_can_make_an_otherwise_safe_payment_unsafe():
    profile = make_profile(current_available_balance=Decimal("10000"), minimum_balance_to_keep=Decimal("3000"))
    purchase = make_purchase(amount=Decimal("5000"), currency="INR")
    rent = make_event(
        "rent-001", AS_OF + timedelta(days=1), Decimal("4000"),
        direction=EventDirection.DEBIT, status=EventStatus.SCHEDULED, category="rent",
    )
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase, events=(rent,)))

    full_payment_today = next(c for c in result.candidates if c.candidate_type.value == "full_payment")
    assert full_payment_today.safe is False
    # 10,000 - 5,000 (purchase) - 4,000 (rent next day) = 1,000 < reserve 3,000.
    assert any(b.plan_low == Decimal("1000") for b in full_payment_today.breach_days)


def test_future_income_can_rescue_a_later_payment():
    profile = make_profile(current_available_balance=Decimal("5000"), minimum_balance_to_keep=Decimal("3000"))
    purchase = make_purchase(amount=Decimal("3000"), currency="INR")
    salary = make_event(
        "salary-001", AS_OF + timedelta(days=5), Decimal("10000"),
        direction=EventDirection.CREDIT, status=EventStatus.SCHEDULED, category="salary",
    )
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase, events=(salary,)))

    wait_candidate = next(c for c in result.candidates if c.candidate_type.value == "wait")
    assert wait_candidate.eligible is True
    # Paying before day+5 is unsafe (5000-3000=2000 < reserve); the
    # earliest safe full payment should land on or after the salary date.
    assert result.earliest_full_payment_date is not None
    assert result.earliest_full_payment_date >= AS_OF + timedelta(days=5)


def test_foreign_currency_debit_is_converted_before_the_safety_check():
    profile = make_profile(
        home_currency="INR", current_available_balance=Decimal("10000"), minimum_balance_to_keep=Decimal("3000"),
    )
    purchase = make_purchase(amount=Decimal("50"), currency="USD")
    rate = make_fx_rate("USD", "INR", AS_OF, Decimal("80"))
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase, fx_rates=(rate,)))

    full_payment_today = next(c for c in result.candidates if c.candidate_type.value == "full_payment")
    assert full_payment_today.total_cost == Decimal("4000.00")  # 50 USD * 80, rounded up to INR cents
    assert full_payment_today.safe is True


def test_not_affordable_when_no_candidate_is_ever_safe():
    profile = make_profile(current_available_balance=Decimal("1000"), minimum_balance_to_keep=Decimal("3000"))
    purchase = make_purchase(amount=Decimal("5000"), currency="INR", allows_partial_payment=False)
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase))

    assert result.status is AffordabilityStatus.NOT_AFFORDABLE
    assert result.chosen is None


def test_unconvertible_debit_blocks_certification_entirely():
    profile = make_profile(current_available_balance=Decimal("10000"), minimum_balance_to_keep=Decimal("3000"))
    purchase = make_purchase(amount=Decimal("1000"), currency="INR")
    unresolvable = make_event(
        "e", AS_OF, Decimal("500"), currency="ZAR", direction=EventDirection.DEBIT,
        status=EventStatus.SETTLED, category="other",
    )
    result = analyze(make_input(as_of=AS_OF, profile=profile, purchase=purchase, events=(unresolvable,)))

    assert result.status is AffordabilityStatus.NOT_AFFORDABLE
    assert result.data_quality.value == "insufficient"
