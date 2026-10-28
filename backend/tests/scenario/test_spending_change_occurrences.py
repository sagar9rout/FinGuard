"""P1-2 / ADR 0010: spending-change targets use ONLY explicitly supplied
occurrences. The engine never synthesizes recurrence (no hardcoded
cadence), and one target is never counted twice.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from finguard_core import analyze
from finguard_core.contracts import AffordabilityStatus, CandidateType, EventStatus, SpendingChangeAction
from tests.support.builders import (
    AS_OF,
    make_event,
    make_input,
    make_preferences,
    make_profile,
    make_purchase,
)

# Balance 8,000, reserve 3,000: paying 4,000 now is safe on day 0 (4,000 left); later
# debits are what breach the reserve, so only savings on those later debits can rescue it.
PROFILE = make_profile(current_available_balance=Decimal("8000"), minimum_balance_to_keep=Decimal("3000"))
PURCHASE = make_purchase(amount=Decimal("4000"), allows_partial_payment=False)
PREFS = make_preferences(
    accepted_methods=(CandidateType.FULL_PAYMENT,),
    variable_spend_categories=(),
    stoppable_categories=("entertainment",),
    reducible_categories=("dining",),
    protected_categories=("rent",),
)


def sub(event_id, day, amount, **kw):
    return make_event(
        event_id,
        AS_OF + timedelta(days=day),
        Decimal(amount),
        status=EventStatus.SCHEDULED,
        category="entertainment",
        is_stoppable=True,
        **kw,
    )


RENT = make_event("rent", AS_OF + timedelta(days=6), Decimal("1500"), status=EventStatus.SCHEDULED, category="rent")


def run(events):
    return analyze(make_input(profile=PROFILE, purchase=PURCHASE, preferences=PREFS, events=tuple(events)))


def changes_of(result):
    return next(c for c in result.candidates if c.candidate_type is CandidateType.FULL_PAYMENT_WITH_SPENDING_CHANGES)


def test_a_single_supplied_event_is_one_occurrence_not_a_synthesized_series():
    # 600 once, plus 1,500 of unavoidable rent: deficit 1,100. Were a cadence
    # invented, 3 x 600 = 1,800 would "rescue" it; the single supplied 600 cannot.
    result = run([sub("one", 5, "600", recurrence_group_id=None), RENT])
    assert result.status is AffordabilityStatus.NOT_AFFORDABLE
    assert changes_of(result).safe is False
    assert changes_of(result).spending_changes == ()


def test_recurrence_group_counts_exactly_the_supplied_occurrences():
    two = run([sub("a", 5, "600", recurrence_group_id="g"), sub("b", 40, "600", recurrence_group_id="g")])
    assert two.status is AffordabilityStatus.AFFORDABLE_WITH_PLAN
    (change,) = changes_of(two).spending_changes
    assert change.action is SpendingChangeAction.STOP
    assert change.occurrences == 2
    assert change.window_total_saving == change.amount_changed == Decimal("1200")

    three = run(
        [sub(f"o{i}", 5 + 30 * i, "600", recurrence_group_id="g") for i in range(3)],
    )
    (change3,) = changes_of(three).spending_changes
    assert change3.occurrences == 3 and change3.window_total_saving == Decimal("1800")


def test_occurrences_outside_the_certifiable_window_are_not_savings():
    events = [sub("in", 5, "600", recurrence_group_id="g"), sub("out", 150, "600", recurrence_group_id="g"), RENT]
    config_result = analyze(
        make_input(
            profile=PROFILE,
            purchase=PURCHASE,
            preferences=PREFS,
            events=tuple(events),
        )
    )
    # default horizon is 90 days with no deadline: the day-150 event is outside the window.
    assert config_result.certifiable_window.effective_end == AS_OF + timedelta(days=90)
    # only the in-window 600 counts: 4,000 - 600 - 1,500 + 600 = 2,500 < 3,000.
    assert changes_of(config_result).safe is False


def test_reduce_saving_uses_current_minus_minimum_over_supplied_occurrences():
    events = [
        make_event(
            f"d{i}",
            AS_OF + timedelta(days=3 + 7 * i),
            Decimal("500"),
            status=EventStatus.SCHEDULED,
            category="dining",
            is_reducible=True,
            minimum_allowed_amount=Decimal("100"),
            recurrence_group_id="dine",
        )
        for i in range(3)
    ]
    # 4,000 left after paying; three dining debits of 500 take it to 2,500; reducing to 100 saves 1,200.
    (change,) = changes_of(run(events)).spending_changes
    assert change.action is SpendingChangeAction.REDUCE
    assert change.occurrences == 3 and change.window_total_saving == Decimal("1200")


def test_stop_and_reduce_of_the_same_target_are_never_combined():
    # If the same group were eligible for both, a combined "stop + reduce"
    # would double count it. The rescue must use the target only once.
    prefs = make_preferences(
        accepted_methods=(CandidateType.FULL_PAYMENT,),
        variable_spend_categories=(),
        stoppable_categories=("dining",),
        reducible_categories=("dining",),
        protected_categories=(),
    )
    events = [
        make_event(
            f"d{i}",
            AS_OF + timedelta(days=3 + 7 * i),
            Decimal("300"),
            status=EventStatus.SCHEDULED,
            category="dining",
            is_stoppable=True,
            is_reducible=True,
            minimum_allowed_amount=Decimal("100"),
            recurrence_group_id="dine",
        )
        for i in range(2)
    ] + [make_event("rent", AS_OF + timedelta(days=20), Decimal("1200"), status=EventStatus.SCHEDULED, category="rent")]
    result = analyze(make_input(profile=PROFILE, purchase=PURCHASE, preferences=prefs, events=tuple(events)))
    # deficit is 800; the best single use of the group is stop = 600, so it is NOT enough.
    # (A double-counted stop + reduce would claim 1,000 and wrongly rescue it.)
    assert changes_of(result).safe is False
    assert result.status is AffordabilityStatus.NOT_AFFORDABLE


def test_protected_category_is_never_a_target():
    events = [
        make_event(
            "r",
            AS_OF + timedelta(days=5),
            Decimal("2000"),
            status=EventStatus.SCHEDULED,
            category="rent",
            is_stoppable=True,
        )
    ]
    result = run(events)
    assert changes_of(result).safe is False
    assert "CATEGORY_PROTECTED" in {r.code for r in changes_of(result).reasons}
