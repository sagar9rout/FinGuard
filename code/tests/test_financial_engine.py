from datetime import date
from decimal import Decimal

from main import projected_balance


def test_payment_at_minimum_boundary_is_safe():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "10000",
        "minimum_balance_to_keep": "3000",
    }

    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=[],
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 1), Decimal("7000"), "INR"),
        ],
        rates={},
    )

    assert safe is True
    assert balance == Decimal("3000")
    assert checked_date == date(2026, 9, 1)


def test_payment_below_minimum_is_rejected():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "10000",
        "minimum_balance_to_keep": "3000",
    }

    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=[],
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 1), Decimal("8000"), "INR"),
        ],
        rates={},
    )

    assert safe is False
    assert balance == Decimal("2000")
    assert checked_date == date(2026, 9, 1)


def test_foreign_currency_payment_is_converted_before_safety_check():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "10000",
        "minimum_balance_to_keep": "3000",
    }

    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=[],
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 1), Decimal("50"), "USD"),
        ],
        rates={
            ("USD", "INR"): Decimal("80"),
        },
    )

    assert safe is True
    assert balance == Decimal("6000")
    assert checked_date == date(2026, 9, 1)


def test_foreign_currency_payment_can_make_balance_unsafe():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "10000",
        "minimum_balance_to_keep": "3000",
    }

    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=[],
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 1), Decimal("100"), "USD"),
        ],
        rates={
            ("USD", "INR"): Decimal("80"),
        },
    )

    assert safe is False
    assert balance == Decimal("2000")
    assert checked_date == date(2026, 9, 1)


def test_future_debit_can_make_an_otherwise_safe_payment_unsafe():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "10000",
        "minimum_balance_to_keep": "3000",
    }

    events = [
        {
            "event_id": "rent-001",
            "event_date": "2026-09-02",
            "amount": "4000",
            "currency": "INR",
            "direction": "debit",
            "status": "scheduled",
            "category": "rent",
        }
    ]

    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=events,
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 1), Decimal("5000"), "INR"),
        ],
        rates={},
    )

    assert safe is False
    assert balance == Decimal("1000")
    assert checked_date == date(2026, 9, 2)


def test_future_income_can_make_payment_safe():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "5000",
        "minimum_balance_to_keep": "3000",
    }

    events = [
        {
            "event_id": "salary-001",
            "event_date": "2026-09-05",
            "amount": "10000",
            "currency": "INR",
            "direction": "credit",
            "status": "scheduled",
            "category": "salary",
        }
    ]

    # Today:
    # ₹5,000 - ₹3,000 payment = ₹2,000 -> unsafe.
    #
    # But the scheduled salary arrives later:
    # ₹2,000 + ₹10,000 = ₹12,000
    #
    # Therefore a payment scheduled after salary should be safe.
    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=events,
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 6), Decimal("3000"), "INR"),
        ],
        rates={},
    )

    assert safe is True
    assert balance == Decimal("12000")
    assert checked_date == date(2026, 9, 6)


def test_future_income_is_not_available_before_settlement():
    profile = {
        "home_currency": "INR",
        "current_available_balance": "5000",
        "minimum_balance_to_keep": "3000",
    }

    events = [
        {
            "event_id": "salary-002",
            "event_date": "2026-09-05",
            "amount": "10000",
            "currency": "INR",
            "direction": "credit",
            "status": "scheduled",
            "category": "salary",
        }
    ]

    # Payment happens before salary arrives.
    # ₹5,000 - ₹3,000 = ₹2,000 < ₹3,000.
    safe, balance, checked_date = projected_balance(
        profile=profile,
        events=events,
        request_date=date(2026, 9, 1),
        payment_schedule=[
            (date(2026, 9, 4), Decimal("3000"), "INR"),
        ],
        rates={},
    )

    assert safe is False
    assert balance == Decimal("2000")
    assert checked_date == date(2026, 9, 4)
