"""Tests for capital gains computation helpers."""

from __future__ import annotations

from datetime import date

import pytest

from scripts.calculators.capital_gains_calc import (
    indexed_cost,
    equity_ltcg_with_grandfathering,
    property_ltcg_choose_regime,
    aggregate_broker_gains,
    COST_INFLATION_INDEX,
)


class TestIndexedCost:
    def test_same_year_returns_cost(self):
        assert indexed_cost(100_000, "2020-21", "2020-21") == 100_000

    def test_inflation_increases_cost(self):
        result = indexed_cost(100_000, "2001-02", "2024-25")
        assert result == 100_000 * 363 / 100

    def test_known_cii_pair(self):
        result = indexed_cost(200_000, "2010-11", "2020-21")
        expected = 200_000 * COST_INFLATION_INDEX["2020-21"] / COST_INFLATION_INDEX["2010-11"]
        assert result == pytest.approx(expected)

    def test_invalid_fy_raises(self):
        with pytest.raises(ValueError, match="CII not available"):
            indexed_cost(100_000, "1990-91", "2024-25")


class TestEquityLTCGGrandfathering:
    def test_no_grandfathering(self):
        result = equity_ltcg_with_grandfathering(
            cost_of_acquisition=100,
            fair_value_jan31_2018=0,
            sale_price=200,
            quantity=10,
            purchased_before_grandfathering=False,
        )
        assert result["gain"] == 1_000
        assert result["grandfathering_applied"] is False

    def test_grandfathering_fmv_higher_than_cost(self):
        result = equity_ltcg_with_grandfathering(
            cost_of_acquisition=50,
            fair_value_jan31_2018=150,
            sale_price=200,
            quantity=10,
            purchased_before_grandfathering=True,
        )
        # deemed_cost = min(max(500, 1500), 2000) = 1500
        assert result["gain"] == 2000 - 1500
        assert result["grandfathering_applied"] is True

    def test_grandfathering_fmv_capped_at_sale_price(self):
        result = equity_ltcg_with_grandfathering(
            cost_of_acquisition=50,
            fair_value_jan31_2018=250,
            sale_price=200,
            quantity=10,
            purchased_before_grandfathering=True,
        )
        # deemed_cost = min(max(500, 2500), 2000) = 2000
        assert result["gain"] == 0
        assert result["deemed_cost_used"] == 2000

    def test_loss_scenario(self):
        result = equity_ltcg_with_grandfathering(
            cost_of_acquisition=200,
            fair_value_jan31_2018=150,
            sale_price=100,
            quantity=10,
            purchased_before_grandfathering=True,
        )
        # deemed_cost = min(max(2000, 1500), 1000) = 1000
        assert result["gain"] == 0


class TestPropertyLTCGChooseRegime:
    def test_old_regime_better_with_indexation(self):
        result = property_ltcg_choose_regime(
            cost=1_000_000,
            sale_price=5_000_000,
            purchase_fy="2010-11",
            sale_fy="2024-25",
            purchase_date=date(2010, 6, 1),
            grandfathering_cutoff=date(2024, 7, 23),
        )
        assert result["eligible_for_grandfathering"] is True
        assert result["recommended"] in ("old_regime_with_indexation", "new_rate_no_indexation")

    def test_post_cutoff_always_new_rate(self):
        result = property_ltcg_choose_regime(
            cost=1_000_000,
            sale_price=2_000_000,
            purchase_fy="2024-25",
            sale_fy="2025-26",
            purchase_date=date(2024, 8, 1),
            grandfathering_cutoff=date(2024, 7, 23),
        )
        assert result["eligible_for_grandfathering"] is False
        assert result["recommended"] == "new_rate_no_indexation"

    def test_invalid_cii_falls_back_to_new(self):
        result = property_ltcg_choose_regime(
            cost=1_000_000,
            sale_price=5_000_000,
            purchase_fy="1990-91",
            sale_fy="2024-25",
            purchase_date=date(1990, 6, 1),
            grandfathering_cutoff=date(2024, 7, 23),
        )
        assert result["tax_with_indexation_old_regime"] is None
        assert result["recommended"] == "new_rate_no_indexation"


class TestAggregateBrokerGains:
    def test_empty_list(self):
        result = aggregate_broker_gains([])
        assert all(v == 0.0 for v in result.values())

    def test_single_report(self):
        report = {"equity_stcg": 50_000, "equity_ltcg": 100_000, "debt_stcg": 10_000}
        result = aggregate_broker_gains([report])
        assert result["equity_stcg"] == 50_000
        assert result["equity_ltcg"] == 100_000
        assert result["debt_stcg"] == 10_000
        assert result["gold_ltcg"] == 0.0

    def test_multiple_reports_summed(self):
        reports = [
            {"equity_stcg": 10_000, "equity_ltcg": 20_000},
            {"equity_stcg": 5_000, "debt_ltcg": 15_000},
        ]
        result = aggregate_broker_gains(reports)
        assert result["equity_stcg"] == 15_000
        assert result["equity_ltcg"] == 20_000
        assert result["debt_ltcg"] == 15_000
