"""Evidence-fact application with asymmetric trust and the locked conflict
precedence (docs/engine/semantics.md Section 12; ADR 0004; ADR 0010).

Phase-1 boundary (exact, enforced by ``validation``):
- supported targets: events only (``target_event_id``); commitment-targeted
  facts are rejected as structurally unsupported;
- supported kinds: ``exclusion`` (explicit cancellation), ``settlement``,
  ``amount_change`` and ``date_change`` (explicit amendments) and
  ``inclusion`` (reinstatement of a cancelled/failed obligation).

Facts alter data, never rules. The *effect* of a fact (reducing or
increasing spendable cash) is derived by the engine from the event's cash
profile before and after the fact; a fact's declared ``direction`` can only
make the engine more cautious, never less.

Conflict precedence on the same target and field group (locked, in order):
1. explicit cancellation / settlement / amendment beats a reinstatement;
2. a newer record from the same source beats an older one;
3. a settlement beats a non-settlement;
4. the financially safer interpretation (reducing beats increasing);
5. fact identifier, purely to make the outcome total and deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal
from enum import StrEnum

from finguard_core.classification import Treatment, classify_event
from finguard_core.contracts import (
    EventDirection,
    EventStatus,
    EvidenceFact,
    FactConfirmation,
    FactDirection,
    FactKind,
    FinancialEventInput,
)
from finguard_core.reason_codes import ReasonCode


class _Group(StrEnum):
    STATUS = "status"
    AMOUNT = "amount"
    DATE = "date"


_GROUP_OF = {
    FactKind.EXCLUSION: _Group.STATUS,
    FactKind.INCLUSION: _Group.STATUS,
    FactKind.SETTLEMENT: _Group.STATUS,
    FactKind.AMOUNT_CHANGE: _Group.AMOUNT,
    FactKind.DATE_CHANGE: _Group.DATE,
}
_EXPLICIT = {FactKind.EXCLUSION, FactKind.SETTLEMENT, FactKind.AMOUNT_CHANGE, FactKind.DATE_CHANGE}


def apply_fact(event: FinancialEventInput, fact: EvidenceFact) -> FinancialEventInput:
    """The event as it would look with ``fact`` applied (pure)."""

    if fact.kind is FactKind.EXCLUSION:
        return replace(event, status=EventStatus.CANCELLED)
    if fact.kind is FactKind.SETTLEMENT:
        return replace(event, status=EventStatus.SETTLED)
    if fact.kind is FactKind.INCLUSION:
        if event.status in (EventStatus.CANCELLED, EventStatus.FAILED):
            return replace(event, status=EventStatus.SCHEDULED)
        return event
    if fact.kind is FactKind.AMOUNT_CHANGE and fact.amount is not None:
        return replace(event, amount=fact.amount)
    if fact.kind is FactKind.DATE_CHANGE and fact.effective_date is not None:
        return replace(event, event_date=fact.effective_date)
    return event


def _cash_profile(event: FinancialEventInput, as_of: date) -> dict[date, Decimal]:
    """Signed cash effect (event currency) by date, as the forecast
    would count it: reserved/overdue debits land on ``as_of``.
    """

    classified = classify_event(event, as_of)
    if (
        classified.treatment not in (Treatment.COUNTED, Treatment.RESERVED_AT_AS_OF)
        or classified.effective_date is None
        or classified.amount is None
    ):
        return {}
    sign = Decimal(-1) if classified.direction is EventDirection.DEBIT else Decimal(1)
    return {classified.effective_date: sign * classified.amount}


def derive_direction(before: FinancialEventInput, after: FinancialEventInput, as_of: date) -> FactDirection:
    """REDUCING only if, at every date, cumulative cash after is no
    greater than before; anything else (increasing or mixed) is
    INCREASING, which is the cautious reading for trust purposes.
    """

    old = _cash_profile(before, as_of)
    new = _cash_profile(after, as_of)
    cum_old = Decimal(0)
    cum_new = Decimal(0)
    for day in sorted(set(old) | set(new)):
        cum_old += old.get(day, Decimal(0))
        cum_new += new.get(day, Decimal(0))
        if cum_new > cum_old:
            return FactDirection.INCREASING
    return FactDirection.REDUCING


def _beats(a: EvidenceFact, b: EvidenceFact, effect: dict[str, FactDirection]) -> bool:
    """Does ``a`` win over ``b`` under the locked precedence?"""

    a_explicit = a.kind in _EXPLICIT
    b_explicit = b.kind in _EXPLICIT
    if a_explicit != b_explicit:
        return a_explicit
    if a.source and a.source == b.source and a.recorded_date != b.recorded_date:
        return a.recorded_date > b.recorded_date
    a_settled = a.kind is FactKind.SETTLEMENT
    b_settled = b.kind is FactKind.SETTLEMENT
    if a_settled != b_settled:
        return a_settled
    a_safe = effect[a.fact_id] is FactDirection.REDUCING
    b_safe = effect[b.fact_id] is FactDirection.REDUCING
    if a_safe != b_safe:
        return a_safe
    return a.fact_id < b.fact_id


def apply_evidence_facts(
    events: Sequence[FinancialEventInput], facts: Sequence[EvidenceFact], as_of: date
) -> tuple[tuple[FinancialEventInput, ...], tuple[ReasonCode, ...]]:
    by_id: dict[str, FinancialEventInput] = {e.event_id: e for e in events}
    codes: list[ReasonCode] = []

    grouped: dict[tuple[str, _Group], list[EvidenceFact]] = {}
    for fact in sorted(facts, key=lambda f: f.fact_id):
        if fact.target_event_id is None or fact.target_event_id not in by_id:
            continue  # rejected earlier by validation; defensive only
        grouped.setdefault((fact.target_event_id, _GROUP_OF[fact.kind]), []).append(fact)

    # Effect of each fact, derived against the *original* event.
    effect: dict[str, FactDirection] = {}
    for (target_id, _group), group_facts in grouped.items():
        original = by_id[target_id]
        for fact in group_facts:
            derived = derive_direction(original, apply_fact(original, fact), as_of)
            effect[fact.fact_id] = (
                FactDirection.INCREASING
                if FactDirection.INCREASING in (derived, fact.direction)
                else FactDirection.REDUCING
            )

    adjusted: dict[str, FinancialEventInput] = dict(by_id)
    for (target_id, _group) in sorted(grouped, key=lambda k: (k[0], k[1].value)):
        group_facts = grouped[(target_id, _group)]
        applicable: list[EvidenceFact] = []
        for fact in group_facts:
            if effect[fact.fact_id] is FactDirection.INCREASING and fact.confirmation is not FactConfirmation.CONFIRMED:
                codes.append(ReasonCode.FACT_UNCONFIRMED_IGNORED)
            else:
                applicable.append(fact)
        if len(group_facts) > 1:
            codes.append(ReasonCode.FACT_CONFLICT)
        if not applicable:
            continue
        winner = applicable[0]
        for challenger in applicable[1:]:
            if _beats(challenger, winner, effect):
                winner = challenger
        adjusted[target_id] = apply_fact(adjusted[target_id], winner)
        codes.append(
            ReasonCode.FACT_APPLIED
            if winner.confirmation is FactConfirmation.CONFIRMED
            else ReasonCode.FACT_APPLIED_UNCONFIRMED_CONSERVATIVE
        )

    return tuple(adjusted[e.event_id] for e in events), tuple(codes)
