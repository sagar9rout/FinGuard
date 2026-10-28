"""Candidate ranking and status mapping (docs/engine/semantics.md
Section 9; ADR 0009).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from finguard_core.contracts import AffordabilityStatus, CandidateResult, CandidateType


def _candidate_sort_key(candidate: CandidateResult) -> tuple[int, Decimal, date, int, str]:
    n_changes = len(candidate.spending_changes)
    n_payments = len(candidate.schedule) if candidate.schedule else 1
    tie_break = f"{candidate.candidate_type.value}:{candidate.option_id or ''}"
    # A safe, eligible candidate always carries a first_payment_date; this
    # fallback only guards the type checker, never a real comparison.
    first_payment_date = candidate.first_payment_date or date.max
    return (
        n_changes,
        candidate.total_cost,
        first_payment_date,
        n_payments,
        tie_break,
    )


def rank_candidates(candidates: tuple[CandidateResult, ...]) -> CandidateResult | None:
    safe = [c for c in candidates if c.eligible and c.safe]
    if not safe:
        return None
    return min(safe, key=_candidate_sort_key)


def map_status(chosen: CandidateResult | None, as_of: date) -> AffordabilityStatus:
    if chosen is None:
        return AffordabilityStatus.NOT_AFFORDABLE

    if chosen.candidate_type is CandidateType.FULL_PAYMENT and chosen.first_payment_date == as_of:
        return AffordabilityStatus.AFFORDABLE_NOW

    if chosen.candidate_type in (
        CandidateType.FULL_PAYMENT_WITH_SPENDING_CHANGES,
        CandidateType.INSTALLMENTS,
        CandidateType.PARTIAL,
    ):
        return AffordabilityStatus.AFFORDABLE_WITH_PLAN

    if chosen.candidate_type is CandidateType.WAIT:
        return AffordabilityStatus.AFFORDABLE_LATER

    return AffordabilityStatus.AFFORDABLE_WITH_PLAN
