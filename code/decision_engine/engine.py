#!/usr/bin/env python3

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from financial_engine.event_mapper import map_event


ZERO = Decimal("0")
CENT = Decimal("0.01")


def dec(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def money(value):
    if value is None:
        return ""

    return str(
        value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
    )


def parse_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def normalize_list(value):
    if not value:
        return set()

    value = str(value).strip()

    for sep in ("|", ";", ","):
        if sep in value:
            return {
                x.strip().lower()
                for x in value.split(sep)
                if x.strip()
            }

    return {value.lower()} if value else set()


def conversion(amount, currency, home, rates):
    if amount is None:
        return None

    currency = (currency or home).upper()
    home = home.upper()

    if currency == home:
        return amount

    direct = rates.get((currency, home))

    if direct is not None:
        return amount * direct

    reverse = rates.get((home, currency))

    if reverse is not None and reverse != 0:
        return amount / reverse

    return None


def event_date(event):
    return event.settlement_date or event.event_date


def usable_event(event):
    if event.status in {"cancelled", "failed", "unrealized"}:
        return False

    if event.amount is None or event.amount == ZERO:
        return False

    if event.direction not in {"debit", "credit"}:
        return False

    # Pending credits are explicitly not spendable.
    if event.status == "pending" and event.direction == "credit":
        return False

    return True


def event_is_outflow(event):
    return event.direction == "debit"


def get_event_category(event):
    return (event.category or "").strip().lower()


def get_event_description(event):
    return (event.description or "").strip().lower()


def is_internal_transfer(event):
    text = (
        get_event_description(event)
        + " "
        + get_event_category(event)
    )

    keywords = (
        "internal transfer",
        "transfer between",
        "own account",
        "same account",
        "matching debit",
        "matching credit",
    )

    return any(k in text for k in keywords)


def protected_categories(profile):
    return normalize_list(
        profile.get("expense_categories_to_protect")
    )


def reducible_categories(profile):
    return normalize_list(
        profile.get(
            "expense_categories_user_is_willing_to_reduce"
        )
    )


def stoppable_categories(profile):
    return normalize_list(
        profile.get(
            "expense_categories_user_is_willing_to_stop"
        )
    )


def recurring_flexible_events(events, profile, request_date):
    protected = protected_categories(profile)
    reducible = reducible_categories(profile)
    stoppable = stoppable_categories(profile)

    candidates = []

    for e in events:
        if not usable_event(e):
            continue

        if not event_is_outflow(e):
            continue

        if is_internal_transfer(e):
            continue

        d = event_date(e)

        if d is None or d < request_date:
            continue

        flexibility = (
            e.flexibility or ""
        ).lower()

        category = get_event_category(e)

        if category in protected:
            continue

        if flexibility not in {
            "reducible",
            "stoppable",
            "reducible_or_stoppable",
        }:
            continue

        priority = 0

        if category in stoppable:
            priority = 4
        elif category in reducible:
            priority = 3
        elif flexibility == "stoppable":
            priority = 2
        elif flexibility == "reducible_or_stoppable":
            priority = 1

        amount = dec(e.amount)

        if amount is None or amount <= 0:
            continue

        candidates.append(
            (
                priority,
                amount,
                e,
            )
        )

    candidates.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            x[2].get("event_id", ""),
        )
    )

    return candidates


def projected_balance(
    profile,
    events,
    request_date,
    payment_schedule,
    rates,
    reductions=None,
):
    home = (
        profile.get("home_currency") or ""
    ).upper()

    balance = (
        dec(profile.get("current_available_balance"))
        or ZERO
    )

    minimum = (
        dec(profile.get("minimum_balance_to_keep"))
        or ZERO
    )

    reductions = reductions or {}

    payments = defaultdict(list)

    for item in payment_schedule:
        if len(item) != 3:
            continue

        first, second, third = item

        if isinstance(first, date):
            pay_date = first
            pay_amount = second
            pay_currency = third
        else:
            pay_amount = first
            pay_date = second
            pay_currency = third

        if not isinstance(pay_date, date):
            continue

        payments[pay_date].append(
            (
                pay_amount,
                pay_currency,
            )
        )

    all_dates = set(payments.keys())

    for e in events:
        if not usable_event(e):
            continue

        d = event_date(e)

        if isinstance(d, date) and d >= request_date:
            all_dates.add(d)

    if not all_dates:
        return True, balance, request_date

    end = max(all_dates)

    current = request_date

    while current <= end:

        day_events = [
            e
            for e in events
            if usable_event(e)
            and event_date(e) == current
        ]

        # Debits happen before credits on the same day.
        day_events.sort(
            key=lambda e: (
                0 if event_is_outflow(e) else 1,
                e.event_id,
            )
        )

        for e in day_events:
            amount = dec(e.amount)

            converted = conversion(
                amount,
                e.currency,
                home,
                rates,
            )

            if converted is None:
                continue

            event_id = e.event_id

            if event_id in reductions:
                converted = reductions[event_id]

            if event_is_outflow(e):
                balance -= converted
            else:
                balance += converted

            if balance < minimum:
                return False, balance, current

        for pay_amount, pay_currency in payments.get(
            current,
            [],
        ):
            converted = conversion(
                dec(pay_amount),
                pay_currency or home,
                home,
                rates,
            )

            if converted is None:
                return False, balance, current

            balance -= converted

            if balance < minimum:
                return False, balance, current

        current += timedelta(days=1)

    return True, balance, end


