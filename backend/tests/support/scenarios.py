"""A rich synthetic scenario that populates EVERY unordered input
collection, used by the order-independence and determinism tests. All
values are invented; none are derived from any dataset.
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from finguard_core.contracts import (
    AnalysisInput,
    CommitmentTier,
    EventDirection,
    EventStatus,
    FactConfirmation,
    FactDirection,
    FactKind,
)
from tests.support.builders import (
    AS_OF,
    make_commitment,
    make_event,
    make_fact,
    make_fx_rate,
    make_input,
    make_installment_option,
    make_preferences,
    make_profile,
    make_purchase,
)


def rich_scenario() -> AnalysisInput:
    events = []
    # History for variable spend: settled groceries/transport, ~8 weeks.
    for i in range(1, 57, 4):
        events.append(make_event(f"h-groc-{i}", AS_OF - timedelta(days=i), Decimal("180"), category="groceries"))
        events.append(make_event(f"h-trans-{i}", AS_OF - timedelta(days=i + 1), Decimal("40"), category="transport"))
    # A foreign-currency settled history event and upcoming foreign debit.
    events.append(make_event("h-usd", AS_OF - timedelta(days=20), Decimal("12"), currency="USD", category="groceries"))
    events.append(
        make_event("f-usd", AS_OF + timedelta(days=9), Decimal("30"), currency="USD", status=EventStatus.SCHEDULED)
    )
    # Recurring stoppable group (explicit occurrences) and reducible dining.
    for week in range(1, 5):
        events.append(
            make_event(
                f"gym-{week}",
                AS_OF + timedelta(days=week * 7),
                Decimal("800"),
                status=EventStatus.SCHEDULED,
                category="entertainment",
                is_stoppable=True,
                recurrence_group_id="gym",
            )
        )
        events.append(
            make_event(
                f"dine-{week}",
                AS_OF + timedelta(days=week * 7 + 2),
                Decimal("400"),
                status=EventStatus.SCHEDULED,
                category="dining",
                is_reducible=True,
                minimum_allowed_amount=Decimal("150"),
                recurrence_group_id="dine",
            )
        )
    events.append(
        make_event("rent-1", AS_OF + timedelta(days=5), Decimal("2500"), status=EventStatus.SCHEDULED, category="rent")
    )
    events.append(
        make_event(
            "pay-1",
            AS_OF + timedelta(days=12),
            Decimal("4000"),
            direction=EventDirection.CREDIT,
            status=EventStatus.SCHEDULED,
            category="salary",
        )
    )
    events.append(
        make_event("pend-1", AS_OF + timedelta(days=3), Decimal("300"), status=EventStatus.PENDING, category="other")
    )
    events.append(
        make_event("fail-1", AS_OF - timedelta(days=2), Decimal("500"), status=EventStatus.FAILED, category="utilities")
    )

    commitments = (
        make_commitment(
            "c-rent",
            category="rent",
            description="Flat rent",
            amount_median=Decimal("2500"),
            tier=CommitmentTier.CONFIRMED,
        ),
        make_commitment(
            "c-rent-dup",
            category="rent",
            description="Flat rent",
            amount_median=Decimal("2500"),
            tier=CommitmentTier.DETECTED,
        ),
        make_commitment(
            "c-net",
            category="utilities",
            anchor_day=10,
            amount_median=Decimal("600"),
            amount_most_recent=Decimal("650"),
            tier=CommitmentTier.DETECTED,
        ),
        make_commitment(
            "c-sal-detected",
            direction=EventDirection.CREDIT,
            category="salary",
            anchor_day=20,
            amount_median=Decimal("9000"),
            amount_most_recent=Decimal("9000"),
            tier=CommitmentTier.DETECTED,
        ),
        make_commitment(
            "c-sal-confirmed",
            direction=EventDirection.CREDIT,
            category="side",
            anchor_day=25,
            amount_median=Decimal("500"),
            amount_most_recent=Decimal("450"),
            tier=CommitmentTier.CONFIRMED,
        ),
        make_commitment(
            "c-gym-rejected", category="entertainment", anchor_day=8, tier=CommitmentTier.DETECTED, user_rejected=True
        ),
    )
    facts = (
        make_fact(
            "fact-b",
            direction=FactDirection.REDUCING,
            confirmation=FactConfirmation.PROPOSED,
            kind=FactKind.AMOUNT_CHANGE,
            target_event_id="rent-1",
            amount=Decimal("2700"),
        ),
        make_fact(
            "fact-a",
            direction=FactDirection.INCREASING,
            confirmation=FactConfirmation.PROPOSED,
            kind=FactKind.EXCLUSION,
            target_event_id="rent-1",
        ),
        make_fact(
            "fact-c",
            direction=FactDirection.REDUCING,
            confirmation=FactConfirmation.CONFIRMED,
            kind=FactKind.INCLUSION,
            target_event_id="fail-1",
        ),
        make_fact(
            "fact-d",
            direction=FactDirection.INCREASING,
            confirmation=FactConfirmation.PROPOSED,
            kind=FactKind.EXCLUSION,
            target_event_id="pend-1",
        ),
    )
    options = (
        make_installment_option(
            "opt-a",
            (
                (AS_OF + timedelta(days=1), Decimal("2000")),
                (AS_OF + timedelta(days=31), Decimal("2000")),
                (AS_OF + timedelta(days=61), Decimal("2100")),
            ),
        ),
        make_installment_option("opt-b", ((AS_OF, Decimal("3000")), (AS_OF + timedelta(days=30), Decimal("3000")))),
    )
    rates = (
        make_fx_rate("USD", "INR", AS_OF - timedelta(days=40), Decimal("82.5")),
        make_fx_rate("USD", "INR", AS_OF - timedelta(days=10), Decimal("83.25")),
        make_fx_rate("EUR", "INR", AS_OF - timedelta(days=10), Decimal("90")),
        make_fx_rate("USD", "EUR", AS_OF - timedelta(days=10), Decimal("0.92")),
        make_fx_rate("USD", "INR", AS_OF - timedelta(days=70), Decimal("81")),
    )
    prefs = make_preferences(
        stoppable_categories=("entertainment", "subscriptions"),
        reducible_categories=("dining", "food"),
        protected_categories=("rent", "medical"),
        category_min_allowed=(("dining", Decimal("100")), ("food", Decimal("50"))),
        variable_spend_categories=("groceries", "transport"),
    )
    return make_input(
        events=tuple(events),
        commitments=commitments,
        evidence_facts=facts,
        payment_options=options,
        fx_rates=rates,
        profile=make_profile(current_available_balance=Decimal("10000"), minimum_balance_to_keep=Decimal("3000")),
        purchase=make_purchase(amount=Decimal("6000"), desired_completion_date=AS_OF + timedelta(days=60)),
        preferences=prefs,
    )


def shuffled(inp: AnalysisInput, rng: random.Random) -> AnalysisInput:
    """Reorder EVERY unordered collection in ``inp`` (and nothing whose
    order is semantically meaningful: schedules and ``fx_pivot_currencies``).
    """

    def mix(items):  # type: ignore[no-untyped-def]
        items = list(items)
        rng.shuffle(items)
        return tuple(items)

    prefs = inp.preferences
    return replace(
        inp,
        events=mix(inp.events),
        commitments=mix(inp.commitments),
        evidence_facts=mix(inp.evidence_facts),
        payment_options=mix(inp.payment_options),
        fx_rates=mix(inp.fx_rates),
        preferences=replace(
            prefs,
            accepted_methods=mix(prefs.accepted_methods),
            stoppable_categories=mix(prefs.stoppable_categories),
            reducible_categories=mix(prefs.reducible_categories),
            protected_categories=mix(prefs.protected_categories),
            variable_spend_categories=mix(prefs.variable_spend_categories),
            category_min_allowed=mix(prefs.category_min_allowed),
        ),
    )
