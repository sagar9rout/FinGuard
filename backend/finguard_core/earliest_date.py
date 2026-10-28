"""Earliest full-payment date (docs/engine/semantics.md Section 11).

The first date in ``[as_of, effective_end]`` at which a single full
payment keeps the reserve safe (per the Section 9 predicate) from that
date onward, using the baseline forecast with no spending changes and no
partial payment. Reported identically regardless of which accepted
methods the user has chosen.
"""

from __future__ import annotations

from datetime import date, timedelta

from finguard_core.contracts import AnalysisInput
from finguard_core.forecast import BaselineForecast
from finguard_core.fx import convert_amount
from finguard_core.safety import build_plan_series, evaluate_candidate_safety


def find_earliest_full_payment_date(
    analysis_input: AnalysisInput, baseline: BaselineForecast
) -> date | None:
    home_currency = analysis_input.profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]
    purchase = analysis_input.purchase
    effective_end = baseline.certifiable_window.effective_end

    day = analysis_input.as_of
    while day <= effective_end:
        converted, _codes, blocks = convert_amount(
            purchase.amount,
            purchase.currency,
            home_currency,
            day,
            analysis_input.fx_rates,
            analysis_input.config,
            True,
            home_registry_currency,
            baseline.fx_log,
        )
        if not blocks and converted is not None:
            plan_series = build_plan_series(baseline, {day: converted})
            safe, _breach_days = evaluate_candidate_safety(
                baseline, plan_series, day, effective_end, baseline.reserve
            )
            if safe:
                return day
        day = day + timedelta(days=1)
    return None
