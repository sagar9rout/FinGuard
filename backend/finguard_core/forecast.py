"""Forecast construction: certifiable window, FX-converted daily ledger,
and the baseline series with its precomputed suffix-minimum
(docs/engine/semantics.md Sections 3, 5, 7, 8).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from finguard_core.classification import Treatment, classify_event
from finguard_core.commitments import effective_commitment_amount, project_commitments, resolve_commitments
from finguard_core.contracts import (
    AnalysisInput,
    BaselineSummary,
    CertifiableWindow,
    CommitmentStatus,
    ConsideredCommitment,
    EventDirection,
    LedgerDay,
    LowestPoint,
    VariableSpendInfo,
)
from finguard_core.evidence import apply_evidence_facts
from finguard_core.fx import FxUsageLog, convert_amount
from finguard_core.reason_codes import ReasonCode
from finguard_core.variable_spend import estimate_variable_spend


def compute_certifiable_window(
    as_of: date, deadline: date | None, horizon_days: int, max_window_days: int
) -> tuple[CertifiableWindow, bool]:
    horizon_end = as_of + timedelta(days=horizon_days)
    deadline_defaulted = deadline is None
    basis = horizon_end if deadline is None else max(horizon_end, deadline)
    effective_end = min(basis, as_of + timedelta(days=max_window_days))
    truncated = deadline is not None and deadline > effective_end
    return (
        CertifiableWindow(
            start=as_of,
            horizon_end=horizon_end,
            deadline=deadline,
            effective_end=effective_end,
            truncated=truncated,
            max_window_days=max_window_days,
        ),
        deadline_defaulted,
    )


@dataclass(frozen=True, slots=True)
class EventEntry:
    """One counted/reserved debit event in the forecast ledger, in home
    currency, kept so spending changes act only on cash that is really
    in the forecast (never on synthesized occurrences).
    """

    event_id: str
    on: date
    home_amount: Decimal
    minimum_home_amount: Decimal | None
    category: str
    is_stoppable: bool
    is_reducible: bool
    group_id: str | None


@dataclass(frozen=True, slots=True)
class BaselineForecast:
    certifiable_window: CertifiableWindow
    series: tuple[LedgerDay, ...]
    series_by_date: dict[date, LedgerDay]
    assumptions: tuple[ReasonCode, ...]
    issues: tuple[ReasonCode, ...]
    blocked: bool
    reserve: Decimal
    opening_balance: Decimal
    debit_totals: dict[date, Decimal]
    credit_totals: dict[date, Decimal]
    fx_log: FxUsageLog
    event_entries: tuple[EventEntry, ...]
    considered_commitments: tuple[ConsideredCommitment, ...]
    variable_spend: VariableSpendInfo
    summary: BaselineSummary


_convert = convert_amount


def summarize_baseline(series: Sequence[LedgerDay], reserve: Decimal) -> BaselineSummary:
    below = [d for d in series if d.low < reserve]
    if not series:
        return BaselineSummary(False, None, None, 0, None, Decimal(0))
    lowest_day = min(series, key=lambda d: (d.low, d.day))
    shortfall = reserve - lowest_day.low
    return BaselineSummary(
        below_reserve=bool(below),
        first_breach_date=below[0].day if below else None,
        last_breach_date=below[-1].day if below else None,
        days_below=len(below),
        lowest=LowestPoint(lowest_day.day, lowest_day.low),
        max_shortfall=shortfall if shortfall > 0 else Decimal(0),
    )


def build_baseline_forecast(analysis_input: AnalysisInput) -> BaselineForecast:
    config = analysis_input.config
    profile = analysis_input.profile
    as_of = analysis_input.as_of
    home_currency = profile.home_currency
    home_registry_currency = analysis_input.currency_registry[home_currency]
    fx_log = FxUsageLog(config)

    assumptions: list[ReasonCode] = []
    issues: list[ReasonCode] = []

    adjusted_events, fact_codes = apply_evidence_facts(
        analysis_input.events, analysis_input.evidence_facts, as_of
    )
    assumptions.extend(c for c in fact_codes if c != ReasonCode.FACT_CONFLICT)
    issues.extend(c for c in fact_codes if c == ReasonCode.FACT_CONFLICT)

    window, deadline_defaulted = compute_certifiable_window(
        as_of,
        analysis_input.purchase.desired_completion_date,
        config.horizon_days,
        config.max_window_days,
    )
    if deadline_defaulted:
        assumptions.append(ReasonCode.DEADLINE_DEFAULTED)
    if window.truncated:
        issues.append(ReasonCode.DEADLINE_BEYOND_CERTIFIABLE_WINDOW)
        assumptions.append(ReasonCode.CERTIFICATION_LIMITED_TO_WINDOW)

    resolution = resolve_commitments(analysis_input.commitments, as_of, config)
    status_code = {
        CommitmentStatus.SUPPRESSED_OVERLAP: ReasonCode.COMMITMENT_OVERLAP_SUPPRESSED,
        CommitmentStatus.SUPPRESSED_BY_USER_REJECTION: ReasonCode.COMMITMENT_REJECTED_BY_USER,
        CommitmentStatus.REJECTED: ReasonCode.COMMITMENT_REJECTED_BY_USER,
        CommitmentStatus.LAPSED: ReasonCode.COMMITMENT_LAPSED,
        CommitmentStatus.UNCONFIRMED_INCOME_EXCLUDED: ReasonCode.RECURRING_INCOME_UNCONFIRMED_EXCLUDED,
    }
    for record in resolution.records:
        mapped = status_code.get(record.status)
        if mapped is not None:
            assumptions.append(mapped)

    projected = project_commitments(resolution.kept, adjusted_events, as_of, window.effective_end, config)
    for occurrence in projected:
        if occurrence.suppressed_by_explicit_event:
            assumptions.append(ReasonCode.EXPLICIT_EVENT_SUPPRESSED_PROJECTION)
        else:
            assumptions.append(
                ReasonCode.RECURRING_EXPENSE_PROJECTED
                if occurrence.direction is EventDirection.DEBIT
                else ReasonCode.RECURRING_INCOME_CONFIRMED_INCLUDED
            )

    considered: list[ConsideredCommitment] = []
    for record in resolution.records:
        c = record.commitment
        mine = [o for o in projected if o.commitment_id == c.commitment_id]
        considered.append(
            ConsideredCommitment(
                commitment_id=c.commitment_id,
                direction=c.direction,
                category=c.category,
                tier=c.tier,
                status=record.status,
                suppressed_by=record.suppressed_by,
                amount_per_occurrence=effective_commitment_amount(c),
                currency=c.currency,
                occurrences_projected=sum(1 for o in mine if not o.suppressed_by_explicit_event),
                occurrences_suppressed_by_explicit_event=sum(1 for o in mine if o.suppressed_by_explicit_event),
            )
        )

    debit_totals: dict[date, Decimal] = {}
    credit_totals: dict[date, Decimal] = {}
    entries: list[EventEntry] = []
    blocked = False

    def _add(day: date, direction: EventDirection, amount: Decimal) -> None:
        bucket = debit_totals if direction is EventDirection.DEBIT else credit_totals
        bucket[day] = bucket.get(day, Decimal(0)) + amount

    for event in adjusted_events:
        classified = classify_event(event, as_of)
        for code in classified.reason_codes:
            (issues if code in _ISSUE_CODES else assumptions).append(code)
        if classified.treatment not in (Treatment.COUNTED, Treatment.RESERVED_AT_AS_OF):
            continue
        if classified.effective_date is None or classified.amount is None:
            continue
        is_debit = classified.direction is EventDirection.DEBIT
        converted, fx_codes, blocks = _convert(
            classified.amount,
            classified.currency,
            home_currency,
            classified.effective_date,
            analysis_input.fx_rates,
            config,
            is_debit,
            home_registry_currency,
            fx_log,
        )
        assumptions.extend(c for c in fx_codes if c != ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)
        if blocks:
            issues.append(ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)
            blocked = True
            continue
        if converted is None or classified.effective_date > window.effective_end:
            continue
        _add(classified.effective_date, classified.direction, converted)
        if is_debit:
            minimum_home: Decimal | None = None
            minimum_native = event.minimum_allowed_amount
            if minimum_native is None:
                minimum_native = dict(analysis_input.preferences.category_min_allowed).get(event.category)
            if event.is_reducible and minimum_native is not None:
                minimum_home, _mc, min_blocks = _convert(
                    minimum_native,
                    classified.currency,
                    home_currency,
                    classified.effective_date,
                    analysis_input.fx_rates,
                    config,
                    True,
                    home_registry_currency,
                    fx_log,
                )
                if min_blocks:
                    minimum_home = None
            entries.append(
                EventEntry(
                    event_id=event.event_id,
                    on=classified.effective_date,
                    home_amount=converted,
                    minimum_home_amount=minimum_home,
                    category=event.category,
                    is_stoppable=event.is_stoppable,
                    is_reducible=event.is_reducible,
                    group_id=event.recurrence_group_id,
                )
            )

    for occurrence in projected:
        if occurrence.suppressed_by_explicit_event:
            continue
        is_debit = occurrence.direction is EventDirection.DEBIT
        converted, fx_codes, blocks = _convert(
            occurrence.amount,
            occurrence.currency,
            home_currency,
            occurrence.occurrence_date,
            analysis_input.fx_rates,
            config,
            is_debit,
            home_registry_currency,
            fx_log,
        )
        assumptions.extend(c for c in fx_codes if c != ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)
        if blocks:
            issues.append(ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)
            blocked = True
            continue
        if converted is not None:
            _add(occurrence.occurrence_date, occurrence.direction, converted)

    variable_estimate = estimate_variable_spend(
        adjusted_events,
        analysis_input.preferences.variable_spend_categories,
        as_of,
        home_currency,
        home_registry_currency,
        config,
        analysis_input.fx_rates,
        fx_log,
    )
    for code in variable_estimate.reason_codes:
        if code is ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION:
            issues.append(code)
            blocked = True
        elif code is ReasonCode.INSUFFICIENT_HISTORY:
            issues.append(code)
        else:
            assumptions.append(code)
    if variable_estimate.daily_amount is not None:
        explicit_overlap = any(
            e.category in variable_estimate.categories
            and e.direction is EventDirection.DEBIT
            and e.event_date >= as_of
            for e in adjusted_events
        )
        if explicit_overlap:
            assumptions.append(ReasonCode.VARIABLE_SPEND_PLUS_EXPLICIT_EVENTS)
        day = as_of
        while day <= window.effective_end:
            _add(day, EventDirection.DEBIT, variable_estimate.daily_amount)
            day = day + timedelta(days=1)

    if profile.balance_as_of is not None:
        if (as_of - profile.balance_as_of).days > config.balance_stale_after_days:
            issues.append(ReasonCode.BALANCE_STALE)

    series: list[LedgerDay] = []
    series_by_date: dict[date, LedgerDay] = {}
    if not blocked:
        running_close = profile.current_available_balance
        day = as_of
        while day <= window.effective_end:
            low = running_close - debit_totals.get(day, Decimal(0))
            close = low + credit_totals.get(day, Decimal(0))
            ledger_day = LedgerDay(day=day, low=low, close=close)
            series.append(ledger_day)
            series_by_date[day] = ledger_day
            running_close = close
            day = day + timedelta(days=1)

    summary = summarize_baseline(series, profile.minimum_balance_to_keep)

    return BaselineForecast(
        certifiable_window=window,
        series=tuple(series),
        series_by_date=series_by_date,
        assumptions=tuple(assumptions),
        issues=tuple(issues),
        blocked=blocked,
        reserve=profile.minimum_balance_to_keep,
        opening_balance=profile.current_available_balance,
        debit_totals=debit_totals,
        credit_totals=credit_totals,
        fx_log=fx_log,
        event_entries=tuple(sorted(entries, key=lambda e: (e.on, e.event_id))),
        considered_commitments=tuple(considered),
        variable_spend=variable_estimate.info,
        summary=summary,
    )


_ISSUE_CODES = {
    ReasonCode.SETTLED_EVENT_IN_FUTURE,
    ReasonCode.OVERDUE_SCHEDULED,
    ReasonCode.UNRESOLVED_AMOUNT,
}
