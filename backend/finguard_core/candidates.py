"""Candidate generation (docs/engine/semantics.md Section 9): full
payment, installments (from a supplied option), partial payment, wait,
and full-payment-with-spending-changes.

Each generator returns a :class:`CandidateResult` with its eligibility
filter outcome and, for eligible candidates, its safety evaluation.
Ranking among safe candidates and overall status mapping live in
``decision.py``.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from itertools import combinations

from finguard_core.contracts import (
    AnalysisInput,
    BreachDay,
    CandidateResult,
    CandidateType,
    PaymentOptionSchedule,
    ReasonEntry,
    SpendingChangeEntry,
)
from finguard_core.currency import RoundingDirection, round_money
from finguard_core.earliest_date import find_earliest_full_payment_date
from finguard_core.forecast import BaselineForecast
from finguard_core.fx import convert_amount
from finguard_core.reason_codes import ReasonCode, severity_of
from finguard_core.safety import build_plan_series, evaluate_candidate_safety
from finguard_core.spending_changes import (
    SpendingChangeCandidate,
    eligible_spending_change_candidates,
)


def _reason(code: ReasonCode, **params: str) -> ReasonEntry:
    return ReasonEntry(
        code=code.value,
        severity=severity_of(code).value,
        params=tuple(sorted(params.items())),
    )


def _rejected(candidate_type: CandidateType, option_id: str | None, code: ReasonCode) -> CandidateResult:
    return CandidateResult(
        candidate_type=candidate_type,
        option_id=option_id,
        safe=False,
        eligible=False,
        rejection_code=code.value,
        first_payment_date=None,
        final_payment_date=None,
        total_cost=Decimal(0),
        schedule=(),
        spending_changes=(),
        breach_days=(),
        reasons=(_reason(code),),
    )


def _evaluate_safety_and_build(
    analysis_input: AnalysisInput,
    baseline: BaselineForecast,
    candidate_type: CandidateType,
    option_id: str | None,
    extra_debits: dict[date, Decimal],
    schedule: tuple[PaymentOptionSchedule, ...],
    total_cost: Decimal,
    first_payment_date: date,
    final_payment_date: date,
    spending_changes: tuple[SpendingChangeEntry, ...] = (),
    extra_reasons: tuple[ReasonEntry, ...] = (),
) -> CandidateResult:
    effective_end = baseline.certifiable_window.effective_end
    plan_series = build_plan_series(baseline, extra_debits)
    safe, breach_days = evaluate_candidate_safety(
        baseline, plan_series, first_payment_date, effective_end, baseline.reserve
    )
    reasons: list[ReasonEntry] = list(extra_reasons)
    if safe:
        is_today = first_payment_date == analysis_input.as_of
        reasons.append(_reason(ReasonCode.PAY_NOW_SAFE if is_today else ReasonCode.PLAN_SAFE_WAIT))
    else:
        for breach in breach_days:
            code = {
                "causes": ReasonCode.PURCHASE_CAUSES_BREACH,
                "worsens": ReasonCode.PURCHASE_WORSENS_EXISTING_BREACH,
                "unrelated": ReasonCode.PURCHASE_UNRELATED_TO_BREACH,
            }[breach.attribution.value]
            reasons.append(_reason(code, date=breach.day.isoformat()))
        reasons.append(_reason(ReasonCode.REJECTED_UNSAFE))

    return CandidateResult(
        candidate_type=candidate_type,
        option_id=option_id,
        safe=safe,
        eligible=True,
        rejection_code=None,
        first_payment_date=first_payment_date,
        final_payment_date=final_payment_date,
        total_cost=total_cost,
        schedule=schedule,
        spending_changes=spending_changes,
        breach_days=breach_days,
        reasons=tuple(reasons),
    )


def _within_window(
    final_payment_date: date, deadline: date | None, effective_end: date
) -> ReasonCode | None:
    if deadline is not None and final_payment_date > deadline:
        return ReasonCode.REJECTED_DEADLINE
    if final_payment_date > effective_end:
        return ReasonCode.REJECTED_BEYOND_CERTIFIABLE_WINDOW
    return None


def generate_full_payment_candidate(
    analysis_input: AnalysisInput, baseline: BaselineForecast
) -> CandidateResult:
    if CandidateType.FULL_PAYMENT not in analysis_input.preferences.accepted_methods:
        return _rejected(CandidateType.FULL_PAYMENT, None, ReasonCode.METHOD_NOT_ACCEPTED)

    as_of = analysis_input.as_of
    home_currency = analysis_input.profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]
    purchase = analysis_input.purchase

    rejection = _within_window(as_of, purchase.desired_completion_date, baseline.certifiable_window.effective_end)
    if rejection is not None:
        return _rejected(CandidateType.FULL_PAYMENT, None, rejection)

    converted, _codes, blocks = convert_amount(
        purchase.amount, purchase.currency, home_currency, as_of,
        analysis_input.fx_rates, analysis_input.config, True, home_registry_currency, baseline.fx_log,
    )
    if blocks or converted is None:
        return _rejected(CandidateType.FULL_PAYMENT, None, ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)

    schedule = (PaymentOptionSchedule(due_date=as_of, amount=purchase.amount, currency=purchase.currency),)
    return _evaluate_safety_and_build(
        analysis_input, baseline, CandidateType.FULL_PAYMENT, None,
        {as_of: converted}, schedule, converted, as_of, as_of,
    )


def generate_installment_candidates(
    analysis_input: AnalysisInput, baseline: BaselineForecast
) -> tuple[CandidateResult, ...]:
    results: list[CandidateResult] = []
    preferences = analysis_input.preferences
    home_currency = analysis_input.profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]

    options = [o for o in analysis_input.payment_options if o.method is CandidateType.INSTALLMENTS]
    for option in options:
        if CandidateType.INSTALLMENTS not in preferences.accepted_methods:
            results.append(_rejected(CandidateType.INSTALLMENTS, option.option_id, ReasonCode.METHOD_NOT_ACCEPTED))
            continue
        if preferences.max_installment_term_days is None:
            results.append(
                _rejected(CandidateType.INSTALLMENTS, option.option_id, ReasonCode.INSTALLMENTS_NOT_CONSIDERED)
            )
            continue
        if not option.schedule:
            results.append(_rejected(CandidateType.INSTALLMENTS, option.option_id, ReasonCode.REJECTED_INVALID_OPTION))
            continue

        first_date = min(s.due_date for s in option.schedule)
        final_date = max(s.due_date for s in option.schedule)
        term = (final_date - first_date).days
        if term > preferences.max_installment_term_days:
            results.append(
                _rejected(CandidateType.INSTALLMENTS, option.option_id, ReasonCode.INSTALLMENT_TERM_EXCEEDS_LIMIT)
            )
            continue

        rejection = _within_window(
            final_date, analysis_input.purchase.desired_completion_date, baseline.certifiable_window.effective_end
        )
        if rejection is not None:
            results.append(_rejected(CandidateType.INSTALLMENTS, option.option_id, rejection))
            continue

        stated_sum = sum((s.amount for s in option.schedule), Decimal(0))
        extra_reasons: tuple[ReasonEntry, ...] = ()
        if abs(stated_sum - option.stated_total) > Decimal("0.01"):
            extra_reasons = (_reason(ReasonCode.OPTION_TOTAL_MISMATCH),)

        extra_debits: dict[date, Decimal] = {}
        total_cost = Decimal(0)
        blocked = False
        for entry in option.schedule:
            converted, _codes, blocks = convert_amount(
                entry.amount, entry.currency, home_currency, entry.due_date,
                analysis_input.fx_rates, analysis_input.config, True, home_registry_currency, baseline.fx_log,
            )
            if blocks or converted is None:
                blocked = True
                break
            extra_debits[entry.due_date] = extra_debits.get(entry.due_date, Decimal(0)) + converted
            total_cost += converted
        if blocked:
            results.append(
                _rejected(
                    CandidateType.INSTALLMENTS,
                    option.option_id,
                    ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION,
                )
            )
            continue

        results.append(
            _evaluate_safety_and_build(
                analysis_input, baseline, CandidateType.INSTALLMENTS, option.option_id,
                extra_debits, option.schedule, total_cost, first_date, final_date,
                extra_reasons=extra_reasons,
            )
        )
    return tuple(results)


def generate_wait_candidate(analysis_input: AnalysisInput, baseline: BaselineForecast) -> CandidateResult:
    if CandidateType.FULL_PAYMENT not in analysis_input.preferences.accepted_methods:
        return _rejected(CandidateType.WAIT, None, ReasonCode.METHOD_NOT_ACCEPTED)

    earliest = find_earliest_full_payment_date(analysis_input, baseline)
    if earliest is None:
        return _rejected(CandidateType.WAIT, None, ReasonCode.NO_SAFE_OPTION)

    rejection = _within_window(
        earliest, analysis_input.purchase.desired_completion_date, baseline.certifiable_window.effective_end
    )
    if rejection is not None:
        return _rejected(CandidateType.WAIT, None, rejection)

    home_currency = analysis_input.profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]
    converted, _codes, blocks = convert_amount(
        analysis_input.purchase.amount, analysis_input.purchase.currency, home_currency, earliest,
        analysis_input.fx_rates, analysis_input.config, True, home_registry_currency, baseline.fx_log,
    )
    if blocks or converted is None:
        return _rejected(CandidateType.WAIT, None, ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)

    schedule = (
        PaymentOptionSchedule(
            due_date=earliest, amount=analysis_input.purchase.amount, currency=analysis_input.purchase.currency
        ),
    )
    return _evaluate_safety_and_build(
        analysis_input, baseline, CandidateType.WAIT, None,
        {earliest: converted}, schedule, converted, earliest, earliest,
        extra_reasons=(_reason(ReasonCode.FULL_PAYMENT_SAFE_FROM, date=earliest.isoformat()),),
    )


def generate_partial_candidate(analysis_input: AnalysisInput, baseline: BaselineForecast) -> CandidateResult:
    if CandidateType.PARTIAL not in analysis_input.preferences.accepted_methods:
        return _rejected(CandidateType.PARTIAL, None, ReasonCode.METHOD_NOT_ACCEPTED)
    if not analysis_input.purchase.allows_partial_payment:
        return _rejected(CandidateType.PARTIAL, None, ReasonCode.PARTIAL_NOT_ALLOWED_BY_REQUEST)

    as_of = analysis_input.as_of
    home_currency = analysis_input.profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]

    converted_total, _codes, blocks = convert_amount(
        analysis_input.purchase.amount, analysis_input.purchase.currency, home_currency, as_of,
        analysis_input.fx_rates, analysis_input.config, True, home_registry_currency, baseline.fx_log,
    )
    if blocks or converted_total is None:
        return _rejected(CandidateType.PARTIAL, None, ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)

    window_lows = [d.low for d in baseline.series]
    headroom = (min(window_lows) - baseline.reserve) if window_lows else Decimal(0)
    safe_amount_now = max(
        Decimal(0),
        round_money(min(headroom, converted_total), home_registry_currency, RoundingDirection.DOWN),
    )
    remainder = converted_total - safe_amount_now

    if remainder <= 0:
        return generate_full_payment_candidate(analysis_input, baseline)

    remainder_date: date | None = None
    day = as_of + timedelta(days=1)
    while day <= baseline.certifiable_window.effective_end:
        plan_series = build_plan_series(baseline, {as_of: safe_amount_now, day: remainder})
        safe, _breach = evaluate_candidate_safety(
            baseline, plan_series, as_of, baseline.certifiable_window.effective_end, baseline.reserve
        )
        if safe:
            remainder_date = day
            break
        day = day + timedelta(days=1)

    if remainder_date is None:
        return _rejected(CandidateType.PARTIAL, None, ReasonCode.NO_SAFE_OPTION)

    schedule = (
        PaymentOptionSchedule(due_date=as_of, amount=safe_amount_now, currency=home_currency),
        PaymentOptionSchedule(due_date=remainder_date, amount=remainder, currency=home_currency),
    )
    extra_reasons = (_reason(ReasonCode.PARTIAL_LIMITED_BY_SAFE_AMOUNT),)
    return _evaluate_safety_and_build(
        analysis_input, baseline, CandidateType.PARTIAL, None,
        {as_of: safe_amount_now, remainder_date: remainder}, schedule, converted_total, as_of, remainder_date,
        extra_reasons=extra_reasons,
    )


def generate_spending_change_candidate(
    analysis_input: AnalysisInput, baseline: BaselineForecast, full_payment_result: CandidateResult
) -> CandidateResult | None:
    if full_payment_result.eligible and full_payment_result.safe:
        return None
    if CandidateType.FULL_PAYMENT not in analysis_input.preferences.accepted_methods:
        return None

    as_of = analysis_input.as_of
    home_currency = analysis_input.profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]
    converted, _codes, blocks = convert_amount(
        analysis_input.purchase.amount, analysis_input.purchase.currency, home_currency, as_of,
        analysis_input.fx_rates, analysis_input.config, True, home_registry_currency, baseline.fx_log,
    )
    if blocks or converted is None:
        return _rejected(
            CandidateType.FULL_PAYMENT_WITH_SPENDING_CHANGES,
            None,
            ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION,
        )

    ranked, reason_codes = eligible_spending_change_candidates(
        baseline.event_entries, analysis_input.preferences
    )
    if not ranked:
        reasons = tuple(_reason(c) for c in reason_codes) + (_reason(ReasonCode.SPENDING_CHANGE_INSUFFICIENT),)
        return CandidateResult(
            candidate_type=CandidateType.FULL_PAYMENT_WITH_SPENDING_CHANGES, option_id=None,
            safe=False, eligible=True, rejection_code=None, first_payment_date=as_of,
            final_payment_date=as_of, total_cost=converted, schedule=(), spending_changes=(),
            breach_days=(), reasons=reasons,
        )

    max_actions = analysis_input.config.max_spending_change_actions
    best: tuple[tuple[SpendingChangeCandidate, ...], CandidateResult] | None = None

    for size in range(1, min(max_actions, len(ranked)) + 1):
        found_at_size: list[tuple[Decimal, tuple[SpendingChangeCandidate, ...], CandidateResult]] = []
        for combo in combinations(ranked, size):
            if len({t.target_id for t in combo}) < len(combo):
                continue  # STOP and REDUCE of one target are alternatives, never both
            extra_debits: dict[date, Decimal] = {as_of: converted}
            for target in combo:
                for occ_date, saving in target.occurrences:
                    extra_debits[occ_date] = extra_debits.get(occ_date, Decimal(0)) - saving
            plan_series = build_plan_series(baseline, extra_debits)
            safe, breach_days = evaluate_candidate_safety(
                baseline, plan_series, as_of, baseline.certifiable_window.effective_end, baseline.reserve
            )
            if safe:
                total_changed = sum((t.window_total_saving for t in combo), Decimal(0))
                found_at_size.append((total_changed, combo, _candidate_result_for_combo(
                    analysis_input, combo, converted, as_of, breach_days, safe=True
                )))
        if found_at_size:
            found_at_size.sort(key=lambda item: (item[0], tuple(t.target_id for t in item[1])))
            best = (found_at_size[0][1], found_at_size[0][2])
            break

    if best is None:
        reasons = tuple(_reason(c) for c in reason_codes) + (_reason(ReasonCode.SPENDING_CHANGE_INSUFFICIENT),)
        return CandidateResult(
            candidate_type=CandidateType.FULL_PAYMENT_WITH_SPENDING_CHANGES, option_id=None,
            safe=False, eligible=True, rejection_code=None, first_payment_date=as_of,
            final_payment_date=as_of, total_cost=converted, schedule=(), spending_changes=(),
            breach_days=(), reasons=reasons,
        )

    return best[1]


def _candidate_result_for_combo(
    analysis_input: AnalysisInput,
    combo: tuple[SpendingChangeCandidate, ...],
    converted_amount: Decimal,
    as_of: date,
    breach_days: tuple[BreachDay, ...],
    safe: bool,
) -> CandidateResult:
    changes = tuple(
        SpendingChangeEntry(
            target_id=t.target_id, action=t.action, category=t.category,
            amount_changed=t.window_total_saving, window_total_saving=t.window_total_saving,
            occurrences=t.remaining_occurrences,
        )
        for t in combo
    )
    reasons = (
        _reason(ReasonCode.SPENDING_CHANGE_PROPOSED),
        _reason(ReasonCode.PLAN_SAFE_WITH_SPENDING_CHANGES),
    )
    return CandidateResult(
        candidate_type=CandidateType.FULL_PAYMENT_WITH_SPENDING_CHANGES, option_id=None,
        safe=safe, eligible=True, rejection_code=None, first_payment_date=as_of,
        final_payment_date=as_of, total_cost=converted_amount, schedule=(), spending_changes=changes,
        breach_days=breach_days, reasons=reasons,
    )
