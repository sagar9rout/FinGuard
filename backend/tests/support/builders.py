"""Synthetic, public-safe test-data builders.

Every value here is invented for the test suite. None of it is derived
from the third-party dataset (see docs/dataset-provenance.md) — these
builders exist precisely so tests never need that dataset.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from finguard_core.contracts import (
    AnalysisInput,
    CandidateType,
    CommitmentInput,
    CommitmentTier,
    EngineConfig,
    EventDirection,
    EventStatus,
    EvidenceFact,
    FactConfirmation,
    FactDirection,
    FactKind,
    FinancialEventInput,
    FinancialProfile,
    FxRateEntry,
    PaymentOption,
    PaymentOptionSchedule,
    PurchaseRequest,
    UserPreferences,
)
from finguard_core.currency import default_currency_registry

AS_OF = date(2026, 1, 1)

ALL_METHODS = (
    CandidateType.FULL_PAYMENT,
    CandidateType.INSTALLMENTS,
    CandidateType.PARTIAL,
    CandidateType.WAIT,
)


def make_preferences(**overrides) -> UserPreferences:
    defaults = dict(
        accepted_methods=ALL_METHODS,
        max_installment_term_days=90,
        stoppable_categories=("entertainment",),
        reducible_categories=("dining",),
        protected_categories=("rent",),
        category_min_allowed=(),
        financial_priorities=(),
        variable_spend_categories=("groceries",),
    )
    defaults.update(overrides)
    return UserPreferences(**defaults)


def make_profile(**overrides) -> FinancialProfile:
    defaults = dict(
        home_currency="INR",
        current_available_balance=Decimal("10000"),
        minimum_balance_to_keep=Decimal("3000"),
        balance_as_of=AS_OF,
    )
    defaults.update(overrides)
    return FinancialProfile(**defaults)


def make_purchase(**overrides) -> PurchaseRequest:
    defaults = dict(
        amount=Decimal("1000"),
        currency="INR",
        desired_completion_date=None,
        allows_partial_payment=True,
    )
    defaults.update(overrides)
    return PurchaseRequest(**defaults)


def make_input(
    *,
    events: tuple[FinancialEventInput, ...] = (),
    commitments: tuple[CommitmentInput, ...] = (),
    evidence_facts: tuple[EvidenceFact, ...] = (),
    payment_options: tuple[PaymentOption, ...] = (),
    fx_rates: tuple[FxRateEntry, ...] = (),
    profile: FinancialProfile | None = None,
    purchase: PurchaseRequest | None = None,
    preferences: UserPreferences | None = None,
    as_of: date = AS_OF,
    config: EngineConfig | None = None,
) -> AnalysisInput:
    return AnalysisInput(
        as_of=as_of,
        profile=profile or make_profile(),
        events=events,
        commitments=commitments,
        evidence_facts=evidence_facts,
        purchase=purchase or make_purchase(),
        payment_options=payment_options,
        preferences=preferences or make_preferences(),
        fx_rates=fx_rates,
        config=config or EngineConfig(),
        currency_registry=default_currency_registry(),
    )


def make_minimal_input() -> AnalysisInput:
    """Balance 10,000 INR, reserve 3,000 INR, no events, purchase of
    1,000 INR today — trivially affordable now.
    """

    return make_input()


def make_input_with_unconvertible_debit() -> AnalysisInput:
    """A debit in a currency with no resolvable FX rate at all, within
    any stage — must block certification
    (``UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION``), never silently drop.
    """

    event = FinancialEventInput(
        event_id="debit-unresolvable",
        event_date=AS_OF,
        amount=Decimal("500"),
        currency="ZAR",
        direction=EventDirection.DEBIT,
        status=EventStatus.SETTLED,
        category="other",
    )
    return make_input(events=(event,))


def make_event(
    event_id: str,
    event_date: date,
    amount: Decimal,
    *,
    currency: str = "INR",
    direction: EventDirection = EventDirection.DEBIT,
    status: EventStatus = EventStatus.SETTLED,
    category: str = "other",
    **overrides,
) -> FinancialEventInput:
    defaults = dict(
        event_id=event_id,
        event_date=event_date,
        amount=amount,
        currency=currency,
        direction=direction,
        status=status,
        category=category,
    )
    defaults.update(overrides)
    return FinancialEventInput(**defaults)


def make_commitment(
    commitment_id: str,
    *,
    direction: EventDirection = EventDirection.DEBIT,
    currency: str = "INR",
    category: str = "rent",
    tier: CommitmentTier = CommitmentTier.CONFIRMED,
    confidence: Decimal = Decimal("0.9"),
    anchor_day: int = 1,
    period_days: int = 30,
    amount_median: Decimal = Decimal("1000"),
    amount_most_recent: Decimal = Decimal("1000"),
    occurrences: int = 6,
    last_seen: date = AS_OF,
    description: str = "",
    user_rejected: bool = False,
) -> CommitmentInput:
    return CommitmentInput(
        commitment_id=commitment_id,
        direction=direction,
        currency=currency,
        category=category,
        tier=tier,
        confidence=confidence,
        anchor_day=anchor_day,
        period_days=period_days,
        amount_median=amount_median,
        amount_most_recent=amount_most_recent,
        occurrences=occurrences,
        last_seen=last_seen,
        description=description,
        user_rejected=user_rejected,
    )


def make_fact(
    fact_id: str,
    *,
    direction: FactDirection,
    confirmation: FactConfirmation,
    kind: FactKind,
    target_event_id: str,
    amount: Decimal | None = None,
    recorded_date: date = AS_OF,
    source: str = "",
    effective_date: date | None = None,
) -> EvidenceFact:
    return EvidenceFact(
        fact_id=fact_id,
        direction=direction,
        confirmation=confirmation,
        kind=kind,
        target_event_id=target_event_id,
        target_commitment_id=None,
        amount=amount,
        effective_date=effective_date,
        recorded_date=recorded_date,
        source=source,
    )


def make_installment_option(
    option_id: str, schedule: tuple[tuple[date, Decimal], ...], currency: str = "INR"
) -> PaymentOption:
    entries = tuple(
        PaymentOptionSchedule(due_date=d, amount=a, currency=currency) for d, a in schedule
    )
    total = sum((a for _d, a in schedule), Decimal(0))
    return PaymentOption(
        option_id=option_id,
        method=CandidateType.INSTALLMENTS,
        schedule=entries,
        stated_total=total,
        stated_total_currency=currency,
    )


def make_fx_rate(base: str, quote: str, on_date: date, rate: Decimal) -> FxRateEntry:
    return FxRateEntry(base_currency=base, quote_currency=quote, rate_date=on_date, rate=rate)
