"""The G.9 safety predicate and breach-attribution taxonomy (docs/engine/
semantics.md Section 9, final locked correction).

The only safety predicate is ``plan_low(d) >= reserve`` for every day
from first payment through ``effective_end``. A baseline breach is
never itself a rejection reason. Every unsafe day gets exactly one of
``causes`` / ``worsens`` / ``unrelated``; ``neither`` only ever
describes a safe day.
"""

from __future__ import annotations

from datetime import date

import pytest

from finguard_core.contracts import BreachAttribution
from finguard_core.safety import classify_breach_day


class TestClassifyBreachDay:
    DAY = date(2026, 1, 5)

    def test_causes_when_baseline_safe_and_plan_unsafe(self):
        result = classify_breach_day(self.DAY, baseline_low=5000, plan_low=1000, reserve=3000)
        assert result is BreachAttribution.CAUSES

    def test_worsens_when_baseline_already_unsafe_and_plan_lower_still(self):
        result = classify_breach_day(self.DAY, baseline_low=2000, plan_low=1000, reserve=3000)
        assert result is BreachAttribution.WORSENS

    def test_unrelated_when_baseline_already_unsafe_and_plan_does_not_worsen_it(self):
        result = classify_breach_day(self.DAY, baseline_low=1000, plan_low=1000, reserve=3000)
        assert result is BreachAttribution.UNRELATED

    def test_unrelated_when_baseline_already_unsafe_and_plan_is_actually_higher(self):
        # The candidate's own schedule can coincide with a credit that
        # makes the day less bad than the baseline, yet still unsafe.
        result = classify_breach_day(self.DAY, baseline_low=1000, plan_low=1500, reserve=3000)
        assert result is BreachAttribution.UNRELATED

    def test_raises_if_called_on_a_safe_day(self):
        with pytest.raises(AssertionError):
            classify_breach_day(self.DAY, baseline_low=5000, plan_low=3000, reserve=3000)

    def test_boundary_plan_low_exactly_at_reserve_is_safe_not_a_breach_day(self):
        # plan_low == reserve satisfies "plan_low >= reserve"; callers
        # must not invoke classify_breach_day for this day at all.
        with pytest.raises(AssertionError):
            classify_breach_day(self.DAY, baseline_low=1000, plan_low=3000, reserve=3000)

    def test_classification_is_exhaustive_and_mutually_exclusive(self):
        # For every unsafe day (plan_low < reserve), sweep a grid of
        # baseline_low values and confirm exactly one of CAUSES/WORSENS/
        # UNRELATED is produced, never NEITHER.
        reserve = 3000
        plan_low = 1000
        for baseline_low in range(-2000, 6000, 250):
            result = classify_breach_day(self.DAY, baseline_low=baseline_low, plan_low=plan_low, reserve=reserve)
            assert result is not BreachAttribution.NEITHER
            assert result in (
                BreachAttribution.CAUSES,
                BreachAttribution.WORSENS,
                BreachAttribution.UNRELATED,
            )
