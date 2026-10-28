"""Spending-change target eligibility and ranking (docs/engine/
semantics.md Section 10; ADR 0008; ADR 0010).

Considered only to rescue an otherwise-unsafe full-payment-today
candidate. Targets are ranked by actual permitted savings across the
remaining occurrences in the certifiable window, never by gross amount:

    window_total_saving = sum over remaining occurrences of
                          permitted_saving_per_occurrence

Phase-1 boundary (ADR 0010): the engine NEVER synthesizes occurrence
dates. A target is either one explicitly supplied event, or the set of
explicitly supplied events sharing a ``recurrence_group_id``. Its
occurrences are exactly those events' counted ledger entries, so every
saving corresponds to cash that is really in the forecast, already
converted to the home currency by the same path as the ledger.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finguard_core.contracts import SpendingChangeAction, UserPreferences
from finguard_core.forecast import EventEntry
from finguard_core.reason_codes import ReasonCode


@dataclass(frozen=True, slots=True)
class SpendingChangeCandidate:
    target_id: str
    action: SpendingChangeAction
    category: str
    occurrences: tuple[tuple[date, Decimal], ...]  # (date, home-currency saving)
    window_total_saving: Decimal

    @property
    def remaining_occurrences(self) -> int:
        return len(self.occurrences)


def eligible_spending_change_candidates(
    entries: Sequence[EventEntry], preferences: UserPreferences
) -> tuple[tuple[SpendingChangeCandidate, ...], tuple[ReasonCode, ...]]:
    groups: dict[str, list[EventEntry]] = {}
    for entry in entries:
        if not (entry.is_stoppable or entry.is_reducible):
            continue
        key = f"group:{entry.group_id}" if entry.group_id is not None else entry.event_id
        groups.setdefault(key, []).append(entry)

    candidates: list[SpendingChangeCandidate] = []
    reason_codes: list[ReasonCode] = []

    for target_id in sorted(groups):
        members = sorted(groups[target_id], key=lambda e: (e.on, e.event_id))
        category = members[0].category
        if category in preferences.protected_categories:
            reason_codes.append(ReasonCode.CATEGORY_PROTECTED)
            continue

        if all(m.is_stoppable for m in members) and category in preferences.stoppable_categories:
            occurrences = tuple((m.on, m.home_amount) for m in members)
            candidates.append(
                SpendingChangeCandidate(
                    target_id=target_id,
                    action=SpendingChangeAction.STOP,
                    category=category,
                    occurrences=occurrences,
                    window_total_saving=sum((s for _d, s in occurrences), Decimal(0)),
                )
            )

        if (
            all(m.is_reducible for m in members)
            and category in preferences.reducible_categories
            and all(m.minimum_home_amount is not None and m.minimum_home_amount < m.home_amount for m in members)
        ):
            reduce_occurrences = tuple(
                (m.on, m.home_amount - (m.minimum_home_amount or Decimal(0))) for m in members
            )
            candidates.append(
                SpendingChangeCandidate(
                    target_id=target_id,
                    action=SpendingChangeAction.REDUCE,
                    category=category,
                    occurrences=reduce_occurrences,
                    window_total_saving=sum((s for _d, s in reduce_occurrences), Decimal(0)),
                )
            )

    if not candidates:
        reason_codes.append(ReasonCode.NO_ELIGIBLE_FLEXIBLE_ITEMS)

    ranked = tuple(
        sorted(candidates, key=lambda c: (-c.window_total_saving, c.target_id, c.action.value))
    )
    return ranked, tuple(reason_codes)
