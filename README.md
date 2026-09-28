# FinGuard

## AI Financial Affordability Agent

> **Core question:** Buy or Wait?

FinGuard is a safety-first financial decision engine that evaluates whether a user can safely afford a requested purchase based on their current financial state, upcoming cash flows, recurring expenses, payment options, settlement timing, and minimum-balance constraints.

The project combines deterministic financial reasoning with structured event processing, evidence handling, forecasting, and validation to produce an explainable affordability decision.

---

## What FinGuard Does

Given a financial profile, financial events, a purchase request, available payment options, and supporting evidence, FinGuard determines:

- how much is safely available to spend
- whether the purchase is affordable now
- whether a payment plan makes it affordable
- whether the user should wait
- whether the purchase should not be recommended
- which payment method is appropriate
- what spending changes, if any, would be required
- when full payment becomes safely possible
- why the decision was made

The engine is designed around **financial safety rather than simple balance checking**.

---

## Decision Outcomes

| Status | Meaning |
|---|---|
| `affordable_now` | The purchase can be safely completed now. |
| `affordable_with_plan` | The purchase is safe with an eligible payment plan. |
| `affordable_later` | The purchase becomes safe at a later date. |
| `not_affordable` | The purchase cannot be safely completed under the available options. |

Supported payment methods include:

- full payment
- partial payment
- installments
- wait
- not recommended

---

## Safety Model

FinGuard does not treat the current account balance as disposable money.

The decision engine considers:

- current available funds
- pending debits
- settled and unsettled transactions
- settlement dates
- recurring expenses
- minimum required balance
- future income
- payment schedules
- currency conversion
- spending reductions
- transaction lifecycle
- conflicting financial events
- payment-method eligibility

Pending credits such as expected bonuses, refunds, commissions, or investment gains are not treated as available cash until they are financially settled.

The engine also evaluates projected balances across the relevant future period rather than checking only today's balance.

---

## Architecture

```text
Financial Profiles
       │
       ├── Financial Events
       ├── Requests
       ├── Payment Options
       ├── Messages
       └── Evidence / Images
              │
              ▼
        Data Ingestion
              │
              ▼
       Event Normalization
              │
              ▼
       Financial State Model
              │
              ├── Lifecycle handling
              ├── Recurrence projection
              ├── Cash-flow processing
              └── Evidence reconciliation
              │
              ▼
       90-Day Cash-Flow Forecast
              │
              ▼
       Decision Engine
              │
              ├── Full payment
              ├── Partial payment
              ├── Installments
              ├── Wait
              └── Not recommended
              │
              ▼
       Deterministic Validation
              │
              ▼
           output.csv
