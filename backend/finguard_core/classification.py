"""Cash-treatment classification (docs/engine/semantics.md Section 4).

One function classifies every event by status, direction, and date
relative to ``as_of``. This module has no knowledge of FX, commitments,
or candidates — it only decides *if*, *when*, and *how* a single event's
amount enters the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from finguard_core.contracts import EventDirection, EventStatus, FinancialEventInput
from finguard_core.reason_codes import ReasonCode


class Treatment(StrEnum):
    COUNTED = "counted"
    RESERVED_AT_AS_OF = "reserved_at_as_of"
    EXCLUDED = "excluded"
    HISTORY_ONLY = "history_only"


@dataclass(frozen=True, slots=True)
class ClassifiedEvent:
    event_id: str
    treatment: Treatment
    effective_date: date | None
    amount: Decimal | None
    currency: str
    direction: EventDirection
    same_day_after_debits: bool
    category: str
    reason_codes: tuple[ReasonCode, ...]


def classify_event(event: FinancialEventInput, as_of: date) -> ClassifiedEvent:
    def make(
        treatment: Treatment,
        effective_date: date | None,
        same_day_after_debits: bool,
        reason_codes: tuple[ReasonCode, ...],
    ) -> ClassifiedEvent:
        return ClassifiedEvent(
            event_id=event.event_id,
            treatment=treatment,
            effective_date=effective_date,
            amount=event.amount,
            currency=event.currency,
            direction=event.direction,
            same_day_after_debits=same_day_after_debits,
            category=event.category,
            reason_codes=reason_codes,
        )

    if event.amount is None:
        return make(Treatment.EXCLUDED, None, False, (ReasonCode.UNRESOLVED_AMOUNT,))

    if event.status in (EventStatus.CANCELLED, EventStatus.FAILED):
        return make(Treatment.EXCLUDED, None, False, ())

    if event.status in (EventStatus.UNREALIZED, EventStatus.NON_CASH):
        return make(Treatment.EXCLUDED, None, False, (ReasonCode.UNREALIZED_EXCLUDED,))

    if event.status is EventStatus.SETTLED:
        if event.event_date < as_of:
            return make(Treatment.HISTORY_ONLY, None, False, ())
        if event.event_date == as_of:
            same_day_credit = event.direction is EventDirection.CREDIT
            settled_today_codes: tuple[ReasonCode, ...] = (
                (ReasonCode.SAME_DAY_CREDIT_AFTER_DEBITS,) if same_day_credit else ()
            )
            return make(Treatment.COUNTED, event.event_date, same_day_credit, settled_today_codes)
        return make(Treatment.COUNTED, event.event_date, False, (ReasonCode.SETTLED_EVENT_IN_FUTURE,))

    if event.status is EventStatus.PENDING:
        if event.direction is EventDirection.CREDIT:
            return make(Treatment.EXCLUDED, None, False, (ReasonCode.PENDING_CREDIT_EXCLUDED,))
        overdue = event.event_date < as_of
        code = ReasonCode.OVERDUE_PENDING_DEBIT_RESERVED if overdue else ReasonCode.PENDING_DEBIT_RESERVED
        return make(Treatment.RESERVED_AT_AS_OF, as_of, False, (code,))

    if event.status is EventStatus.SCHEDULED:
        if event.direction is EventDirection.DEBIT:
            if event.event_date >= as_of:
                return make(Treatment.COUNTED, event.event_date, False, ())
            return make(Treatment.RESERVED_AT_AS_OF, as_of, False, (ReasonCode.OVERDUE_SCHEDULED,))
        # scheduled credit
        if event.event_date >= as_of:
            same_day_credit = event.event_date == as_of
            codes: tuple[ReasonCode, ...] = (
                (ReasonCode.SCHEDULED_INCOME_COUNTED, ReasonCode.SAME_DAY_CREDIT_AFTER_DEBITS)
                if same_day_credit
                else (ReasonCode.SCHEDULED_INCOME_COUNTED,)
            )
            return make(Treatment.COUNTED, event.event_date, same_day_credit, codes)
        return make(Treatment.EXCLUDED, None, False, (ReasonCode.OVERDUE_SCHEDULED,))

    raise AssertionError(f"Unhandled event status: {event.status!r}")
