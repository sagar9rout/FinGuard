"""The engine's public entry points: ``analyze``, ``forecast``, and
``validate_input`` (ADR 0001). This is the only module callers should
import from directly, aside from the contract types.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from finguard_core.candidates import (
    generate_full_payment_candidate,
    generate_installment_candidates,
    generate_partial_candidate,
    generate_spending_change_candidate,
    generate_wait_candidate,
)
from finguard_core.canonical import input_hash as compute_input_hash
from finguard_core.canonical import normalize_input
from finguard_core.contracts import (
    AffordabilityStatus,
    AnalysisInput,
    AnalysisResult,
    BaselineSummary,
    CandidateResult,
    CandidateType,
    ForecastResult,
    ReasonEntry,
)
from finguard_core.decision import map_status, rank_candidates
from finguard_core.earliest_date import find_earliest_full_payment_date
from finguard_core.forecast import BaselineForecast, build_baseline_forecast
from finguard_core.quality import compute_data_quality, compute_missing_information
from finguard_core.reason_codes import ReasonCode, severity_of
from finguard_core.validation import InputValidationError, collect_violations, validate_or_raise


def _to_reason_entries(codes: Sequence[ReasonCode]) -> tuple[ReasonEntry, ...]:
    """Deduplicated and sorted by code value, so the output never depends
    on the order in which codes were emitted.
    """

    unique = sorted({code.value: code for code in codes}.values(), key=lambda c: c.value)
    return tuple(ReasonEntry(code=c.value, severity=severity_of(c).value) for c in unique)


def _entry(code: ReasonCode, **params: str) -> ReasonEntry:
    return ReasonEntry(code=code.value, severity=severity_of(code).value, params=tuple(sorted(params.items())))


def validate_input(analysis_input: AnalysisInput) -> tuple[ReasonEntry, ...]:
    """Hard structural validation (see ``finguard_core.validation``).
    Raises :class:`InputValidationError` (a ``ValueError``) carrying every
    violation as a machine-readable ``rule:subject`` string; returns an
    empty tuple when the input is well-formed.
    """

    validate_or_raise(analysis_input)
    return ()


def _prepare(analysis_input: AnalysisInput) -> tuple[AnalysisInput, str]:
    validate_or_raise(analysis_input)
    normalized = normalize_input(analysis_input)
    return normalized, compute_input_hash(normalized)


def forecast(analysis_input: AnalysisInput) -> ForecastResult:
    normalized, the_hash = _prepare(analysis_input)
    baseline = build_baseline_forecast(normalized)
    return ForecastResult(
        certifiable_window=baseline.certifiable_window,
        baseline_series=baseline.series,
        baseline_summary=baseline.summary,
        considered_commitments=baseline.considered_commitments,
        engine_config_echo=normalized.config,
        fx_usage=baseline.fx_log.entries(),
        variable_spend=baseline.variable_spend,
        assumptions=_to_reason_entries(baseline.assumptions),
        issues=_to_reason_entries(baseline.issues),
        input_hash=the_hash,
    )


def _context_reasons(
    inp: AnalysisInput,
    baseline: BaselineForecast,
    full_payment: CandidateResult,
    earliest: object,
) -> tuple[ReasonEntry, ...]:
    out: list[ReasonEntry] = []
    summary: BaselineSummary = baseline.summary
    if summary.lowest is not None:
        out.append(
            _entry(ReasonCode.LOWEST_POINT, date=summary.lowest.day.isoformat(), balance=str(summary.lowest.balance))
        )
    if summary.below_reserve and summary.first_breach_date is not None and summary.last_breach_date is not None:
        out.append(
            _entry(
                ReasonCode.BASELINE_BELOW_RESERVE,
                first=summary.first_breach_date.isoformat(),
                last=summary.last_breach_date.isoformat(),
                days=str(summary.days_below),
                max_shortfall=str(summary.max_shortfall),
            )
        )
    if full_payment.eligible and not full_payment.safe and full_payment.breach_days:
        first = full_payment.breach_days[0]
        out.append(
            _entry(
                ReasonCode.RESERVE_BREACH_IF_PAID_NOW,
                date=first.day.isoformat(),
                shortfall=str(first.reserve - first.plan_low),
                cause={"causes": "purchase_causes", "worsens": "worsens_existing", "unrelated": "unrelated"}[
                    first.attribution.value
                ],
            )
        )
    if earliest is not None and earliest != inp.as_of:
        out.append(_entry(ReasonCode.FULL_PAYMENT_SAFE_FROM, date=str(earliest)))
    return tuple(out)


def _core(inp: AnalysisInput, the_hash: str) -> AnalysisResult:
    """The full analysis on an already validated, normalized input. Does
    not compute missing-information entries (so shadow re-analyses cannot
    recurse).
    """

    baseline = build_baseline_forecast(inp)
    common = {
        "baseline_summary": baseline.summary,
        "considered_commitments": baseline.considered_commitments,
        "engine_config_echo": inp.config,
        "variable_spend": baseline.variable_spend,
        "certifiable_window": baseline.certifiable_window,
        "input_hash": the_hash,
        "missing_information": (),
    }

    candidates: list[CandidateResult] = []
    earliest = None
    full_payment: CandidateResult | None = None
    blocked = baseline.blocked
    if not blocked:
        full_payment = generate_full_payment_candidate(inp, baseline)
        installments = generate_installment_candidates(inp, baseline)
        wait = generate_wait_candidate(inp, baseline)
        partial = generate_partial_candidate(inp, baseline)
        changes = generate_spending_change_candidate(inp, baseline, full_payment)
        candidates = [full_payment, *installments, wait, partial]
        if changes is not None:
            candidates.append(changes)
        blocked = any(c.rejection_code == ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION.value for c in candidates)
        if not blocked:
            earliest = find_earliest_full_payment_date(inp, baseline)

    issues = list(baseline.issues)
    if blocked and ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION not in issues:
        issues.append(ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION)

    if blocked:
        return AnalysisResult(
            status=AffordabilityStatus.NOT_AFFORDABLE,
            chosen=None,
            candidates=(),
            reasons=(_entry(ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION),),
            assumptions=_to_reason_entries(baseline.assumptions),
            issues=_to_reason_entries(issues),
            data_quality=compute_data_quality(issues, baseline.assumptions, True),
            earliest_full_payment_date=None,
            fx_usage=baseline.fx_log.entries(),
            certified=False,
            **common,  # type: ignore[arg-type]
        )

    assert full_payment is not None
    chosen = rank_candidates(tuple(candidates))
    status = map_status(chosen, inp.as_of)
    top_reasons: list[ReasonEntry] = []
    if chosen is not None:
        top_reasons.extend(chosen.reasons)
    else:
        top_reasons.append(_entry(ReasonCode.NO_SAFE_OPTION))
    top_reasons.extend(_context_reasons(inp, baseline, full_payment, earliest))

    return AnalysisResult(
        status=AffordabilityStatus(status),
        chosen=chosen,
        candidates=tuple(candidates),
        reasons=tuple(top_reasons),
        assumptions=_to_reason_entries(baseline.assumptions),
        issues=_to_reason_entries(issues),
        data_quality=compute_data_quality(issues, baseline.assumptions, False),
        earliest_full_payment_date=earliest,
        fx_usage=baseline.fx_log.entries(),
        certified=True,
        **common,  # type: ignore[arg-type]
    )


def analyze(analysis_input: AnalysisInput) -> AnalysisResult:
    normalized, the_hash = _prepare(analysis_input)
    result = _core(normalized, the_hash)
    missing = compute_missing_information(normalized, result, lambda shadow: _core(shadow, the_hash))
    return replace(result, missing_information=missing)


__all__ = [
    "CandidateType",
    "InputValidationError",
    "analyze",
    "collect_violations",
    "forecast",
    "validate_input",
]
