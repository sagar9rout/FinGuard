"""ASGI entry point: ``uvicorn finguard_api.main:app`` (development only
until authentication exists; see docs/adr/0011-backend-api-boundary.md).
"""

from finguard_api.app import create_app

app = create_app()