def safe_today_amount(
    profile,
    events,
    request_date,
    rates,
):
    home = (
        profile.get("home_currency") or ""
    ).upper()

    balance = (
        dec(profile.get("current_available_balance"))
        or ZERO
    )

    minimum = (
        dec(profile.get("minimum_balance_to_keep"))
        or ZERO
    )

    available = balance - minimum

    if available <= ZERO:
        return ZERO

    # Same-day debits must be reserved.
    for e in events:
        if not usable_event(e):
            continue

        if event_date(e) != request_date:
            continue

        if not event_is_outflow(e):
            continue

        converted = conversion(
            dec(e.amount),
            e.currency,
            home,
            rates,
        )

        if converted is not None:
            available -= converted

    return max(
        ZERO,
        available,
    )


def format_plan(items):
    formatted = []

    for item in items:
        if len(item) != 3:
            continue

        first, second, _currency = item

        if isinstance(first, date):
            pay_date = first
            amount = second
        else:
            amount = first
            pay_date = second

        if not isinstance(pay_date, date):
            raise TypeError(
                f"Invalid payment date in schedule: {pay_date!r}"
            )

        formatted.append(
            f"{pay_date.isoformat()}:{money(dec(amount) or ZERO)}"
        )

    return "|".join(formatted)


def candidate_full_payment(
    request,
    profile,
    events,
    options,
    request_date,
    desired_date,
    rates,
):
    home = (
        profile.get("home_currency") or ""
    ).upper()

    requested = (
        dec(request.get("requested_amount"))
        or ZERO
    )

    candidates = []

    for option in options:
        method = (
            option.get("payment_method") or ""
        ).strip().lower()

        if method not in {
            "full_payment",
            "installments",
        }:
            continue

        first = parse_date(
            option.get("first_payment_date")
        )

        if first is None:
            continue

        number = int(
            option.get("number_of_payments")
            or 1
        )

        frequency = int(
            option.get("payment_frequency_days")
            or 0
        )

        amount = dec(
            option.get("payment_amount")
        )

        total = dec(
            option.get("total_payable_amount")
        )

        if amount is None:
            continue

        schedule = []

        for i in range(number):
            d = first + timedelta(
                days=i * frequency
            )

            schedule.append(
                (
                    amount,
                    d,
                    option,
                )
            )

        final_date = schedule[-1][1]

        if desired_date and final_date > desired_date:
            continue

        payment_schedule = [
            (
                a,
                d,
                option.get("currency") or home,
            )
            for a, d, _ in schedule
        ]

        safe, _, _ = projected_balance(
            profile,
            events,
            request_date,
            payment_schedule,
            rates,
        )

        if not safe:
            continue

        candidates.append(
            {
                "method": method,
                "option": option,
                "schedule": payment_schedule,
                "first": first,
                "final": final_date,
                "total": (
                    total
                    if total is not None
                    else amount * number
                ),
            }
        )

    candidates.sort(
        key=lambda x: (
            x["final"],
            x["total"],
            0 if x["method"] == "full_payment" else 1,
        )
    )

    return (
        candidates[0]
        if candidates
        else None
    )


def candidate_partial(
    request,
    profile,
    events,
    request_date,
    desired_date,
    rates,
):
    if str(
        request.get("allows_partial_payment", "")
    ).lower() not in {
        "true",
        "1",
        "yes",
    }:
        return None

    requested = (
        dec(request.get("requested_amount"))
        or ZERO
    )

    safe = safe_today_amount(
        profile,
        events,
        request_date,
        rates,
    )

    if safe <= ZERO or safe >= requested:
        return None

    current = request_date + timedelta(days=1)

    while current <= desired_date:
        remaining = requested - safe

        schedule = [
            (
                safe,
                request_date,
                profile.get("home_currency"),
            ),
            (
                remaining,
                current,
                profile.get("home_currency"),
            ),
        ]

        ok, _, _ = projected_balance(
            profile,
            events,
            request_date,
            schedule,
            rates,
        )

        if ok:
            return {
                "method": "partial_payment",
                "safe": safe,
                "date": current,
                "schedule": schedule,
            }

        current += timedelta(days=1)

    return None


