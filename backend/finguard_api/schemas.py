"""Request schemas: the explicit, versioned wire contract of ``/v1``.

These pydantic models are deliberately separate from the core's
dataclasses so the HTTP contract can evolve (and be versioned) without
touching the core, and so strictness is enforced at the boundary:

- unknown fields are rejected (never silently ignored);
- money is a JSON string or integer, NEVER a float, and must be finite;
- dates are ISO-8601 strings; enums are their string values.

A parity test guarantees these models cover every field of the core's
input contracts, so a core change cannot silently drift from the API.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict

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
from finguard_core.currency import Currency, default_currency_registry


def _money(value: Any) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("money_must_be_string_or_integer")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, str):
        try:
            number = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError("money_not_a_number") from exc
    else:
        raise ValueError("money_must_be_string_or_integer")
    if not number.is_finite():
        raise ValueError("money_not_finite")
    return number


Money = Annotated[Decimal, BeforeValidator(_money)]


class _Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EventIn(_Wire):
    event_id: str
    event_date: date
    amount: Money | None
    currency: str
    direction: EventDirection
    status: EventStatus
    category: str
    linked_event_id: str | None = None
    description: str = ""
    is_stoppable: bool = False
    is_reducible: bool = False
    minimum_allowed_amount: Money | None = None
    recurrence_group_id: str | None = None


class CommitmentIn(_Wire):
    commitment_id: str
    direction: EventDirection
    currency: str
    category: str
    tier: CommitmentTier
    confidence: Money
    anchor_day: int
    period_days: int
    amount_median: Money
    amount_most_recent: Money
    occurrences: int
    last_seen: date
    description: str = ""
    user_rejected: bool = False


class EvidenceFactIn(_Wire):
    fact_id: str
    direction: FactDirection
    confirmation: FactConfirmation
    kind: FactKind
    target_event_id: str | None = None
    target_commitment_id: str | None = None
    amount: Money | None = None
    currency: str | None = None
    effective_date: date | None = None
    recorded_date: date = date.min
    source: str = ""


class ScheduleStepIn(_Wire):
    due_date: date
    amount: Money
    currency: str


class PaymentOptionIn(_Wire):
    option_id: str
    method: CandidateType
    schedule: tuple[ScheduleStepIn, ...]
    stated_total: Money
    stated_total_currency: str


class PurchaseIn(_Wire):
    amount: Money
    currency: str
    desired_completion_date: date | None = None
    allows_partial_payment: bool


class ProfileIn(_Wire):
    home_currency: str
    current_available_balance: Money
    minimum_balance_to_keep: Money
    balance_as_of: date | None = None


class CategoryMinimumIn(_Wire):
    category: str
    minimum: Money


class PreferencesIn(_Wire):
    accepted_methods: tuple[CandidateType, ...]
    max_installment_term_days: int | None = None
    stoppable_categories: tuple[str, ...] = ()
    reducible_categories: tuple[str, ...] = ()
    protected_categories: tuple[str, ...] = ()
    category_min_allowed: tuple[CategoryMinimumIn, ...] = ()
    financial_priorities: tuple[str, ...] = ()
    variable_spend_categories: tuple[str, ...] = ()


class FxRateIn(_Wire):
    base_currency: str
    quote_currency: str
    rate_date: date
    rate: Money


class EngineConfigIn(_Wire):
    horizon_days: int | None = None
    max_window_days: int | None = None
    fx_prior_window_days: int | None = None
    fx_pivot_currencies: tuple[str, ...] | None = None
    fx_pessimistic_window_days: int | None = None
    commitment_overlap_day_tolerance: int | None = None
    commitment_overlap_amount_tolerance: Money | None = None
    variable_spend_lookback_days: int | None = None
    variable_spend_min_weeks_for_percentile: int | None = None
    variable_spend_min_history_days: int | None = None
    balance_stale_after_days: int | None = None
    max_spending_change_actions: int | None = None


class CurrencyIn(_Wire):
    code: str
    exponent: int


class AnalysisRequest(_Wire):
    as_of: date
    profile: ProfileIn
    purchase: PurchaseIn
    preferences: PreferencesIn
    events: tuple[EventIn, ...] = ()
    commitments: tuple[CommitmentIn, ...] = ()
    evidence_facts: tuple[EvidenceFactIn, ...] = ()
    payment_options: tuple[PaymentOptionIn, ...] = ()
    fx_rates: tuple[FxRateIn, ...] = ()
    config: EngineConfigIn | None = None
    currencies: tuple[CurrencyIn, ...] | None = None

    def to_core(self) -> AnalysisInput:
        """Pure, lossless translation to the core contract. Fields the
        caller omitted take the core's own documented defaults.
        """

        defaults = EngineConfig()
        overrides = {} if self.config is None else self.config.model_dump(exclude_none=True)
        config = EngineConfig(**{**_config_kwargs(defaults), **overrides})
        registry = (
            default_currency_registry()
            if self.currencies is None
            else {c.code: Currency(code=c.code, exponent=c.exponent) for c in self.currencies}
        )
        p = self.preferences
        return AnalysisInput(
            as_of=self.as_of,
            profile=FinancialProfile(**self.profile.model_dump()),
            events=tuple(FinancialEventInput(**e.model_dump()) for e in self.events),
            commitments=tuple(CommitmentInput(**c.model_dump()) for c in self.commitments),
            evidence_facts=tuple(EvidenceFact(**f.model_dump()) for f in self.evidence_facts),
            purchase=PurchaseRequest(**self.purchase.model_dump()),
            payment_options=tuple(
                PaymentOption(
                    option_id=o.option_id,
                    method=o.method,
                    schedule=tuple(PaymentOptionSchedule(**s.model_dump()) for s in o.schedule),
                    stated_total=o.stated_total,
                    stated_total_currency=o.stated_total_currency,
                )
                for o in self.payment_options
            ),
            preferences=UserPreferences(
                accepted_methods=p.accepted_methods,
                max_installment_term_days=p.max_installment_term_days,
                stoppable_categories=p.stoppable_categories,
                reducible_categories=p.reducible_categories,
                protected_categories=p.protected_categories,
                category_min_allowed=tuple((m.category, m.minimum) for m in p.category_min_allowed),
                financial_priorities=p.financial_priorities,
                variable_spend_categories=p.variable_spend_categories,
            ),
            fx_rates=tuple(FxRateEntry(**r.model_dump()) for r in self.fx_rates),
            config=config,
            currency_registry=registry,
        )


def _config_kwargs(config: EngineConfig) -> dict[str, Any]:
    return {name: getattr(config, name) for name in EngineConfig.__dataclass_fields__}
