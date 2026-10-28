"""Property-style agreement check between the production G.9
implementation and the independent oracle, over a grid of synthetic
cases. Confirms the two independently-written implementations of the
same specification agree — not just that the production code is
internally consistent with itself.
"""

from __future__ import annotations

from datetime import date

from finguard_core.safety import classify_breach_day
from tests.oracle.reference_safety import reference_breach_attribution

DAY = date(2026, 1, 1)


def test_breach_attribution_agrees_with_the_independent_oracle_over_a_grid():
    reserve = 3000.0
    plan_low = 1000.0  # always unsafe for this grid
    for baseline_low in [x * 0.5 for x in range(-6000, 12000, 500)]:
        production = classify_breach_day(DAY, baseline_low=baseline_low, plan_low=plan_low, reserve=reserve)
        oracle = reference_breach_attribution(baseline_low, plan_low, reserve)
        assert production.value == oracle, (baseline_low, plan_low, reserve)


def test_breach_attribution_agrees_with_the_independent_oracle_across_varying_plan_low():
    reserve = 3000.0
    baseline_low = 2000.0  # baseline already unsafe
    for plan_low in [x * 0.25 for x in range(-4000, 2000 * 4, 250) if x * 0.25 < reserve]:
        production = classify_breach_day(DAY, baseline_low=baseline_low, plan_low=plan_low, reserve=reserve)
        oracle = reference_breach_attribution(baseline_low, plan_low, reserve)
        assert production.value == oracle, (baseline_low, plan_low, reserve)


def test_safety_predicate_agrees_with_reference_over_synthetic_ledgers():
    from decimal import Decimal

    from finguard_core.forecast import build_baseline_forecast
    from finguard_core.safety import build_plan_series, evaluate_candidate_safety
    from tests.oracle.reference_safety import reference_is_safe
    from tests.support.builders import make_input, make_profile, make_purchase

    for balance, reserve, purchase_amount in [
        (10000, 3000, 1000),
        (10000, 3000, 7500),
        (5000, 1000, 4500),
        (3000, 3000, 1),
        (3000, 3000, 0),
    ]:
        balance, reserve, purchase_amount = Decimal(balance), Decimal(reserve), Decimal(purchase_amount)
        profile = make_profile(current_available_balance=balance, minimum_balance_to_keep=reserve)
        purchase = make_purchase(amount=purchase_amount, currency="INR")
        analysis_input = make_input(profile=profile, purchase=purchase)
        baseline = build_baseline_forecast(analysis_input)

        as_of = analysis_input.as_of
        plan_series = build_plan_series(baseline, {as_of: purchase_amount})
        safe, _breach = evaluate_candidate_safety(
            baseline, plan_series, as_of, baseline.certifiable_window.effective_end, baseline.reserve
        )

        plan_low_by_day = {day: float(ledger.low) for day, ledger in plan_series.items()}
        oracle_safe = reference_is_safe(
            plan_low_by_day, float(reserve), as_of, baseline.certifiable_window.effective_end
        )
        assert safe == oracle_safe, (balance, reserve, purchase_amount)