def find_wait_date(
    request,
    profile,
    events,
    request_date,
    desired_date,
    rates,
):
    requested = (
        dec(request.get("requested_amount"))
        or ZERO
    )

    home = profile.get("home_currency")

    current = request_date + timedelta(days=1)

    while current <= desired_date:
        schedule = [
            (
                requested,
                current,
                home,
            )
        ]

        ok, _, _ = projected_balance(
            profile,
            events,
            request_date,
            schedule,
            rates,
        )

        if ok:
            return current

        current += timedelta(days=1)

    return None


def spending_change_plan(
    request,
    profile,
    events,
    request_date,
    rates,
):
    candidates = recurring_flexible_events(
        events,
        profile,
        request_date,
    )

    if not candidates:
        return {}, []

    requested = (
        dec(request.get("requested_amount"))
        or ZERO
    )

    safe = safe_today_amount(
        profile,
        events,
        request_date,
        rates,
    )

    needed = requested - safe

    if needed <= ZERO:
        return {}, []

    reductions = {}
    descriptions = []

    home = profile.get("home_currency")

    for priority, amount, e in candidates:
        event_id = e.event_id
        flexibility = (
            e.flexibility or ""
        ).lower()
        category = get_event_category(e)

        converted = conversion(
            amount,
            e.currency,
            home,
            rates,
        )

        if converted is None:
            continue

        if flexibility in {
            "stoppable",
            "reducible_or_stoppable",
        }:
            if (
                category in stoppable_categories(profile)
                or flexibility == "stoppable"
            ):
                reductions[event_id] = ZERO
                descriptions.append(
                    f"stop:{event_id}"
                )
                needed -= converted

        if needed <= ZERO:
            break

        if flexibility in {
            "reducible",
            "reducible_or_stoppable",
        }:
            if (
                category in reducible_categories(profile)
                or flexibility == "reducible"
            ):
                minimum = dec(
                    e.minimum_allowed_amount
                )

                if minimum is None:
                    minimum = ZERO

                minimum_home = conversion(
                    minimum,
                    e.currency,
                    home,
                    rates,
                )

                if minimum_home is None:
                    continue

                reduction = max(
                    ZERO,
                    converted - minimum_home,
                )

                if reduction > ZERO:
                    reductions[event_id] = minimum_home

                    descriptions.append(
                        f"reduce_to:{event_id}:{money(minimum)}"
                    )

                    needed -= reduction

        if len(descriptions) >= 3:
            break

    return reductions, descriptions[:3]


def make_explanation(
    request,
    status,
    method,
    safe,
    changes,
    earliest,
    plan,
):
    requested = request.get(
        "requested_amount",
        "",
    )

    if method == "not_recommended":
        return (
            f"No safe payment option was found for "
            f"the requested amount {requested}. "
            f"The recommendation is to wait rather "
            f"than risk the required minimum balance."
        )

    if method == "full_payment":
        if changes:
            return (
                f"Pay {requested} in full while keeping "
                f"the required minimum balance by applying "
                f"the allowed spending changes: "
                f"{', '.join(changes)}."
            )

        return (
            f"Pay {requested} in full using the available "
            f"cash flow while maintaining the required "
            f"minimum balance."
        )

    if method == "installments":
        return (
            "Use the supplied installment option because "
            "the scheduled payments remain within the safe "
            "balance throughout the forecast period."
        )

    if method == "partial_payment":
        return (
            f"Pay the safe amount of {money(safe)} now "
            f"and pay the remaining amount on "
            f"{earliest.isoformat()} when the forecast "
            f"supports completing the purchase."
        )

    if method == "wait":
        return (
            f"Wait until {earliest.isoformat()}, when the "
            f"requested amount can be paid while preserving "
            f"the required minimum balance."
        )

    return "No recommendation."


