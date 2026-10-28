"""finguard_api — the thin, stateless HTTP boundary around ``finguard_core``.

PR-2 scope (docs/adr/0011-backend-api-boundary.md): request validation,
translation to the core contracts, and faithful, deterministic
serialization of the core's results. It performs NO financial reasoning,
has NO persistence, NO authentication and NO AI. The deterministic core
remains the only source of affordability decisions.
"""

API_VERSION = "v1"
