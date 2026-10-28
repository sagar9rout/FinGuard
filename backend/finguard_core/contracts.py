"""The engine's only public data contracts (docs/engine/semantics.md;
ADR 0001).

Every type here is immutable (``frozen=True``) and uses tuples rather
than lists so that an ``AnalysisInput``/``AnalysisResult`` value is
hashable-by-content and safe to pass across the canonical-serialization
boundary without aliasing surprises. Collections whose order is not
semantically meaningful (events, commitments, evidence facts, payment
options, fx rates) are treated as sets by the canonical layer — callers
may supply them in any order and get the same result and the same input
hash (docs/adr/0001-core-purity-and-contracts.md).

No reference to the wall clock, filesystem, network, or a database
appears anywhere in this module, and none ever may (ADR 0001).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from finguard_core.currency import Currency, default_currency_registry


class EventDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class EventStatus(StrEnum):
    SETTLED = "settled"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    UNREALIZED = "unrealized"
    NON_CASH = "non_cash"


class CommitmentTier(StrEnum):
    USER_DECLARED = "user_declared"
    CONFIRMED = "confirmed"
    DETECTED = "detected"


class FactDirection(StrEnum):
    INCREASING = "increasing"
    REDUCING = "reducing"


class FactConfirmation(StrEnum):
    CONFIRMED = "confirmed"
    PROPOSED = "proposed"


class FactKind(StrEnum):
    """Phase-1 supported fact kinds (ADR 0010). ``EXCLUSION`` is an
    explicit cancellation, ``SETTLEMENT`` an explicit settlement,
    ``AMOUNT_CHANGE`` / ``DATE_CHANGE`` explicit amendments, and
    ``INCLUSION`` a reinstatement of a cancelled/failed obligation.
    """

    AMOUNT_CHANGE = "amount_change"
    DATE_CHANGE = "date_change"
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    SETTLEMENT = "settlement"


class CandidateType(StrEnum):
    FULL_PAYMENT = "full_payment"
    INSTALLMENTS = "installments"
    PARTIAL = "partial"
    WAIT = "wait"
    FULL_PAYMENT_WITH_SPENDING_CHANGES = "full_payment_with_spending_changes"


class SpendingChangeAction(StrEnum):
    STOP = "stop"
    REDUCE = "reduce"


class AffordabilityStatus(StrEnum):
    AFFORDABLE_NOW = "affordable_now"
    AFFORDABLE_WITH_PLAN = "affordable_with_plan"
    AFFORDABLE_LATER = "affordable_later"
    NOT_AFFORDABLE = "not_affordable"


class BreachAttribution(StrEnum):
    """The G.9 breach-attribution taxonomy (docs/engine/semantics.md
    Section 9, final locked correction). Exactly one of these applies to
    every day in a candidate's evaluated range; ``NEITHER`` applies only
    to safe days and never explains why a candidate failed.
    """

    CAUSES = "causes"
    WORSENS = "worsens"
    UNRELATED = "unrelated"
    NEITHER = "neither"


class DataQualityLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class MissingInfoImpact(StrEnum):
    INFORMATIONAL = "informational"
    COULD_CHANGE_DECISION = "could_change_decision"


# --------------------------------------------------------------------------
# Input contracts
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinancialEventInput:
    event_id: str
    event_date: date
    amount: Decimal | None
    currency: str
    direction: EventDirection
    status: EventStatus
    category: str
    linked_event_id: str | None = None
    description: str = ""
    is_stoppable: bool = False
    is_reducible: bool = False
    minimum_allowed_amount: Decimal | None = None
    # Events that share a non-None ``recurrence_group_id`` are explicitly
    # supplied occurrences of one recurring obligation and form ONE
    # spending-change target; its remaining occurrences are exactly the
    # group's counted events on/after the evaluation date. The engine
    # never synthesizes occurrence dates (ADR 0010).
    recurrence_group_id: str | None = None


@dataclass(frozen=True, slots=True)
class CommitmentInput:
    """A recurring obligation or income stream, already detected and
    typed upstream (detection/NLP is out of scope for this pure core —
    see docs/engine/semantics.md Section 6 and ADR 0004's note that
    Phase 1 consumes only pre-typed facts/commitments).
    """

    commitment_id: str
    direction: EventDirection
    currency: str
    category: str
    tier: CommitmentTier
    confidence: Decimal
    anchor_day: int
    period_days: int
    amount_median: Decimal
    amount_most_recent: Decimal
    occurrences: int
    last_seen: date
    description: str = ""
    user_rejected: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceFact:
    """A typed, pre-extracted evidence fact (docs/engine/semantics.md
    Section 12; ADR 0004). The engine never parses free text itself.
    """

    fact_id: str
    direction: FactDirection
    confirmation: FactConfirmation
    kind: FactKind
    target_event_id: str | None
    target_commitment_id: str | None = None  # unsupported in Phase 1 (ADR 0010)
    amount: Decimal | None = None
    currency: str | None = None
    effective_date: date | None = None
    recorded_date: date = field(default=date.min)
    source: str = ""


@dataclass(frozen=True, slots=True)
class PaymentOptionSchedule:
    due_date: date
    amount: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class PaymentOption:
    option_id: str
    method: CandidateType
    schedule: tuple[PaymentOptionSchedule, ...]
    stated_total: Decimal
    stated_total_currency: str


@dataclass(frozen=True, slots=True)
class PurchaseRequest:
    amount: Decimal
    currency: str
    desired_completion_date: date | None
    allows_partial_payment: bool


@dataclass(frozen=True, slots=True)
class FinancialProfile:
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    balance_as_of: date | None = None


@dataclass(frozen=True, slots=True)
class UserPreferences:
    accepted_methods: tuple[CandidateType, ...]
    max_installment_term_days: int | None
    stoppable_categories: tuple[str, ...]
    reducible_categories: tuple[str, ...]
    protected_categories: tuple[str, ...]
    category_min_allowed: tuple[tuple[str, Decimal], ...] = ()
    financial_priorities: tuple[str, ...] = ()
    variable_spend_categories: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FxRateEntry:
    base_currency: str
    quote_currency: str
    rate_date: date
    rate: Decimal  # units of quote_currency per 1 unit of base_currency


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Tunable, documented parameters (docs/engine/semantics.md Sections
    5, 7, 8; ADR 0003). Defaults match the locked specification;
    provisional values are marked as such in the referenced ADRs.
    """

    horizon_days: int = 90
    max_window_days: int = 180
    fx_prior_window_days: int = 45
    fx_pivot_currencies: tuple[str, ...] = ("USD", "EUR")
    fx_pessimistic_window_days: int = 180  # provisional, ADR 0003
    commitment_overlap_day_tolerance: int = 3
    commitment_overlap_amount_tolerance: Decimal = Decimal("0.10")
    variable_spend_lookback_days: int = 56
    variable_spend_min_weeks_for_percentile: int = 4
    variable_spend_min_history_days: int = 14
    balance_stale_after_days: int = 7
    max_spending_change_actions: int = 3


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    as_of: date
    profile: FinancialProfile
    events: tuple[FinancialEventInput, ...]
    commitments: tuple[CommitmentInput, ...]
    evidence_facts: tuple[EvidenceFact, ...]
    purchase: PurchaseRequest
    payment_options: tuple[PaymentOption, ...]
    preferences: UserPreferences
    fx_rates: tuple[FxRateEntry, ...]
    config: EngineConfig = field(default_factory=EngineConfig)
    currency_registry: Mapping[str, Currency] = field(
        default_factory=default_currency_registry
    )


