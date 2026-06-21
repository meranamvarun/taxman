"""Tests for tax_calculator — slab tax, rebate, surcharge, cess, regime comparison."""

from __future__ import annotations

import math

import pytest

from scripts.calculators.tax_calculator import (
    _slab_tax,
    _rebate_87a,
    _surcharge,
    compute_regime,
    compare_regimes,
)


# ---------------------------------------------------------------------------
# _slab_tax
# ---------------------------------------------------------------------------

class TestSlabTax:
    @pytest.fixture
    def new_regime_slabs(self, ay2526_rules):
        return ay2526_rules["new_regime"]["slabs"]

    @pytest.fixture
    def old_regime_slabs(self, ay2526_rules):
        return ay2526_rules["old_regime"]["slabs_general"]

    def test_zero_income(self, new_regime_slabs):
        assert _slab_tax(0, new_regime_slabs) == 0.0

    def test_within_nil_slab(self, new_regime_slabs):
        assert _slab_tax(200_000, new_regime_slabs) == 0.0

    def test_exactly_at_slab_boundary(self, new_regime_slabs):
        assert _slab_tax(300_000, new_regime_slabs) == 0.0

    def test_crosses_first_taxable_slab(self, new_regime_slabs):
        # 3L–7L at 5% → 4L * 5% = 20000; income 500k → 200k * 5% = 10000
        assert _slab_tax(500_000, new_regime_slabs) == 10_000.0

    def test_full_new_regime_700k(self, new_regime_slabs):
        # 0-3L: 0, 3-7L: 4L*5% = 20k
        assert _slab_tax(700_000, new_regime_slabs) == 20_000.0

    def test_new_regime_1m(self, new_regime_slabs):
        # 0-3L: 0, 3-7L: 20k, 7-10L: 3L*10% = 30k → total 50k
        assert _slab_tax(1_000_000, new_regime_slabs) == 50_000.0

    def test_new_regime_2m(self, new_regime_slabs):
        # 0-3L: 0, 3-7L: 20k, 7-10L: 30k, 10-12L: 30k, 12-15L: 60k, 15-20L: 5L*30%=150k → total 290k
        assert _slab_tax(2_000_000, new_regime_slabs) == 290_000.0

    def test_old_regime_general_basic(self, old_regime_slabs):
        # 0-2.5L: 0, 2.5-5L: 2.5L*5% = 12500
        assert _slab_tax(500_000, old_regime_slabs) == 12_500.0

    def test_old_regime_general_10l(self, old_regime_slabs):
        # 0-2.5L: 0, 2.5-5L: 12500, 5-10L: 5L*20% = 100k → 112500
        assert _slab_tax(1_000_000, old_regime_slabs) == 112_500.0

    @pytest.mark.parametrize("income,expected", [
        (0, 0.0),
        (250_000, 0.0),
        (300_000, 2_500.0),
        (500_000, 12_500.0),
        (1_000_000, 112_500.0),
        (1_500_000, 262_500.0),
    ])
    def test_old_regime_parametrized(self, old_regime_slabs, income, expected):
        assert _slab_tax(income, old_regime_slabs) == expected


# ---------------------------------------------------------------------------
# _rebate_87a
# ---------------------------------------------------------------------------

class TestRebate87A:
    def test_below_threshold_full_rebate(self):
        rules = {"max_income": 500_000, "max_rebate": 12_500}
        assert _rebate_87a(12_500, 450_000, rules, False) == 12_500

    def test_at_threshold_full_rebate(self):
        rules = {"max_income": 500_000, "max_rebate": 12_500}
        assert _rebate_87a(12_500, 500_000, rules, False) == 12_500

    def test_above_threshold_no_rebate(self):
        rules = {"max_income": 500_000, "max_rebate": 12_500}
        assert _rebate_87a(12_500, 500_001, rules, False) == 0.0

    def test_rebate_capped_at_slab_tax(self):
        rules = {"max_income": 500_000, "max_rebate": 12_500}
        assert _rebate_87a(5_000, 300_000, rules, False) == 5_000

    def test_new_regime_marginal_relief(self):
        rules = {"max_income": 700_000, "max_rebate": 25_000}
        slab_tax = 20_000.0
        income = 700_000
        rebate = _rebate_87a(slab_tax, income, rules, True)
        assert rebate == 20_000.0


