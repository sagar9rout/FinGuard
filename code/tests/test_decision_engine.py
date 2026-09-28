"""
Regression tests for main.choose_decision().

These tests use small, hand-built, in-memory dictionaries/lists that match
the exact field names and shapes choose_decision() (and the helpers it
calls: candidate_full_payment, candidate_partial, find_wait_date,
safe_today_amount, compute_earliest_full_payment_date, projected_balance)
read directly from CSV rows in production. No dataset file is read, no
internal function is mocked/monkeypatched, and no production code is
modified.

Field shapes were taken directly from code/main.py:
  - profile: a single dict (main.load_profiles just indexes csv rows by
    user_id) with home_currency, current_available_balance,
    minimum_balance_to_keep, payment_methods_user_will_consider
    (pipe/comma/semicolon separated, case-insensitive -- see
    normalize_list), and max_installment_months (blank means the user will
    not consider installments at all -- see candidate_full_payment).
  - events: a list of raw event dicts for the request's user_id (main
    groups financial_events.csv rows by user_id via load_events). Required
    keys actually read by usable_event()/event_date()/projected_balance():
    event_id, direction ("debit"/"credit"), amount, currency, status,
    event_date (settlement_date is also checked first if present).
  - options: a list of raw request_payment_options.csv rows for this one
    request_id (main groups by request_id via load_options). Required
    keys: payment_option_id, payment_method ("full_payment"/
    "installments"), first_payment_date, number_of_payments,
    payment_frequency_days, payment_amount, total_payable_amount,
    currency.
  - rates: the dict main.build_exchange_rates() would produce, keyed
    (base_currency, quote_currency) -> Decimal. All scenarios below keep
    every amount in the profile's home currency, so an empty dict is
    sufficient (main.conversion() short-circuits when currency == home).

Each test is self-contained: no shared fixtures/state between tests, and
each uses its own user_id/request_id.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import choose_decision  # noqa: E402


def make_profile(**overrides):
    profile = {
        "user_id": "user_x",
        "home_currency": "USD",
        "current_available_balance": "10000",
        "minimum_balance_to_keep": "500",
        "financial_priorities": "",
        "expense_categories_to_protect": "",
        "expense_categories_user_is_willing_to_reduce": "",
        "expense_categories_user_is_willing_to_stop": "",
        "payment_methods_user_will_consider": "full_payment",
        "max_installment_months": "",
    }
    profile.update(overrides)
    return profile


def make_request(**overrides):
    request = {
        "request_id": "request_x",
        "user_id": "user_x",
        "request_date": "2026-01-05",
        "request_type": "purchase",
        "requested_amount": "1000",
        "desired_completion_date": "2026-02-01",
        "allows_partial_payment": "false",
        "request_text": "Test request.",
    }
    request.update(overrides)
    return request


def make_event(**overrides):
    event = {
        "event_id": "event_x",
        "user_id": "user_x",
        "event_type": "recurring",
        "description": "Test event",
        "category": "salary",
        "direction": "credit",
        "amount": "0",
        "currency": "USD",
        "event_date": "2026-01-05",
        "settlement_date": "2026-01-05",
        "status": "scheduled",
        "linked_event_id": "",
        "flexibility": "fixed",
        "minimum_allowed_amount": "",
    }
    event.update(overrides)
    return event


def make_option(**overrides):
    option = {
        "request_id": "request_x",
        "payment_option_id": "option_x",
        "payment_method": "full_payment",
        "first_payment_date": "2026-01-05",
        "number_of_payments": "1",
        "payment_frequency_days": "0",
        "payment_amount": "1000",
        "total_payable_amount": "1000",
        "currency": "USD",
    }
    option.update(overrides)
    return option


def test_affordable_now_full_payment():
    """
    Enough available balance to safely pay the full requested amount
    immediately: a matching full_payment option is supplied, the user
    accepts full_payment, and current_available_balance comfortably
    clears requested_amount + minimum_balance_to_keep with no other
    events in play.
    """
    profile = make_profile(
        user_id="user_now",
        current_available_balance="10000",
        minimum_balance_to_keep="500",
        payment_methods_user_will_consider="full_payment",
    )
    request = make_request(
        request_id="request_now",
        user_id="user_now",
        request_date="2026-01-05",
        desired_completion_date="2026-01-05",
        requested_amount="1000",
        allows_partial_payment="false",
    )
    options = [
        make_option(
            request_id="request_now",
            payment_option_id="option_now_1",
            payment_method="full_payment",
            first_payment_date="2026-01-05",
            number_of_payments="1",
            payment_frequency_days="0",
            payment_amount="1000",
            total_payable_amount="1000",
            currency="USD",
        )
    ]

    row = choose_decision(request, profile, events=[], options=options, rates={})

    assert row["affordability_status"] == "affordable_now"
    assert row["recommended_payment_method"] == "full_payment"


def test_affordable_with_plan_installments():
    """
    Immediate full payment is not what the user wants to consider (only
    "installments" is in payment_methods_user_will_consider, so
    candidate_full_payment never offers full_payment), but a supplied
    installment option -- with both its installments scheduled after a
    confirmed future salary credit -- safely completes the purchase by
    desired_completion_date.
    """
    profile = make_profile(
        user_id="user_plan",
        current_available_balance="2000",
        minimum_balance_to_keep="500",
        payment_methods_user_will_consider="installments",
        max_installment_months="6",
    )
    request = make_request(
        request_id="request_plan",
        user_id="user_plan",
        request_date="2026-01-05",
        desired_completion_date="2026-03-05",
        requested_amount="3000",
        allows_partial_payment="false",
    )
    events = [
        make_event(
            event_id="event_plan_salary",
            user_id="user_plan",
            category="salary",
            direction="credit",
            amount="5000",
            currency="USD",
            status="scheduled",
            event_date="2026-02-01",
            settlement_date="2026-02-01",
        )
    ]
    options = [
        make_option(
            request_id="request_plan",
            payment_option_id="option_plan_1",
            payment_method="installments",
            first_payment_date="2026-02-05",
            number_of_payments="2",
            payment_frequency_days="20",
            payment_amount="1500",
            total_payable_amount="3000",
            currency="USD",
        )
    ]

    row = choose_decision(
        request, profile, events=events, options=options, rates={}
    )

    assert row["affordability_status"] == "affordable_with_plan"
    assert row["payment_plan"] != ""
    assert row["earliest_date_for_full_payment"] != ""


def test_affordable_later_wait():
    """
    The purchase cannot safely be paid now (current balance is far below
    requested_amount + minimum_balance_to_keep, and no payment options are
    supplied so there is nothing to install/partial-pay against), but a
    confirmed future salary credit makes the full lump-sum payment safe
    before desired_completion_date, and the user accepts full_payment (a
    prerequisite for "wait" per candidate eligibility rules).
    """
    profile = make_profile(
        user_id="user_later",
        current_available_balance="1000",
        minimum_balance_to_keep="200",
        payment_methods_user_will_consider="full_payment",
    )
    request = make_request(
        request_id="request_later",
        user_id="user_later",
        request_date="2026-01-05",
        desired_completion_date="2026-02-15",
        requested_amount="2500",
        allows_partial_payment="false",
    )
    events = [
        make_event(
            event_id="event_later_salary",
            user_id="user_later",
            category="salary",
            direction="credit",
            amount="4000",
            currency="USD",
            status="scheduled",
            event_date="2026-02-01",
            settlement_date="2026-02-01",
        )
    ]

    row = choose_decision(request, profile, events=events, options=[], rates={})

    assert row["affordability_status"] == "affordable_later"
    assert row["recommended_payment_method"] == "wait"
    assert row["earliest_date_for_full_payment"] != ""


def test_not_affordable():
    """
    No safe payment strategy exists within the requested completion
    window: a very small balance, a large requested amount, no payment
    options supplied, partial payment not allowed, and no future cash-flow
    event before desired_completion_date to make a full/"wait" payment
    safe either.
    """
    profile = make_profile(
        user_id="user_no",
        current_available_balance="300",
        minimum_balance_to_keep="250",
        payment_methods_user_will_consider="full_payment",
    )
    request = make_request(
        request_id="request_no",
        user_id="user_no",
        request_date="2026-01-05",
        desired_completion_date="2026-01-20",
        requested_amount="5000",
        allows_partial_payment="false",
    )

    row = choose_decision(request, profile, events=[], options=[], rates={})

    assert row["affordability_status"] == "not_affordable"
    assert row["recommended_payment_method"] == "not_recommended"
