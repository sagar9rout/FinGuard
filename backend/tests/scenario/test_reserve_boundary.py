"""Minimum-reserve boundary (docs/engine/semantics.md section 9: safe iff plan_low(d) >= reserve).

Profile: balance INR 35,000, reserve INR 8,000, no other events, partial payment allowed, every method accepted.
Paying exactly 27,000 leaves exactly the reserve (safe); one rupee more breaches it (unsafe, certified, no option).
The partial candidate cannot rescue the 27,001 case: the safe amount now is 27,000 and, with no income, the remaining
1.00 can never be paid later without breaching the reserve.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from finguard_api import service

METHODS = ["full_payment", "installments", "partial", "wait", "full_payment_with_spending_changes"]


def _analyze(amount: str, as_of: str = "2026-10-24", partial: bool = True) -> dict:
    request = {
        "as_of": as_of,
        "profile": {
            "home_currency": "INR",
            "current_available_balance": "35000",
            "minimum_balance_to_keep": "8000",
            "balance_as_of": as_of,
        },
        "purchase": {"amount": amount, "currency": "INR", "allows_partial_payment": partial},
        "preferences": {"accepted_methods": METHODS},
    }
    response = service.handle_analyze(json.dumps(request).encode())
    assert response.status_code == 200
    return response.body


def _codes(body: dict) -> list[str]:
    return [r["code"] for r in body["result"]["reasons"]]


def _params(body: dict, code: str) -> dict[str, str]:
    entry = next(r for r in body["result"]["reasons"] if r["code"] == code)
    return {k: v for k, v in entry["params"]}


@pytest.mark.parametrize("as_of", ["2026-10-24", "2026-10-28"])
def test_exact_reserve_is_safe(as_of: str) -> None:
    body = _analyze("27000", as_of)
    assert body["outcome"] == {"certified": True, "status": "affordable_now"}
    chosen = body["result"]["chosen"]
    assert chosen["candidate_type"] == "full_payment" and chosen["safe"] is True
    assert chosen["total_cost"] == "27000"
    assert [(s["due_date"], s["amount"]) for s in chosen["schedule"]] == [(as_of, "27000")]
    assert chosen["breach_days"] == []
    assert "PAY_NOW_SAFE" in _codes(body)
    assert "RESERVE_BREACH_IF_PAID_NOW" not in _codes(body)


@pytest.mark.parametrize("as_of", ["2026-10-24", "2026-10-28"])
def test_one_rupee_below_reserve_is_not_affordable_and_certified(as_of: str) -> None:
    body = _analyze("27001", as_of)
    assert body["outcome"] == {"certified": True, "status": "not_affordable"}
    assert body["result"]["certified"] is True and body["result"]["status"] == "not_affordable"
    assert body["result"]["chosen"] is None
    assert _codes(body)[0] == "NO_SAFE_OPTION"
    breach = _params(body, "RESERVE_BREACH_IF_PAID_NOW")
    assert breach == {"cause": "purchase_causes", "date": as_of, "shortfall": "1.00"}
    # The baseline itself never breaches the reserve: the purchase is the cause.
    summary = body["result"]["baseline_summary"]
    assert summary["below_reserve"] is False and summary["days_below"] == 0 and summary["max_shortfall"] == "0"
    assert summary["lowest"] == {"day": as_of, "balance": "35000"}


def test_one_rupee_breach_is_not_rescued_by_partial_payment_or_by_disallowing_it() -> None:
    allowed = _analyze("27001", partial=True)
    refused = _analyze("27001", partial=False)
    assert allowed["outcome"] == refused["outcome"] == {"certified": True, "status": "not_affordable"}
    assert allowed["result"]["chosen"] is None and refused["result"]["chosen"] is None


def test_larger_breach_reports_the_full_shortfall() -> None:
    body = _analyze("28000")
    assert body["outcome"] == {"certified": True, "status": "not_affordable"}
    assert body["result"]["chosen"] is None
    assert _codes(body)[0] == "NO_SAFE_OPTION" and "RESERVE_BREACH_IF_PAID_NOW" in _codes(body)
    assert _params(body, "RESERVE_BREACH_IF_PAID_NOW")["shortfall"] == "1000.00"


# ---------------------------------------------------------------------------------------------------------------
# Paise-level boundary with a controlled forecast (balance 84,250.75, reserve 50,000.00, no events unless stated).
# Headroom above the reserve is 34,250.75, so the boundary purchase is 34,250.75, NOT 54,250.75: paying 54,250.74
# leaves 84,250.75 - 54,250.74 = 30,000.01, which is 19,999.99 below the reserve and is correctly rejected.
# ---------------------------------------------------------------------------------------------------------------


def _analyze2(amount: str, events: list[dict] | None = None, as_of: str = "2026-10-28") -> dict:
    request: dict = {
        "as_of": as_of,
        "profile": {
            "home_currency": "INR",
            "current_available_balance": "84250.75",
            "minimum_balance_to_keep": "50000",
        },
        "purchase": {"amount": amount, "currency": "INR", "allows_partial_payment": True},
        "preferences": {"accepted_methods": METHODS},
    }
    if events is not None:
        request["events"] = events
    response = service.handle_analyze(json.dumps(request).encode())
    assert response.status_code == 200
    return response.body


@pytest.mark.parametrize(
    ("amount", "left"),
    [("34250.74", "50000.01"), ("34250.75", "50000.00")],
)
def test_paise_above_or_exactly_at_reserve_is_affordable_now(amount: str, left: str) -> None:
    body = _analyze2(amount)
    assert body["outcome"] == {"certified": True, "status": "affordable_now"}
    chosen = body["result"]["chosen"]
    assert chosen["candidate_type"] == "full_payment" and chosen["safe"] is True and chosen["breach_days"] == []
    assert chosen["total_cost"] == amount
    assert Decimal("84250.75") - Decimal(amount) == Decimal(left)  # the arithmetic this test is named after
    assert body["result"]["baseline_summary"]["below_reserve"] is False


def test_one_paisa_below_reserve_is_not_affordable_with_exact_shortfall() -> None:
    body = _analyze2("34250.76")  # leaves 49,999.99
    assert body["outcome"] == {"certified": True, "status": "not_affordable"}
    assert body["result"]["chosen"] is None
    assert _params(body, "RESERVE_BREACH_IF_PAID_NOW")["shortfall"] == "0.01"
    full = next(c for c in body["result"]["candidates"] if c["candidate_type"] == "full_payment")
    assert full["eligible"] is True and full["safe"] is False
    assert full["breach_days"][0]["plan_low"] == "49999.99" and full["breach_days"][0]["reserve"] == "50000"


def test_reported_request_is_a_genuine_rejection_not_a_boundary_defect() -> None:
    body = _analyze2("54250.74")  # leaves 30,000.01, NOT 50,000.01
    assert body["outcome"] == {"certified": True, "status": "not_affordable"}
    assert body["result"]["chosen"] is None
    full = next(c for c in body["result"]["candidates"] if c["candidate_type"] == "full_payment")
    assert (full["eligible"], full["safe"], full["total_cost"]) == (True, False, "54250.74")
    assert full["breach_days"][0] == {
        "day": "2026-10-28",
        "attribution": "causes",
        "baseline_low": "84250.75",
        "plan_low": "30000.01",
        "reserve": "50000",
    }
    assert _params(body, "RESERVE_BREACH_IF_PAID_NOW")["shortfall"] == "19999.99"


def test_purchase_that_clears_the_reserve_today_is_still_rejected_for_a_genuine_future_breach() -> None:
    rent = {
        "event_id": "syn-rent",
        "event_date": "2026-11-01",
        "amount": "22000",
        "currency": "INR",
        "direction": "debit",
        "status": "scheduled",
        "category": "rent",
    }
    # Baseline alone stays above the reserve (84,250.75 - 22,000 = 62,250.75). Leaving 50,000.01 today is fine on the
    # day, but the 22,000 rent on 2026-11-01 then takes the balance to 28,000.01.
    body = _analyze2("34250.74", [rent])
    assert body["result"]["baseline_summary"]["below_reserve"] is False
    assert body["outcome"] == {"certified": True, "status": "not_affordable"}
    assert body["result"]["chosen"] is None
    full = next(c for c in body["result"]["candidates"] if c["candidate_type"] == "full_payment")
    assert full["safe"] is False
    first = full["breach_days"][0]
    assert (first["day"], first["attribution"], first["plan_low"], first["baseline_low"]) == (
        "2026-11-01",
        "causes",
        "28000.01",
        "62250.75",
    )
    # Day one is not a breach day: the future cash flow, not the purchase date, is the cause.
    assert "2026-10-28" not in [d["day"] for d in full["breach_days"]]


@pytest.mark.parametrize(
    "amount", ["27000", "27001", "34250.74", "34250.75", "34250.76", "54250.74", "54250.75", "100000"]
)
def test_candidates_and_outcome_are_consistent(amount: str) -> None:
    body = _analyze2(amount)
    result = body["result"]
    assert body["outcome"]["status"] == result["status"] and body["outcome"]["certified"] is result["certified"] is True
    safe = [c for c in result["candidates"] if c["eligible"] and c["safe"]]
    if result["status"] == "not_affordable":
        assert result["chosen"] is None and safe == []
        assert "NO_SAFE_OPTION" in [r["code"] for r in result["reasons"]]
    else:
        assert result["chosen"] in safe
        assert result["chosen"]["breach_days"] == []
        assert result["status"] == "affordable_now" and result["chosen"]["first_payment_date"] == "2026-10-28"
    for c in result["candidates"]:
        if c["safe"]:
            assert c["eligible"] and c["breach_days"] == []
        if not c["eligible"]:
            assert c["rejection_code"] is not None and c["safe"] is False


def test_baseline_forecast_without_a_purchase_stays_above_the_reserve() -> None:
    request = {
        "as_of": "2026-10-28",
        "profile": {
            "home_currency": "INR",
            "current_available_balance": "84250.75",
            "minimum_balance_to_keep": "50000",
        },
        "purchase": {"amount": "1", "currency": "INR", "allows_partial_payment": False},
        "preferences": {"accepted_methods": ["full_payment"]},
    }
    response = service.handle_forecast(json.dumps(request).encode())
    assert response.status_code == 200
    summary = response.body["result"]["baseline_summary"]
    assert summary["below_reserve"] is False and summary["lowest"] == {"day": "2026-10-28", "balance": "84250.75"}
