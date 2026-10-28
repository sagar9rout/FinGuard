"""Property-style tests over randomized synthetic inputs.

``hypothesis`` could not be installed in this environment (no network
access to PyPI from this session — see the PR-1 report's deviations
section). These tests substitute a fixed-seed ``random.Random`` sweep
over many synthetic cases, which gives the same kind of broad coverage
with full reproducibility (the seed is fixed, so a failure is always
reproducible) and no new dependency. If ``hypothesis`` becomes available
later, these should be reformulated as ``@given`` strategies over the
same value ranges.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from finguard_core import analyze
from finguard_core.contracts import BreachAttribution
from tests.support.builders import make_input, make_profile, make_purchase

SEED = 20261004
N_CASES = 300


def _random_decimal(rng: random.Random, lo: int, hi: int) -> Decimal:
    return Decimal(rng.randint(lo * 100, hi * 100)) / Decimal(100)


def test_safety_predicate_is_the_only_rejection_reason_never_a_bare_baseline_breach():
    """For every randomized case, a candidate's rejection is never
    reported solely because the baseline itself has a breach unrelated
    to the candidate — the predicate is always plan_low >= reserve, and
    'unrelated' days are recorded, not used to reject.
    """

    rng = random.Random(SEED)
    as_of = date(2026, 2, 1)

    for _ in range(N_CASES):
        balance = _random_decimal(rng, 0, 20000)
        reserve = _random_decimal(rng, 0, 10000)
        amount = _random_decimal(rng, 0, 15000)

        profile = make_profile(current_available_balance=balance, minimum_balance_to_keep=reserve)
        purchase = make_purchase(amount=amount, currency="INR", allows_partial_payment=False)
        result = analyze(make_input(as_of=as_of, profile=profile, purchase=purchase))

        full_payment_today = next(
            c for c in result.candidates if c.candidate_type.value == "full_payment"
        )
        if full_payment_today.eligible:
            plan_low_today = balance - amount
            expected_safe = plan_low_today >= reserve
            assert full_payment_today.safe == expected_safe, (balance, reserve, amount)
            if not expected_safe and balance >= reserve:
                # The baseline (no events at all) is safe on as_of exactly
                # when balance >= reserve. When that holds and the plan is
                # still unsafe, the purchase is what did it: CAUSES.
                for breach in full_payment_today.breach_days:
                    assert breach.attribution is BreachAttribution.CAUSES


def test_canonical_hash_is_stable_under_repeated_computation():
    from finguard_core.canonical import input_hash

    rng = random.Random(SEED + 1)
    as_of = date(2026, 3, 1)
    for _ in range(50):
        balance = _random_decimal(rng, 0, 50000)
        reserve = _random_decimal(rng, 0, 20000)
        amount = _random_decimal(rng, 0, 30000)
        profile = make_profile(current_available_balance=balance, minimum_balance_to_keep=reserve)
        purchase = make_purchase(amount=amount, currency="INR")
        analysis_input = make_input(as_of=as_of, profile=profile, purchase=purchase)

        first = input_hash(analysis_input)
        second = input_hash(analysis_input)
        third = input_hash(make_input(as_of=as_of, profile=profile, purchase=purchase))
        assert first == second == third


def test_ranking_never_prefers_a_candidate_requiring_more_spending_changes():
    """Among safe, eligible candidates, one requiring strictly fewer
    spending changes must never lose to one requiring more, regardless
    of their relative cost — ADR 0009's ranking order is lexicographic,
    changes-count first.
    """

    from finguard_core.contracts import CandidateResult, CandidateType, SpendingChangeAction, SpendingChangeEntry
    from finguard_core.decision import rank_candidates

    rng = random.Random(SEED + 2)
    as_of = date(2026, 4, 1)

    def _candidate(n_changes: int, cost: Decimal, first_day_offset: int) -> CandidateResult:
        changes = tuple(
            SpendingChangeEntry(
                target_id=f"t{i}", action=SpendingChangeAction.STOP, category="x",
                amount_changed=Decimal(10), window_total_saving=Decimal(10),
            )
            for i in range(n_changes)
        )
        return CandidateResult(
            candidate_type=CandidateType.FULL_PAYMENT, option_id=None, safe=True, eligible=True,
            rejection_code=None, first_payment_date=as_of + timedelta(days=first_day_offset),
            final_payment_date=as_of + timedelta(days=first_day_offset), total_cost=cost,
            schedule=(), spending_changes=changes, breach_days=(), reasons=(),
        )

    for _ in range(50):
        fewer_changes = _candidate(0, _random_decimal(rng, 100, 10000), rng.randint(0, 30))
        more_changes = _candidate(rng.randint(1, 3), _random_decimal(rng, 0, 99), rng.randint(0, 30))
        chosen = rank_candidates((more_changes, fewer_changes))
        assert chosen is fewer_changes