# --------------------------------------------------------------------------
# Output contracts
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReasonEntry:
    code: str
    severity: str
    params: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class CertifiableWindow:
    start: date
    horizon_end: date
    deadline: date | None
    effective_end: date
    truncated: bool
    max_window_days: int


@dataclass(frozen=True, slots=True)
class LowestPoint:
    day: date
    balance: Decimal


@dataclass(frozen=True, slots=True)
class BaselineSummary:
    """Summary of the no-purchase baseline against the reserve. Purely
    contextual; never itself a rejection reason (G.9).
    """

    below_reserve: bool
    first_breach_date: date | None
    last_breach_date: date | None
    days_below: int
    lowest: LowestPoint | None
    max_shortfall: Decimal


class CommitmentStatus(StrEnum):
    APPLIED = "applied"
    SUPPRESSED_OVERLAP = "suppressed_overlap"
    SUPPRESSED_BY_USER_REJECTION = "suppressed_by_user_rejection"
    REJECTED = "rejected"
    LAPSED = "lapsed"
    UNCONFIRMED_INCOME_EXCLUDED = "unconfirmed_income_excluded"


@dataclass(frozen=True, slots=True)
class ConsideredCommitment:
    commitment_id: str
    direction: EventDirection
    category: str
    tier: CommitmentTier
    status: CommitmentStatus
    suppressed_by: str | None
    amount_per_occurrence: Decimal
    currency: str
    occurrences_projected: int
    occurrences_suppressed_by_explicit_event: int


