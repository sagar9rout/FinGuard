"""P1-1: evidence conflict semantics and the exact Phase-1 boundary
(ADR 0004; ADR 0010). Locked precedence on the same target and field:
1. explicit cancellation/settlement/amendment, 2. newer record from the
same source, 3. settlement, 4. financially safer interpretation.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from finguard_core import analyze, validate_input
from finguard_core.contracts import (
    EventDirection,
    EventStatus,
    EvidenceFact,
    FactConfirmation,
    FactDirection,
    FactKind,
)
from finguard_core.evidence import apply_evidence_facts, derive_direction
from finguard_core.validation import InputValidationError
from tests.support.builders import AS_OF, make_event, make_fact, make_input

CONFIRMED, PROPOSED = FactConfirmation.CONFIRMED, FactConfirmation.PROPOSED
REDUCING, INCREASING = FactDirection.REDUCING, FactDirection.INCREASING

BILL = make_event("bill", AS_OF + timedelta(days=5), Decimal("1000"), status=EventStatus.SCHEDULED)
PAYDAY = make_event(
    "pay",
    AS_OF + timedelta(days=5),
    Decimal("1000"),
    direction=EventDirection.CREDIT,
    status=EventStatus.SCHEDULED,
    category="salary",
)


def fact(fact_id, kind, target="bill", confirmation=CONFIRMED, direction=REDUCING, **kw):
    return make_fact(fact_id, direction=direction, confirmation=confirmation, kind=kind, target_event_id=target, **kw)


def run(events, facts):
    adjusted, codes = apply_evidence_facts(events, facts, AS_OF)
    return {e.event_id: e for e in adjusted}, {c.value for c in codes}


# --- asymmetric trust ------------------------------------------------------


def test_unconfirmed_reducing_fact_applies_conservatively():
    out, codes = run([BILL], [fact("f", FactKind.AMOUNT_CHANGE, confirmation=PROPOSED, amount=Decimal("1500"))])
    assert out["bill"].amount == Decimal("1500")
    assert "FACT_APPLIED_UNCONFIRMED_CONSERVATIVE" in codes


def test_unconfirmed_increasing_fact_is_ignored_and_recorded():
    out, codes = run([BILL], [fact("f", FactKind.EXCLUSION, confirmation=PROPOSED, direction=INCREASING)])
    assert out["bill"].status is EventStatus.SCHEDULED
    assert "FACT_UNCONFIRMED_IGNORED" in codes


def test_confirmed_increasing_fact_applies():
    out, codes = run([BILL], [fact("f", FactKind.EXCLUSION, direction=INCREASING)])
    assert out["bill"].status is EventStatus.CANCELLED
    assert "FACT_APPLIED" in codes


def test_a_fact_cannot_understate_its_own_risk_the_engine_derives_direction():
    # Declared "reducing" but it actually removes a debit: increasing, so
    # an unconfirmed claim must not be applied.
    out, codes = run([BILL], [fact("f", FactKind.EXCLUSION, confirmation=PROPOSED, direction=REDUCING)])
    assert out["bill"].status is EventStatus.SCHEDULED
    assert "FACT_UNCONFIRMED_IGNORED" in codes


def test_direction_is_relative_to_event_direction():
    cancel_credit = replace(BILL, status=EventStatus.CANCELLED)
    assert derive_direction(BILL, cancel_credit, AS_OF) is INCREASING
    assert derive_direction(PAYDAY, replace(PAYDAY, status=EventStatus.CANCELLED), AS_OF) is REDUCING


def test_failed_debit_reinstatement_is_reducing_and_applies_unconfirmed():
    failed = replace(BILL, status=EventStatus.FAILED)
    out, codes = run([failed], [fact("f", FactKind.INCLUSION, confirmation=PROPOSED)])
    assert out["bill"].status is EventStatus.SCHEDULED
    assert "FACT_APPLIED_UNCONFIRMED_CONSERVATIVE" in codes


# --- locked precedence -----------------------------------------------------


def test_1_explicit_cancellation_beats_reinstatement():
    failed = replace(BILL, status=EventStatus.FAILED)
    facts = [fact("a-incl", FactKind.INCLUSION), fact("z-excl", FactKind.EXCLUSION, direction=INCREASING)]
    out, codes = run([failed], facts)
    assert out["bill"].status is EventStatus.CANCELLED
    assert "FACT_CONFLICT" in codes


def test_2_newer_record_from_same_source_wins():
    older = fact("a", FactKind.AMOUNT_CHANGE, amount=Decimal("1200"), source="bank", recorded_date=AS_OF)
    newer = fact(
        "b",
        FactKind.AMOUNT_CHANGE,
        amount=Decimal("1100"),
        source="bank",
        recorded_date=AS_OF + timedelta(days=1),
        direction=INCREASING,
    )
    # The newer record is the *less* cautious one (increasing) yet still wins
    # because rule 2 outranks rule 4.
    out, _ = run([BILL], [older, newer])
    assert out["bill"].amount == Decimal("1100")


def test_2_does_not_apply_across_different_sources():
    a = fact("a", FactKind.AMOUNT_CHANGE, amount=Decimal("1200"), source="bank", recorded_date=AS_OF)
    b = fact(
        "b",
        FactKind.AMOUNT_CHANGE,
        amount=Decimal("1100"),
        source="email",
        recorded_date=AS_OF + timedelta(days=9),
        direction=INCREASING,
    )
    out, _ = run([BILL], [a, b])
    assert out["bill"].amount == Decimal("1200")  # falls through to rule 4: safer (reducing) wins


def test_3_settlement_beats_other_explicit_status_facts():
    facts = [
        fact("a-cancel", FactKind.EXCLUSION, direction=INCREASING),
        fact("b-settle", FactKind.SETTLEMENT, direction=INCREASING),
    ]
    out, _ = run([BILL], facts)
    assert out["bill"].status is EventStatus.SETTLED


def test_4_financially_safer_interpretation_wins_when_nothing_else_decides():
    facts = [
        fact("a", FactKind.AMOUNT_CHANGE, amount=Decimal("400"), direction=INCREASING),
        fact("b", FactKind.AMOUNT_CHANGE, amount=Decimal("1300"), direction=REDUCING),
    ]
    out, _ = run([BILL], facts)
    assert out["bill"].amount == Decimal("1300")


def test_fact_id_makes_the_outcome_total_and_independent_of_input_order():
    facts = [
        fact("a", FactKind.AMOUNT_CHANGE, amount=Decimal("1300")),
        fact("b", FactKind.AMOUNT_CHANGE, amount=Decimal("1400")),
    ]
    forward, _ = run([BILL], facts)
    backward, _ = run([BILL], list(reversed(facts)))
    assert forward == backward and forward["bill"].amount == Decimal("1300")


def test_facts_on_different_fields_do_not_conflict():
    facts = [
        fact("amt", FactKind.AMOUNT_CHANGE, amount=Decimal("1300")),
        fact("dt", FactKind.DATE_CHANGE, effective_date=AS_OF + timedelta(days=2)),
    ]
    out, codes = run([BILL], facts)
    assert out["bill"].amount == Decimal("1300")
    assert out["bill"].event_date == AS_OF + timedelta(days=2)
    assert "FACT_CONFLICT" not in codes


# --- supported kinds (Phase-1 boundary) ----------------------------------


def test_date_change_moving_a_debit_earlier_is_reducing_later_is_increasing():
    earlier = fact("e", FactKind.DATE_CHANGE, confirmation=PROPOSED, effective_date=AS_OF + timedelta(days=1))
    later = fact(
        "l",
        FactKind.DATE_CHANGE,
        confirmation=PROPOSED,
        effective_date=AS_OF + timedelta(days=20),
        direction=INCREASING,
    )
    out_e, codes_e = run([BILL], [earlier])
    out_l, codes_l = run([BILL], [later])
    assert out_e["bill"].event_date == AS_OF + timedelta(days=1)
    assert "FACT_APPLIED_UNCONFIRMED_CONSERVATIVE" in codes_e
    assert out_l["bill"].event_date == BILL.event_date
    assert "FACT_UNCONFIRMED_IGNORED" in codes_l


def test_settlement_removes_a_future_obligation_only_when_confirmed():
    confirmed, _ = run([BILL], [fact("s", FactKind.SETTLEMENT, direction=INCREASING)])
    proposed, codes = run([BILL], [fact("s", FactKind.SETTLEMENT, confirmation=PROPOSED, direction=INCREASING)])
    assert confirmed["bill"].status is EventStatus.SETTLED
    assert proposed["bill"].status is EventStatus.SCHEDULED
    assert "FACT_UNCONFIRMED_IGNORED" in codes


def test_end_to_end_unconfirmed_exclusion_cannot_make_a_purchase_safe():
    heavy = make_event("heavy", AS_OF + timedelta(days=3), Decimal("9000"), status=EventStatus.SCHEDULED)
    exclusion = fact("x", FactKind.EXCLUSION, target="heavy", confirmation=PROPOSED, direction=INCREASING)
    base = analyze(make_input(events=(heavy,)))
    with_unconfirmed = analyze(make_input(events=(heavy,), evidence_facts=(exclusion,)))
    with_confirmed = analyze(make_input(events=(heavy,), evidence_facts=(replace(exclusion, confirmation=CONFIRMED),)))
    assert with_unconfirmed.status == base.status
    assert with_unconfirmed.status != with_confirmed.status


# --- exact Phase-1 boundary (rejected, never silently ignored) -------------


def test_commitment_targeted_facts_are_rejected_not_ignored():
    f = EvidenceFact(
        fact_id="c",
        direction=REDUCING,
        confirmation=CONFIRMED,
        kind=FactKind.AMOUNT_CHANGE,
        target_event_id=None,
        target_commitment_id="rent",
        amount=Decimal("1"),
    )
    with pytest.raises(InputValidationError) as err:
        validate_input(make_input(evidence_facts=(f,)))
    assert "fact_commitment_target_unsupported:c" in err.value.violations
    assert "fact_missing_target:c" in err.value.violations


def test_facts_with_unknown_target_or_missing_payload_are_rejected():
    facts = (
        fact("u", FactKind.EXCLUSION, target="nope"),
        fact("a", FactKind.AMOUNT_CHANGE, target="bill"),
        fact("d", FactKind.DATE_CHANGE, target="bill"),
    )
    with pytest.raises(InputValidationError) as err:
        validate_input(make_input(events=(BILL,), evidence_facts=facts))
    for rule in ("fact_unknown_target:u", "fact_amount_change_without_amount:a", "fact_date_change_without_date:d"):
        assert rule in err.value.violations
