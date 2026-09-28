from datetime import date
from decimal import Decimal

from financial_engine.event_mapper import map_event


def test_map_event_normalizes_core_fields():
    row = {
        "event_id": "evt-1",
        "user_id": "user-1",
        "event_date": "2026-09-20",
        "event_type": "PAYMENT",
        "description": "Rent",
        "amount": "12500.50",
        "currency": "INR",
        "direction": "DEBIT",
        "status": "SETTLED",
        "category": "housing",
        "flexibility": "protected",
        "recurring_group": "rent",
    }

    event = map_event(row)

    assert event.event_id == "evt-1"
    assert event.user_id == "user-1"
    assert event.event_date == date(2026, 9, 20)
    assert event.amount == Decimal("12500.50")
    assert event.direction == "debit"
    assert event.status == "settled"
    assert event.recurring_group == "rent"
    assert event.is_outflow
    assert event.is_valid_for_cashflow


def test_blank_amount_becomes_unresolved():
    row = {
        "event_id": "evt-2",
        "user_id": "user-1",
        "event_date": "2026-09-20",
        "amount": "",
        "currency": "INR",
        "direction": "debit",
        "status": "settled",
    }

    event = map_event(row)

    assert event.amount is None
    assert not event.is_valid_for_cashflow