def choose_decision(
    request,
    profile,
    events,
    options,
    rates,
):
    events = [
        event if hasattr(event, "event_id") else map_event(event)
        for event in events
    ]

    request_date = parse_date(
        request.get("request_date")
    )

    desired_date = parse_date(
        request.get("desired_completion_date")
    )

    if request_date is None:
        request_date = date.today()

    if desired_date is None:
        desired_date = request_date + timedelta(days=90)

    requested = (
        dec(request.get("requested_amount"))
        or ZERO
    )

    safe_today = safe_today_amount(
        profile,
        events,
        request_date,
        rates,
    )

    # 1. Full payment / supplied installment options.
    direct = candidate_full_payment(
        request,
        profile,
        events,
        options,
        request_date,
        desired_date,
        rates,
    )

    # 2. If direct option works, prefer it.
    if direct is not None:
        method = direct["method"]
        schedule = direct["schedule"]

        if method == "full_payment":
            reductions, changes = spending_change_plan(
                request,
                profile,
                events,
                request_date,
                rates,
            )

            if changes:
                safe_after, _, _ = projected_balance(
                    profile,
                    events,
                    request_date,
                    schedule,
                    rates,
                    reductions,
                )

                if safe_after:
                    return {
                        "request_id": request["request_id"],
                        "amount_safe_to_pay": min(
                            requested,
                            safe_today,
                        ),
                        "affordability_status": (
                            "affordable_with_plan"
                            if changes
                            else "affordable_now"
                        ),
                        "recommended_payment_method": method,
                        "payment_plan": format_plan(
                            schedule
                        ),
                        "earliest_date_for_full_payment": (
                            direct["final"].isoformat()
                        ),
                        "spending_changes_needed": (
                            "|".join(changes)
                        ),
                        "decision_explanation": (
                            make_explanation(
                                request,
                                "affordable_with_plan",
                                method,
                                safe_today,
                                changes,
                                direct["final"],
                                schedule,
                            )
                        ),
                    }

            return {
                "request_id": request["request_id"],
                "amount_safe_to_pay": min(
                    requested,
                    safe_today,
                ),
                "affordability_status": (
                    "affordable_now"
                ),
                "recommended_payment_method": method,
                "payment_plan": format_plan(schedule),
                "earliest_date_for_full_payment": (
                    direct["final"].isoformat()
                ),
                "spending_changes_needed": "",
                "decision_explanation": (
                    make_explanation(
                        request,
                        "affordable_now",
                        method,
                        safe_today,
                        [],
                        direct["final"],
                        schedule,
                    )
                ),
            }

        return {
            "request_id": request["request_id"],
            "amount_safe_to_pay": min(
                requested,
                safe_today,
            ),
            "affordability_status": (
                "affordable_with_plan"
            ),
            "recommended_payment_method": method,
            "payment_plan": format_plan(schedule),
            "earliest_date_for_full_payment": (
                direct["final"].isoformat()
            ),
            "spending_changes_needed": "",
            "decision_explanation": (
                make_explanation(
                    request,
                    "affordable_with_plan",
                    method,
                    safe_today,
                    [],
                    direct["final"],
                    schedule,
                )
            ),
        }

    # 3. Partial payment.
    partial = candidate_partial(
        request,
        profile,
        events,
        request_date,
        desired_date,
        rates,
    )

    if partial is not None:
        return {
            "request_id": request["request_id"],
            "amount_safe_to_pay": partial["safe"],
            "affordability_status": (
                "affordable_with_plan"
            ),
            "recommended_payment_method": (
                "partial_payment"
            ),
            "payment_plan": format_plan(
                partial["schedule"]
            ),
            "earliest_date_for_full_payment": (
                partial["date"].isoformat()
            ),
            "spending_changes_needed": "",
            "decision_explanation": (
                make_explanation(
                    request,
                    "affordable_with_plan",
                    "partial_payment",
                    partial["safe"],
                    [],
                    partial["date"],
                    partial["schedule"],
                )
            ),
        }

    # 4. Wait.
    wait_date = find_wait_date(
        request,
        profile,
        events,
        request_date,
        desired_date,
        rates,
    )

    if wait_date is not None:
        schedule = [
            (
                requested,
                wait_date,
                profile.get("home_currency"),
            )
        ]

        return {
            "request_id": request["request_id"],
            "amount_safe_to_pay": min(
                requested,
                safe_today,
            ),
            "affordability_status": (
                "affordable_later"
            ),
            "recommended_payment_method": "wait",
            "payment_plan": format_plan(schedule),
            "earliest_date_for_full_payment": (
                wait_date.isoformat()
            ),
            "spending_changes_needed": "",
            "decision_explanation": (
                make_explanation(
                    request,
                    "affordable_later",
                    "wait",
                    safe_today,
                    [],
                    wait_date,
                    schedule,
                )
            ),
        }

    # 5. Last resort: not recommended.
    return {
        "request_id": request["request_id"],
        "amount_safe_to_pay": min(
            requested,
            safe_today,
        ),
        "affordability_status": (
            "not_affordable"
        ),
        "recommended_payment_method": (
            "not_recommended"
        ),
        "payment_plan": "",
        "earliest_date_for_full_payment": "",
        "spending_changes_needed": "",
        "decision_explanation": (
            make_explanation(
                request,
                "not_affordable",
                "not_recommended",
                safe_today,
                [],
                None,
                [],
            )
        ),
    }
