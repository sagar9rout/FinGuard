"""Commitment precedence, overlap resolution, and projection
(docs/engine/semantics.md Section 6).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from finguard_core.contracts import (
    CommitmentInput,
    CommitmentStatus,
    CommitmentTier,
    EngineConfig,
    EventDirection,
    FinancialEventInput,
)
from finguard_core.currency import higher_of, lower_of

_TIER_RANK = {
    CommitmentTier.USER_DECLARED: 0,
    CommitmentTier.CONFIRMED: 1,
    CommitmentTier.DETECTED: 2,
}


def effective_commitment_amount(commitment: CommitmentInput) -> Decimal:
    """ADR 0006: a projected debit uses the higher of median / most
    recent; a projected credit uses the lower.
    """

    if commitment.direction is EventDirection.DEBIT:
        return higher_of(commitment.amount_median, commitment.amount_most_recent)
    return lower_of(commitment.amount_median, commitment.amount_most_recent)


def _normalize_description(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _circular_day_diff(a: int, b: int, period: int = 30) -> int:
    diff = abs(a - b) % period
    return min(diff, period - diff)


def _amounts_overlap(a: Decimal, b: Decimal, tolerance: Decimal) -> bool:
    larger = max(abs(a), abs(b))
    if larger == 0:
        return True
    return abs(a - b) / larger <= tolerance


def _commitments_overlap(a: CommitmentInput, b: CommitmentInput, config: EngineConfig) -> bool:
    if a.direction is not b.direction or a.currency != b.currency or a.category != b.category:
        return False
    if _normalize_description(a.description) == _normalize_description(b.description) and a.description:
        return True
    day_diff = _circular_day_diff(a.anchor_day, b.anchor_day)
    if day_diff > config.commitment_overlap_day_tolerance:
        return False
    amount_a = effective_commitment_amount(a)
    amount_b = effective_commitment_amount(b)
    return _amounts_overlap(amount_a, amount_b, config.commitment_overlap_amount_tolerance)


def _sort_key(c: CommitmentInput) -> tuple[int, Decimal, int, int, str]:
    return (
        _TIER_RANK[c.tier],
        -c.confidence,
        -c.occurrences,
        -c.last_seen.toordinal(),
        c.commitment_id,
    )


@dataclass(frozen=True, slots=True)
class CommitmentRecord:
    commitment: CommitmentInput
    status: CommitmentStatus
    suppressed_by: str | None


@dataclass(frozen=True, slots=True)
class CommitmentResolution:
    kept: tuple[CommitmentInput, ...]
    records: tuple[CommitmentRecord, ...]


_COUNTABLE_INCOME_TIERS = (CommitmentTier.USER_DECLARED, CommitmentTier.CONFIRMED)


def resolve_commitments(
    commitments: Sequence[CommitmentInput], as_of: date, config: EngineConfig
) -> CommitmentResolution:
    """Precedence/overlap resolution plus the ADR 0005 income policy.

    Only commitments that end up ``APPLIED`` are projected. A credit
    commitment is applied only if its tier is ``user_declared`` or
    ``confirmed``; a detected credit is recorded as
    ``UNCONFIRMED_INCOME_EXCLUDED`` and never enters spendable cash.
    """

    rejected = sorted((c for c in commitments if c.user_rejected), key=lambda c: c.commitment_id)
    active = sorted((c for c in commitments if not c.user_rejected), key=_sort_key)

    kept: list[CommitmentInput] = []
    records: list[CommitmentRecord] = [
        CommitmentRecord(r, CommitmentStatus.REJECTED, None) for r in rejected
    ]

    for candidate in active:
        rejected_overlap = next(
            (r for r in rejected if _commitments_overlap(candidate, r, config)), None
        )
        if rejected_overlap is not None:
            records.append(
                CommitmentRecord(
                    candidate, CommitmentStatus.SUPPRESSED_BY_USER_REJECTION, rejected_overlap.commitment_id
                )
            )
            continue

        kept_overlap = next((k for k in kept if _commitments_overlap(candidate, k, config)), None)
        if kept_overlap is not None:
            records.append(
                CommitmentRecord(candidate, CommitmentStatus.SUPPRESSED_OVERLAP, kept_overlap.commitment_id)
            )
            continue

        if candidate.tier is CommitmentTier.DETECTED:
            staleness_limit = max(candidate.period_days * 3, 1)
            if (as_of - candidate.last_seen).days > staleness_limit:
                records.append(CommitmentRecord(candidate, CommitmentStatus.LAPSED, None))
                continue

        if candidate.direction is EventDirection.CREDIT and candidate.tier not in _COUNTABLE_INCOME_TIERS:
            records.append(CommitmentRecord(candidate, CommitmentStatus.UNCONFIRMED_INCOME_EXCLUDED, None))
            continue

        kept.append(candidate)
        records.append(CommitmentRecord(candidate, CommitmentStatus.APPLIED, None))

    records.sort(key=lambda r: r.commitment.commitment_id)
    return CommitmentResolution(tuple(kept), tuple(records))


@dataclass(frozen=True, slots=True)
class ProjectedOccurrence:
    commitment_id: str
    occurrence_date: date
    amount: Decimal
    currency: str
    direction: EventDirection
    category: str
    suppressed_by_explicit_event: bool


def project_commitments(
    kept: Sequence[CommitmentInput],
    explicit_events: Sequence[FinancialEventInput],
    as_of: date,
    window_end: date,
    config: EngineConfig,
) -> tuple[ProjectedOccurrence, ...]:
    """Project each kept commitment forward at its period cadence,
    suppressing (never deleting) any occurrence that coincides with an
    explicit event for the same commitment key.
    """

    occurrences: list[ProjectedOccurrence] = []
    for commitment in kept:
        amount = effective_commitment_amount(commitment)
        period = max(commitment.period_days, 1)
        next_date = commitment.last_seen + timedelta(days=period)
        while next_date < as_of:
            next_date = next_date + timedelta(days=period)
        while next_date <= window_end:
            suppressed = any(
                e.direction == commitment.direction
                and e.currency == commitment.currency
                and e.category == commitment.category
                and abs((e.event_date - next_date).days) <= config.commitment_overlap_day_tolerance
                and e.amount is not None
                and _amounts_overlap(e.amount, amount, config.commitment_overlap_amount_tolerance)
                for e in explicit_events
            )
            occurrences.append(
                ProjectedOccurrence(
                    commitment_id=commitment.commitment_id,
                    occurrence_date=next_date,
                    amount=amount,
                    currency=commitment.currency,
                    direction=commitment.direction,
                    category=commitment.category,
                    suppressed_by_explicit_event=suppressed,
                )
            )
            next_date = next_date + timedelta(days=period)
    return tuple(occurrences)
