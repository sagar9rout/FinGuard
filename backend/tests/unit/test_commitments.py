"""Commitment precedence and overlap resolution (docs/engine/semantics.md
Section 6).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from finguard_core.commitments import effective_commitment_amount, resolve_commitments
from finguard_core.contracts import CommitmentStatus, CommitmentTier, EngineConfig, EventDirection
from tests.support.builders import make_commitment

AS_OF = date(2026, 1, 1)
CONFIG = EngineConfig()


def test_debit_commitment_amount_uses_higher_of_median_or_recent():
    c = make_commitment(
        "c", direction=EventDirection.DEBIT, amount_median=Decimal("1000"), amount_most_recent=Decimal("1200")
    )
    assert effective_commitment_amount(c) == Decimal("1200")


def test_credit_commitment_amount_uses_lower_of_median_or_recent():
    c = make_commitment(
        "c", direction=EventDirection.CREDIT, amount_median=Decimal("1000"), amount_most_recent=Decimal("1200")
    )
    assert effective_commitment_amount(c) == Decimal("1000")


def test_user_declared_outranks_confirmed_which_outranks_detected():
    user_declared = make_commitment("a", tier=CommitmentTier.USER_DECLARED, anchor_day=1)
    confirmed = make_commitment("b", tier=CommitmentTier.CONFIRMED, anchor_day=1)
    detected = make_commitment("c", tier=CommitmentTier.DETECTED, anchor_day=1)

    result = resolve_commitments((detected, confirmed, user_declared), AS_OF, CONFIG)
    assert result.kept == (user_declared,)
    assert _suppressed(result) == {"b": "a", "c": "a"}


def test_non_overlapping_commitments_are_all_kept():
    a = make_commitment("a", category="rent", anchor_day=1)
    b = make_commitment("b", category="utilities", anchor_day=1)
    result = resolve_commitments((a, b), AS_OF, CONFIG)
    assert set(c.commitment_id for c in result.kept) == {"a", "b"}


def test_overlap_by_matching_normalized_description():
    a = make_commitment("a", tier=CommitmentTier.CONFIRMED, description="Netflix Subscription", anchor_day=1)
    b = make_commitment("b", tier=CommitmentTier.DETECTED, description="  netflix   subscription ", anchor_day=20)
    result = resolve_commitments((a, b), AS_OF, CONFIG)
    assert result.kept == (a,)
    assert _status(result, "b") is CommitmentStatus.SUPPRESSED_OVERLAP


def test_overlap_by_anchor_day_and_amount_tolerance():
    a = make_commitment(
        "a", tier=CommitmentTier.CONFIRMED, anchor_day=5,
        amount_median=Decimal("1000"), amount_most_recent=Decimal("1000"),
    )
    b = make_commitment(
        "b", tier=CommitmentTier.DETECTED, anchor_day=7,
        amount_median=Decimal("1050"), amount_most_recent=Decimal("1050"),
    )
    result = resolve_commitments((a, b), AS_OF, CONFIG)
    assert result.kept == (a,)


def test_anchor_day_outside_tolerance_does_not_overlap():
    a = make_commitment(
        "a", tier=CommitmentTier.CONFIRMED, anchor_day=1,
        amount_median=Decimal("1000"), amount_most_recent=Decimal("1000"),
    )
    b = make_commitment(
        "b", tier=CommitmentTier.DETECTED, anchor_day=10,
        amount_median=Decimal("1000"), amount_most_recent=Decimal("1000"),
    )
    result = resolve_commitments((a, b), AS_OF, CONFIG)
    assert set(c.commitment_id for c in result.kept) == {"a", "b"}


def test_amount_outside_tolerance_does_not_overlap():
    a = make_commitment(
        "a", tier=CommitmentTier.CONFIRMED, anchor_day=1,
        amount_median=Decimal("1000"), amount_most_recent=Decimal("1000"),
    )
    b = make_commitment(
        "b", tier=CommitmentTier.DETECTED, anchor_day=1,
        amount_median=Decimal("1500"), amount_most_recent=Decimal("1500"),
    )
    result = resolve_commitments((a, b), AS_OF, CONFIG)
    assert set(c.commitment_id for c in result.kept) == {"a", "b"}


def test_user_rejected_commitment_is_never_kept_and_suppresses_overlapping_ones():
    rejected = make_commitment("r", tier=CommitmentTier.USER_DECLARED, anchor_day=1, user_rejected=True)
    detected = make_commitment("d", tier=CommitmentTier.DETECTED, anchor_day=1)
    result = resolve_commitments((rejected, detected), AS_OF, CONFIG)
    assert result.kept == ()
    assert _status(result, "r") is CommitmentStatus.REJECTED
    assert _status(result, "d") is CommitmentStatus.SUPPRESSED_BY_USER_REJECTION
    assert _suppressed(result) == {"d": "r"}


def test_stale_detected_commitment_lapses():
    old = make_commitment("old", tier=CommitmentTier.DETECTED, period_days=30, last_seen=date(2025, 1, 1))
    result = resolve_commitments((old,), AS_OF, CONFIG)
    assert result.kept == ()
    assert _status(result, "old") is CommitmentStatus.LAPSED


def test_resolution_never_deletes_only_suppresses_with_a_recorded_reason():
    a = make_commitment("a", tier=CommitmentTier.CONFIRMED, anchor_day=1)
    b = make_commitment("b", tier=CommitmentTier.DETECTED, anchor_day=1)
    result = resolve_commitments((a, b), AS_OF, CONFIG)
    assert len(result.records) == 2  # nothing is deleted
    assert _suppressed(result) == {"b": "a"}
    assert _status(result, "b") is CommitmentStatus.SUPPRESSED_OVERLAP


def test_detected_income_is_excluded_not_applied():
    """ADR 0005: detected-but-unconfirmed income never enters spendable cash."""

    income = make_commitment(
        "salary", direction=EventDirection.CREDIT, category="salary", tier=CommitmentTier.DETECTED
    )
    result = resolve_commitments((income,), AS_OF, CONFIG)
    assert result.kept == ()
    assert _status(result, "salary") is CommitmentStatus.UNCONFIRMED_INCOME_EXCLUDED


def test_confirmed_and_user_declared_income_is_applied():
    for tier in (CommitmentTier.CONFIRMED, CommitmentTier.USER_DECLARED):
        income = make_commitment("salary", direction=EventDirection.CREDIT, category="salary", tier=tier)
        result = resolve_commitments((income,), AS_OF, CONFIG)
        assert result.kept == (income,)
        assert _status(result, "salary") is CommitmentStatus.APPLIED


def test_detected_expense_is_still_projected_pessimistically():
    expense = make_commitment(
        "sub", direction=EventDirection.DEBIT, category="subscriptions", tier=CommitmentTier.DETECTED
    )
    result = resolve_commitments((expense,), AS_OF, CONFIG)
    assert result.kept == (expense,)


def _status(result, commitment_id):
    return next(r.status for r in result.records if r.commitment.commitment_id == commitment_id)


def _suppressed(result):
    return {
        r.commitment.commitment_id: r.suppressed_by for r in result.records if r.suppressed_by is not None
    }
