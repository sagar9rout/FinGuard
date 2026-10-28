"""FinGuard server: a thin, loopback-only HTTP layer over the existing, tested API in ``backend/finguard_api``.

It owns transport concerns only (settings, host and origin guards, safe logging, error shape, engine availability).
It contains no financial logic: every number and decision comes from ``finguard_core`` through the backend handlers.
"""