# ---------------------------------------------------------------------------
# _surcharge
# ---------------------------------------------------------------------------

class TestSurcharge:
    def test_no_surcharge_below_50l(self, ay2526_rules):
        slabs = ay2526_rules["surcharge"]["old_regime"]
        assert _surcharge(100_000, 4_000_000, slabs) == 0.0

    def test_10pct_surcharge_above_50l(self, ay2526_rules):
        slabs = ay2526_rules["surcharge"]["old_regime"]
        result = _surcharge(100_000, 6_000_000, slabs)
        assert result == 10_000.0

    def test_surcharge_with_cap(self, ay2526_rules):
        slabs = ay2526_rules["surcharge"]["old_regime"]
        result = _surcharge(100_000, 6_000_000, slabs, cap=5)
        assert result == 5_000.0


# ---------------------------------------------------------------------------
# compute_regime (integration-style with real rules)
# ---------------------------------------------------------------------------

class TestComputeRegime:
    def test_zero_income_zero_tax(self, ay2526_rules, minimal_income, zero_deductions):
        result = compute_regime(minimal_income, zero_deductions, ay2526_rules, "new", "general")
        assert result["total_tax"] == 0

    def test_salary_only_new_regime(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 1_000_000
        result = compute_regime(minimal_income, zero_deductions, ay2526_rules, "new", "general")
        # Net salary: 10L - 75k SD = 9.25L
        # Slab: 0-3L:0, 3-7L:20k, 7-9.25L: 2.25L*10% = 22.5k → total 42.5k
        # No rebate (income > 7L), no surcharge, cess = 42500 * 4% = 1700
        # Total = ceil(42500 + 1700) = 44200
        assert result["slab_income"] == 925_000
        assert result["total_tax"] == 44_200

    def test_salary_only_old_regime(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 1_000_000
        result = compute_regime(minimal_income, zero_deductions, ay2526_rules, "old", "general")
        # Net salary: 10L - 50k SD = 9.5L
        # Old slabs general: 0-2.5L:0, 2.5-5L: 12.5k, 5-9.5L: 4.5L*20% = 90k → 102.5k
        # No rebate (>5L), cess = 102500*4% = 4100
        assert result["slab_income"] == 950_000
        assert result["total_tax"] == math.ceil(102_500 + 4_100)

    def test_refund_due_when_tds_exceeds_tax(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 500_000
        minimal_income["salary"]["total_tds"] = 50_000
        result = compute_regime(minimal_income, zero_deductions, ay2526_rules, "new", "general")
        assert result["refund_due"] is True
        assert result["balance"] < 0

    def test_deductions_reduce_old_regime_tax(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 1_200_000
        no_ded = compute_regime(minimal_income, zero_deductions, ay2526_rules, "old", "general")
        with_ded = {**zero_deductions, "80C": 150_000, "80D_self": 25_000}
        result = compute_regime(minimal_income, with_ded, ay2526_rules, "old", "general")
        assert result["total_tax"] < no_ded["total_tax"]

    def test_capital_gains_taxed_at_special_rate(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 500_000
        minimal_income["capital_gains"]["equity_stcg"] = 200_000
        result = compute_regime(minimal_income, zero_deductions, ay2526_rules, "new", "general")
        # STCG at 20% = 40000
        assert result["special_rate_tax"] >= 40_000


# ---------------------------------------------------------------------------
# compare_regimes
# ---------------------------------------------------------------------------

class TestCompareRegimes:
    def test_recommends_lower_tax_regime(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 1_000_000
        result = compare_regimes(minimal_income, zero_deductions, ay2526_rules, "general")
        assert result["recommended_regime"] in ("old", "new")
        assert result["savings_by_choosing_recommended"] >= 0
        assert result[result["recommended_regime"]]["total_tax"] <= result[
            "old" if result["recommended_regime"] == "new" else "new"
        ]["total_tax"]

    def test_both_regimes_computed(self, ay2526_rules, minimal_income, zero_deductions):
        minimal_income["salary"]["gross"] = 800_000
        result = compare_regimes(minimal_income, zero_deductions, ay2526_rules, "general")
        assert "old" in result and "new" in result
        for regime in ("old", "new"):
            for key in ("total_tax", "slab_income", "cess", "surcharge"):
                assert key in result[regime]