@dataclass(frozen=True, slots=True)
class FxUsageEntry:
    base_currency: str
    quote_currency: str
    stage: str
    direction: str
    count: int
    worst_age_days: int | None
    worst_rate: Decimal | None
    inverse_used_count: int
    window_days: int | None
    candidates_considered: int | None


@dataclass(frozen=True, slots=True)
class BreachDay:
    day: date
    attribution: BreachAttribution
    baseline_low: Decimal
    plan_low: Decimal
    reserve: Decimal


@dataclass(frozen=True, slots=True)
class SpendingChangeEntry:
    target_id: str
    action: SpendingChangeAction
    category: str
    amount_changed: Decimal  # total actually changed, home currency
    window_total_saving: Decimal  # home currency; equals amount_changed
    occurrences: int = 1


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate_type: CandidateType
    option_id: str | None
    safe: bool
    eligible: bool
    rejection_code: str | None
    first_payment_date: date | None
    final_payment_date: date | None
    total_cost: Decimal
    schedule: tuple[PaymentOptionSchedule, ...]
    spending_changes: tuple[SpendingChangeEntry, ...]
    breach_days: tuple[BreachDay, ...]
    reasons: tuple[ReasonEntry, ...]


@dataclass(frozen=True, slots=True)
class MissingInfoEntry:
    field_name: str
    impact: MissingInfoImpact
    code: str = ""  # a ReasonCode value; the engine emits codes, never prose
    subject_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VariableSpendInfo:
    """The actual parameters ``weekly_p75_nearest_rank_v1`` ran with
    (docs/engine/semantics.md Section 5 step 5), so nothing is applied
    silently. ``daily_amount`` is None when no estimate was produced.
    """

    method: str
    estimated: bool
    categories: tuple[str, ...]
    lookback_days: int
    history_days: int
    complete_weeks_used: int
    zero_weeks: int
    weekly_totals: tuple[Decimal, ...]
    statistic: str  # "p75_nearest_rank", "max_weekly_total" or "none"
    weekly_value: Decimal | None
    daily_amount: Decimal | None
    currency: str | None


ENGINE_VERSION = "1.0.0-pr1.1"


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    status: AffordabilityStatus
    chosen: CandidateResult | None
    candidates: tuple[CandidateResult, ...]
    reasons: tuple[ReasonEntry, ...]
    assumptions: tuple[ReasonEntry, ...]
    issues: tuple[ReasonEntry, ...]
    data_quality: DataQualityLevel
    missing_information: tuple[MissingInfoEntry, ...]
    certifiable_window: CertifiableWindow
    earliest_full_payment_date: date | None
    input_hash: str
    baseline_summary: BaselineSummary
    considered_commitments: tuple[ConsideredCommitment, ...]
    engine_config_echo: EngineConfig
    fx_usage: tuple[FxUsageEntry, ...]
    variable_spend: VariableSpendInfo
    engine_version: str = ENGINE_VERSION
    # False only when certification is blocked (an unconvertible debit,
    # docs/engine/semantics.md Section 7 stage 5). ``status`` is then
    # NOT_AFFORDABLE by convention only, because the four-value status
    # mapping has no "not certified" member; consumers must check this
    # flag before presenting ``status`` as a verdict.
    certified: bool = True


@dataclass(frozen=True, slots=True)
class LedgerDay:
    day: date
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class ForecastResult:
    certifiable_window: CertifiableWindow
    baseline_series: tuple[LedgerDay, ...]
    baseline_summary: BaselineSummary
    considered_commitments: tuple[ConsideredCommitment, ...]
    engine_config_echo: EngineConfig
    fx_usage: tuple[FxUsageEntry, ...]
    variable_spend: VariableSpendInfo
    assumptions: tuple[ReasonEntry, ...]
    issues: tuple[ReasonEntry, ...]
    input_hash: str
