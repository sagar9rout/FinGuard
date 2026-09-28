# FinGuard — Claude Engineering Guide

## Project identity

FinGuard is an AI-assisted financial affordability decision system.

Its core purpose is to answer:

> Can this purchase be afforded safely, or should the user wait?

The project is a standalone portfolio product. Do not describe it as a
HackerRank project, hackathon submission, internship artifact, or challenge
solution.

## Engineering principles

- Preserve the deterministic financial decision engine as the source of truth.
- Do not replace financial calculations with LLM-generated reasoning.
- Keep financial calculations explicit, testable, and explainable.
- Treat AI as an interface/orchestration layer around the deterministic engine.
- Do not invent financial data, transactions, balances, or evidence.
- Preserve existing behaviour unless a change is explicitly required.
- Prefer small, testable modules over large rewrites.
- Add tests for meaningful behavioural changes.
- Never commit secrets, API keys, credentials, tokens, or private user data.

## Current architecture

The main production components are:

- `code/financial_engine/` — financial modelling and cash-flow simulation
- `code/decision_engine/` — affordability and purchase decision logic
- `code/evidence/` — evidence extraction, OCR, and reconciliation
- `code/evaluation/` — validation and evaluation utilities
- `code/tests/` — automated tests
- `code/main.py` — production pipeline entry point

## Verification

Before considering a meaningful change complete, run:

```bash
python3 code/main.py
python3 code/evaluation/main.py
pytest -q code/tests
