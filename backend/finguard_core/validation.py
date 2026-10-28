"""Hard structural validation of an ``AnalysisInput`` (ADR 0001, ADR 0010).

Only *structurally impossible or ambiguous* contract states are rejected
here. Every numeric bound used is an arithmetic-safety bound, documented
in ADR 0010, not a business rule: amounts are bounded so that the
default 28-digit ``Decimal`` context can never silently round, and the
scale is bounded so equal values have bounded canonical text.

Violations are machine-readable strings of the form ``<rule>:<subject>``;
the engine never emits prose.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from finguard_core.contracts import (
    AnalysisInput,
    CandidateType,
    EventDirection,
    FactKind,
)

MAX_ABS_AMOUNT = Decimal(10) ** 15
MAX_SCALE = 10


class InputValidationError(ValueError):
    """Raised when an input is structurally invalid. ``violations`` is a
    sorted tuple of ``rule:subject`` strings (deterministic).
    """

    def __init__(self, violations: Iterable[str]) -> None:
        self.violations: tuple[str, ...] = tuple(sorted(set(violations)))
        super().__init__("invalid AnalysisInput: " + "; ".join(self.violations))


def _bad_decimal(value: Decimal) -> bool:
    if not value.is_finite():
        return True
    if abs(value) >= MAX_ABS_AMOUNT:
        return True
    exponent = value.as_tuple().exponent
    return isinstance(exponent, int) and -exponent > MAX_SCALE


def _check_amount(
    out: list[str],
    rule: str,
    subject: str,
    value: Decimal | None,
    *,
    allow_negative: bool = False,
    positive: bool = False,
) -> None:
    if value is None:
        return
    if _bad_decimal(value):
        out.append(f"{rule}_invalid:{subject}")
        return
    if positive and value <= 0:
        out.append(f"{rule}_not_positive:{subject}")
    elif not allow_negative and value < 0:
        out.append(f"{rule}_negative:{subject}")


def _duplicates(out: list[str], rule: str, ids: list[str]) -> None:
    for item, count in Counter(ids).items():
        if not item:
            out.append(f"{rule}_empty:")
        elif count > 1:
            out.append(f"{rule}_duplicate:{item}")


def collect_violations(inp: AnalysisInput) -> tuple[str, ...]:
    out: list[str] = []
    registry = inp.currency_registry
    config = inp.config

    # --- identifiers -------------------------------------------------------
    _duplicates(out, "event_id", [e.event_id for e in inp.events])
    _duplicates(out, "commitment_id", [c.commitment_id for c in inp.commitments])
    _duplicates(out, "fact_id", [f.fact_id for f in inp.evidence_facts])
    _duplicates(out, "option_id", [o.option_id for o in inp.payment_options])

    # --- currencies --------------------------------------------------------
    codes: set[str] = {inp.purchase.currency, inp.profile.home_currency}
    codes.update(e.currency for e in inp.events)
    codes.update(c.currency for c in inp.commitments)
    codes.update(r.base_currency for r in inp.fx_rates)
    codes.update(r.quote_currency for r in inp.fx_rates)
    codes.update(p for p in config.fx_pivot_currencies)
    for option in inp.payment_options:
        codes.update(s.currency for s in option.schedule)
        codes.add(option.stated_total_currency)
    for fact in inp.evidence_facts:
        if fact.currency is not None:
            codes.add(fact.currency)
    for code in sorted(codes):
        if code not in registry:
            out.append(f"currency_unregistered:{code}")
    for key, currency in registry.items():
        if key != currency.code:
            out.append(f"currency_registry_key_mismatch:{key}")

    # --- profile / purchase / as_of ---------------------------------------
    _check_amount(out, "balance", "profile", inp.profile.current_available_balance, allow_negative=True)
    _check_amount(out, "minimum_balance", "profile", inp.profile.minimum_balance_to_keep)
    if inp.profile.balance_as_of is not None and inp.profile.balance_as_of > inp.as_of:
        out.append("balance_as_of_after_as_of:profile")
    _check_amount(out, "purchase_amount", "purchase", inp.purchase.amount, positive=True)

    # --- events -------------------------------------------------------------
    event_ids = {e.event_id for e in inp.events}
    for event in inp.events:
        _check_amount(out, "event_amount", event.event_id, event.amount)
        _check_amount(out, "event_minimum_allowed", event.event_id, event.minimum_allowed_amount)
        if (
            event.minimum_allowed_amount is not None
            and event.amount is not None
            and event.minimum_allowed_amount > event.amount
        ):
            out.append(f"event_minimum_allowed_exceeds_amount:{event.event_id}")
        if event.minimum_allowed_amount is not None and not event.is_reducible:
            out.append(f"event_minimum_allowed_without_reducible:{event.event_id}")
        if (event.is_stoppable or event.is_reducible) and event.direction is not EventDirection.DEBIT:
            out.append(f"event_flexible_credit:{event.event_id}")

    groups: dict[str, list[object]] = {}
    for event in inp.events:
        if event.recurrence_group_id is not None:
            groups.setdefault(event.recurrence_group_id, []).append(
                (event.category, event.direction, event.is_stoppable, event.is_reducible)
            )
    for group_id, shapes in groups.items():
        if len(set(map(str, shapes))) > 1:
            out.append(f"recurrence_group_inconsistent:{group_id}")

    # --- commitments --------------------------------------------------------
    for c in inp.commitments:
        _check_amount(out, "commitment_amount", c.commitment_id, c.amount_median)
        _check_amount(out, "commitment_amount", c.commitment_id, c.amount_most_recent)
        if not (Decimal(0) <= c.confidence <= Decimal(1)):
            out.append(f"commitment_confidence_out_of_range:{c.commitment_id}")
        if not 1 <= c.anchor_day <= 31:
            out.append(f"commitment_anchor_day_invalid:{c.commitment_id}")
        if c.period_days < 1:
            out.append(f"commitment_period_invalid:{c.commitment_id}")
        if c.occurrences < 0:
            out.append(f"commitment_occurrences_negative:{c.commitment_id}")

    # --- evidence facts -----------------------------------------------------
    for f in inp.evidence_facts:
        if f.target_commitment_id is not None:
            out.append(f"fact_commitment_target_unsupported:{f.fact_id}")
        if f.target_event_id is None:
            out.append(f"fact_missing_target:{f.fact_id}")
        elif f.target_event_id not in event_ids:
            out.append(f"fact_unknown_target:{f.fact_id}")
        _check_amount(out, "fact_amount", f.fact_id, f.amount)
        if f.kind is FactKind.AMOUNT_CHANGE and f.amount is None:
            out.append(f"fact_amount_change_without_amount:{f.fact_id}")
        if f.kind is FactKind.DATE_CHANGE and f.effective_date is None:
            out.append(f"fact_date_change_without_date:{f.fact_id}")
        target = next((e for e in inp.events if e.event_id == f.target_event_id), None)
        if target is not None and f.currency is not None and f.currency != target.currency:
            out.append(f"fact_currency_mismatch:{f.fact_id}")

    # --- FX rates -----------------------------------------------------------
    seen_rates: dict[tuple[str, str, date], Decimal] = {}
    for r in inp.fx_rates:
        subject = f"{r.base_currency}/{r.quote_currency}@{r.rate_date.isoformat()}"
        if r.base_currency == r.quote_currency:
            out.append(f"fx_rate_same_currency:{subject}")
        if not r.rate.is_finite() or r.rate <= 0 or _bad_decimal(r.rate):
            out.append(f"fx_rate_invalid:{subject}")
            continue
        rate_key = (r.base_currency, r.quote_currency, r.rate_date)
        previous = seen_rates.get(rate_key)
        if previous is not None and previous != r.rate:
            out.append(f"fx_rate_conflict:{subject}")
        seen_rates[rate_key] = r.rate

    # --- payment options ----------------------------------------------------
    max_term = inp.preferences.max_installment_term_days
    if max_term is not None and max_term < 0:
        out.append("installment_term_negative:preferences")
    for option in inp.payment_options:
        oid = option.option_id
        if option.method is not CandidateType.INSTALLMENTS:
            out.append(f"option_method_unsupported:{oid}")
        if not option.schedule:
            out.append(f"option_schedule_empty:{oid}")
            continue
        _check_amount(out, "option_stated_total", oid, option.stated_total)
        currencies = {s.currency for s in option.schedule}
        if len(currencies) > 1:
            out.append(f"option_mixed_currency:{oid}")
        previous_date = None
        for step in option.schedule:
            _check_amount(out, "option_installment", oid, step.amount, positive=True)
            if previous_date is not None and step.due_date <= previous_date:
                out.append(f"option_dates_not_strictly_increasing:{oid}")
            previous_date = step.due_date

    # --- preferences --------------------------------------------------------
    for category, minimum in inp.preferences.category_min_allowed:
        _check_amount(out, "category_minimum", category, minimum)
    min_categories = [c for c, _ in inp.preferences.category_min_allowed]
    for category, count in Counter(min_categories).items():
        if count > 1:
            out.append(f"category_minimum_duplicate:{category}")

    # --- config -------------------------------------------------------------
    positive_ints = {
        "horizon_days": config.horizon_days,
        "max_window_days": config.max_window_days,
        "variable_spend_lookback_days": config.variable_spend_lookback_days,
        "variable_spend_min_weeks_for_percentile": config.variable_spend_min_weeks_for_percentile,
        "max_spending_change_actions": config.max_spending_change_actions,
    }
    for name, value in positive_ints.items():
        if value < 1:
            out.append(f"config_not_positive:{name}")
    non_negative = {
        "fx_prior_window_days": config.fx_prior_window_days,
        "fx_pessimistic_window_days": config.fx_pessimistic_window_days,
        "commitment_overlap_day_tolerance": config.commitment_overlap_day_tolerance,
        "variable_spend_min_history_days": config.variable_spend_min_history_days,
        "balance_stale_after_days": config.balance_stale_after_days,
    }
    for name, nn_value in non_negative.items():
        if nn_value < 0:
            out.append(f"config_negative:{name}")
    if not (Decimal(0) <= config.commitment_overlap_amount_tolerance <= Decimal(1)):
        out.append("config_out_of_range:commitment_overlap_amount_tolerance")
    return tuple(sorted(set(out)))


def validate_or_raise(inp: AnalysisInput) -> None:
    violations = collect_violations(inp)
    if violations:
        raise InputValidationError(violations)
