"""Cash-treatment classification (docs/engine/semantics.md Section 4)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finguard_core.classification import Treatment, classify_event
from finguard_core.contracts import EventDirection, EventStatus
from finguard_core.reason_codes import ReasonCode
from tests.support.builders import make_event

AS_OF = date(2026, 1, 1)
PAST = AS_OF - timedelta(days=5)
FUTURE = AS_OF + timedelta(days=5)


def test_settled_before_as_of_is_history_only():
    event = make_event("e", PAST, Decimal("100"), status=EventStatus.SETTLED)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.HISTORY_ONLY


def test_settled_debit_today_is_counted():
    event = make_event("e", AS_OF, Decimal("100"), status=EventStatus.SETTLED, direction=EventDirection.DEBIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.COUNTED
    assert result.same_day_after_debits is False


def test_settled_credit_today_is_counted_after_same_day_debits():
    event = make_event("e", AS_OF, Decimal("100"), status=EventStatus.SETTLED, direction=EventDirection.CREDIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.COUNTED
    assert result.same_day_after_debits is True
    assert ReasonCode.SAME_DAY_CREDIT_AFTER_DEBITS in result.reason_codes


def test_settled_in_future_is_counted_but_flagged():
    event = make_event("e", FUTURE, Decimal("100"), status=EventStatus.SETTLED)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.COUNTED
    assert ReasonCode.SETTLED_EVENT_IN_FUTURE in result.reason_codes


def test_pending_credit_is_never_counted():
    event = make_event("e", FUTURE, Decimal("100"), status=EventStatus.PENDING, direction=EventDirection.CREDIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.EXCLUDED
    assert ReasonCode.PENDING_CREDIT_EXCLUDED in result.reason_codes


def test_pending_debit_is_reserved_at_as_of():
    event = make_event("e", FUTURE, Decimal("100"), status=EventStatus.PENDING, direction=EventDirection.DEBIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.RESERVED_AT_AS_OF
    assert result.effective_date == AS_OF
    assert ReasonCode.PENDING_DEBIT_RESERVED in result.reason_codes


def test_overdue_pending_debit_is_reserved_and_flagged_overdue():
    event = make_event("e", PAST, Decimal("100"), status=EventStatus.PENDING, direction=EventDirection.DEBIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.RESERVED_AT_AS_OF
    assert ReasonCode.OVERDUE_PENDING_DEBIT_RESERVED in result.reason_codes


def test_scheduled_debit_on_or_after_as_of_is_counted_on_its_date():
    event = make_event("e", FUTURE, Decimal("100"), status=EventStatus.SCHEDULED, direction=EventDirection.DEBIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.COUNTED
    assert result.effective_date == FUTURE


def test_scheduled_debit_before_as_of_is_overdue_and_reserved():
    event = make_event("e", PAST, Decimal("100"), status=EventStatus.SCHEDULED, direction=EventDirection.DEBIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.RESERVED_AT_AS_OF
    assert ReasonCode.OVERDUE_SCHEDULED in result.reason_codes


def test_scheduled_credit_on_or_after_as_of_is_counted():
    event = make_event("e", FUTURE, Decimal("100"), status=EventStatus.SCHEDULED, direction=EventDirection.CREDIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.COUNTED
    assert ReasonCode.SCHEDULED_INCOME_COUNTED in result.reason_codes


def test_scheduled_credit_before_as_of_is_not_counted():
    event = make_event("e", PAST, Decimal("100"), status=EventStatus.SCHEDULED, direction=EventDirection.CREDIT)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.EXCLUDED


def test_cancelled_and_failed_events_are_excluded():
    for status in (EventStatus.CANCELLED, EventStatus.FAILED):
        event = make_event("e", AS_OF, Decimal("100"), status=status)
        result = classify_event(event, AS_OF)
        assert result.treatment is Treatment.EXCLUDED


def test_unrealized_and_non_cash_are_excluded():
    for status in (EventStatus.UNREALIZED, EventStatus.NON_CASH):
        event = make_event("e", AS_OF, Decimal("100"), status=status)
        result = classify_event(event, AS_OF)
        assert result.treatment is Treatment.EXCLUDED
        assert ReasonCode.UNREALIZED_EXCLUDED in result.reason_codes


def test_missing_amount_is_excluded_with_issue_code():
    event = make_event("e", AS_OF, None, status=EventStatus.SETTLED)
    result = classify_event(event, AS_OF)
    assert result.treatment is Treatment.EXCLUDED
    assert ReasonCode.UNRESOLVED_AMOUNT in result.reason_codes
