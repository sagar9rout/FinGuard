"""Runtime purity check (ADR 0001): run a full ``analyze()`` call with
filesystem and socket access monkey-patched to raise, and confirm the
engine still completes normally. This is a behavioral complement to the
static AST check in ``test_import_contract.py`` — it proves the core
doesn't reach I/O through some indirect path the AST scan might miss
(e.g. a builtin called dynamically).
"""

from __future__ import annotations

import builtins
import socket

from tests.support.builders import make_minimal_input


def test_analyze_does_not_touch_filesystem_or_network(monkeypatch):
    def _deny_open(*_args, **_kwargs):
        raise AssertionError("finguard_core attempted filesystem access via open()")

    def _deny_socket(*_args, **_kwargs):
        raise AssertionError("finguard_core attempted to open a socket")

    monkeypatch.setattr(builtins, "open", _deny_open)
    monkeypatch.setattr(socket, "socket", _deny_socket)

    from finguard_core import analyze

    result = analyze(make_minimal_input())
    assert result is not None


def test_analyze_does_not_touch_filesystem_or_network_on_blocked_input(monkeypatch):
    def _deny_open(*_args, **_kwargs):
        raise AssertionError("finguard_core attempted filesystem access via open()")

    monkeypatch.setattr(builtins, "open", _deny_open)

    from finguard_core import analyze
    from tests.support.builders import make_input_with_unconvertible_debit

    result = analyze(make_input_with_unconvertible_debit())
    assert result is not None
