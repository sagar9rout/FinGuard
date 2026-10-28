"""Spending-change eligibility and window-total-savings ranking (D-13;
docs/engine/semantics.md Section 10; ADR 0010: targets are explicitly
supplied ledger entries, never synthesized occurrences).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finguard_core.contracts import SpendingChangeAction
from finguard_core.forecast import EventEntry
from finguard_core.reason_codes import ReasonCode
from finguard_core.spending_changes import eligible_spending_change_candidates
from tests.support.builders import make_preferences

AS_OF = date(2026, 1, 1)


def entry(event_id, amount, *, day=0, category="entertainment", stop=True, reduce=False, minimum=None, group=None):
    return EventEntry(
        event_id=event_id,
        on=AS_OF + timedelta(days=day),
        home_amount=Decimal(amount),
        minimum_home_amount=None if minimum is None else Decimal(minimum),
        category=category,
        is_stoppable=stop,
        is_reducible=reduce,
        group_id=group,
    )


def test_gross_amount_is_never_the_ranking_key_window_total_is():
    big_one_off = entry("big", "500")
    recurring = tuple(entry(f"small{i}", "100", day=i * 7, group="gym") for i in range(6))
    ranked, _ = eligible_spending_change_candidates(
        (big_one_off, *recurring), make_preferences(stoppable_categories=("entertainment",))
    )
    assert ranked[0].target_id == "group:gym"
    assert ranked[0].window_total_saving == Decimal("600")
    assert ranked[0].remaining_occurrences == 6
    assert ranked[1].target_id == "big"
    assert ranked[1].window_total_saving == Decimal("500")


def test_reduce_saving_is_current_minus_minimum_summed_over_explicit_occurrences():
    members = tuple(
        entry(f"d{i}", "300", day=i * 7, category="dining", stop=False, reduce=True, minimum="100", group="dining")
        for i in range(4)
    )
    ranked, _ = eligible_spending_change_candidates(members, make_preferences(reducible_categories=("dining",)))
    assert len(ranked) == 1
    assert ranked[0].action is SpendingChangeAction.REDUCE
    assert ranked[0].window_total_saving == Decimal("800")
    assert all(saving == Decimal("200") for _d, saving in ranked[0].occurrences)


def test_occurrences_are_exactly_the_supplied_entries_no_synthesized_cadence():
    members = (entry("a", "50", day=0, group="g"), entry("b", "50", day=11, group="g"))
    ranked, _ = eligible_spending_change_candidates(members, make_preferences(stoppable_categories=("entertainment",)))
    assert [d for d, _s in ranked[0].occurrences] == [AS_OF, AS_OF + timedelta(days=11)]


def test_protected_category_is_never_touched_even_if_tagged_flexible():
    ranked, codes = eligible_spending_change_candidates(
        (entry("rent", "1000", category="rent"),),
        make_preferences(protected_categories=("rent",), stoppable_categories=("rent",)),
    )
    assert ranked == ()
    assert ReasonCode.CATEGORY_PROTECTED in codes


def test_flexibility_tag_alone_is_not_sufficient_without_user_listed_category():
    ranked, codes = eligible_spending_change_candidates(
        (entry("sub", "200", category="subscriptions"),), make_preferences(stoppable_categories=("entertainment",))
    )
    assert ranked == ()
    assert ReasonCode.NO_ELIGIBLE_FLEXIBLE_ITEMS in codes


def test_reduce_without_a_stated_minimum_is_not_eligible():
    ranked, _ = eligible_spending_change_candidates(
        (entry("dining", "300", category="dining", stop=False, reduce=True),),
        make_preferences(reducible_categories=("dining",)),
    )
    assert ranked == ()
