"""Data quality level and missing-information entries (docs/engine/
semantics.md Section 13; ADR 0010).

The level reflects INPUT quality, never decision outcome. Rules, applied
in order:

- ``insufficient``: certification is blocked (an unconvertible debit).
- ``low``: any of BALANCE_STALE, UNRESOLVED_AMOUNT, MISSING_EVENT_DATE,
  INSUFFICIENT_HISTORY, FX_PESSIMISTIC_BOUND_USED,
  UNCONVERTIBLE_CREDIT_EXCLUDED.
- ``medium``: any of SETTLED_EVENT_IN_FUTURE, OVERDUE_SCHEDULED,
  OPTION_TOTAL_MISMATCH, FACT_CONFLICT, FACT_UNCONFIRMED_IGNORED,
  FX_PRIOR_RATE_USED, FX_TRIANGULATED.
- ``high``: otherwise.

A baseline breach, commitment overlap, or window truncation never affects
the level (decision-neutral by specification).

Missing-information impact is estimated with bounded internal shadow
re-analyses (at most two per analysis): one that confirms every proposed
fact, and one that confirms every excluded detected income. Where the
missing quantity can only ever *reduce* spendable cash (a stale balance,
unmodelled variable spend, an unknown debit), no numeric guess is made:
the impact is ``could_change_decision`` unless the result is already
not-affordable or uncertified, which further spending cannot overturn.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from finguard_core.contracts import (
    AffordabilityStatus,
    AnalysisInput,
    AnalysisResult,
    CommitmentStatus,
    CommitmentTier,
    DataQualityLevel,
    EventDirection,
    FactConfirmation,
    MissingInfoEntry,
    MissingInfoImpact,
)
from finguard_core.reason_codes import ReasonCode

_LOW = {
    ReasonCode.BALANCE_STALE,
    ReasonCode.UNRESOLVED_AMOUNT,
    ReasonCode.MISSING_EVENT_DATE,
    ReasonCode.INSUFFICIENT_HISTORY,
    ReasonCode.FX_PESSIMISTIC_BOUND_USED,
    ReasonCode.UNCONVERTIBLE_CREDIT_EXCLUDED,
}
_MEDIUM = {
    ReasonCode.SETTLED_EVENT_IN_FUTURE,
    ReasonCode.OVERDUE_SCHEDULED,
    ReasonCode.OPTION_TOTAL_MISMATCH,
    ReasonCode.FACT_CONFLICT,
    ReasonCode.FACT_UNCONFIRMED_IGNORED,
    ReasonCode.FX_PRIOR_RATE_USED,
    ReasonCode.FX_TRIANGULATED,
}


def compute_data_quality(
    issues: Sequence[ReasonCode], assumptions: Sequence[ReasonCode], blocked: bool
) -> DataQualityLevel:
    if blocked:
        return DataQualityLevel.INSUFFICIENT
    seen = set(issues) | set(assumptions)
    if seen & _LOW:
        return DataQualityLevel.LOW
    if seen & _MEDIUM:
        return DataQualityLevel.MEDIUM
    return DataQualityLevel.HIGH


def _signature(result: AnalysisResult) -> tuple[object, ...]:
    chosen = result.chosen
    return (
        result.status,
        result.certified,
        None if chosen is None else (chosen.candidate_type, chosen.option_id, chosen.first_payment_date),
    )


def _downside_only_impact(result: AnalysisResult) -> MissingInfoImpact:
    if not result.certified or result.status is AffordabilityStatus.NOT_AFFORDABLE:
        return MissingInfoImpact.INFORMATIONAL
    return MissingInfoImpact.COULD_CHANGE_DECISION


def compute_missing_information(
    inp: AnalysisInput,
    result: AnalysisResult,
    rerun: Callable[[AnalysisInput], AnalysisResult],
) -> tuple[MissingInfoEntry, ...]:
    codes = {e.code for e in result.assumptions} | {e.code for e in result.issues}
    entries: list[MissingInfoEntry] = []

    def add(field_name: str, impact: MissingInfoImpact, code: ReasonCode, subjects: Sequence[str] = ()) -> None:
        entries.append(MissingInfoEntry(field_name, impact, code.value, tuple(sorted(subjects))))

    if ReasonCode.DEADLINE_DEFAULTED.value in codes:
        add("purchase.desired_completion_date", MissingInfoImpact.INFORMATIONAL, ReasonCode.DEADLINE_DEFAULTED)

    if ReasonCode.BALANCE_STALE.value in codes:
        add("profile.balance_as_of", _downside_only_impact(result), ReasonCode.BALANCE_STALE)

    if ReasonCode.VARIABLE_SPEND_INSUFFICIENT_HISTORY.value in codes:
        add(
            "events.history",
            _downside_only_impact(result),
            ReasonCode.VARIABLE_SPEND_INSUFFICIENT_HISTORY,
            inp.preferences.variable_spend_categories,
        )

    unresolved = [e for e in inp.events if e.amount is None]
    if unresolved:
        has_credit = any(e.direction is EventDirection.CREDIT for e in unresolved)
        impact = MissingInfoImpact.COULD_CHANGE_DECISION if has_credit else _downside_only_impact(result)
        add("events.amount", impact, ReasonCode.UNRESOLVED_AMOUNT, [e.event_id for e in unresolved])

    proposed = [f for f in inp.evidence_facts if f.confirmation is FactConfirmation.PROPOSED]
    if ReasonCode.FACT_UNCONFIRMED_IGNORED.value in codes and proposed:
        shadow = replace(
            inp,
            evidence_facts=tuple(replace(f, confirmation=FactConfirmation.CONFIRMED) for f in inp.evidence_facts),
        )
        changed = _signature(rerun(shadow)) != _signature(result)
        add(
            "evidence_facts.confirmation",
            MissingInfoImpact.COULD_CHANGE_DECISION if changed else MissingInfoImpact.INFORMATIONAL,
            ReasonCode.FACT_UNCONFIRMED_IGNORED,
            [f.fact_id for f in proposed],
        )

    excluded_income = {
        c.commitment_id
        for c in result.considered_commitments
        if c.status is CommitmentStatus.UNCONFIRMED_INCOME_EXCLUDED
    }
    if excluded_income:
        shadow_commitments = tuple(
            replace(c, tier=CommitmentTier.CONFIRMED) if c.commitment_id in excluded_income else c
            for c in inp.commitments
        )
        changed = _signature(rerun(replace(inp, commitments=shadow_commitments))) != _signature(result)
        add(
            "commitments.confirmation",
            MissingInfoImpact.COULD_CHANGE_DECISION if changed else MissingInfoImpact.INFORMATIONAL,
            ReasonCode.RECURRING_INCOME_UNCONFIRMED_EXCLUDED,
            sorted(excluded_income),
        )

    entries.sort(key=lambda e: (e.field_name, e.code))
    return tuple(entries)
