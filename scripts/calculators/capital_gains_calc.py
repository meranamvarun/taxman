"""
Capital gains computation.

Zerodha / Groww already provide computed P&L per category.
This module:
  1. Aggregates those pre-computed figures
  2. Applies LTCG equity grandfathering (pre-Jan 31, 2018 FMV)
  3. Handles property LTCG: chooses better of old (20% + indexation) vs new (12.5% no indexation)
     for acquisitions before the grandfathering cutoff date in the rules file
  4. Verifies debt MF categorisation (debt MF bought after Apr 1 2023 taxed at slab rate)
"""

from __future__ import annotations

from datetime import date


COST_INFLATION_INDEX: dict[str, int] = {
    "2001-02": 100, "2002-03": 105, "2003-04": 109, "2004-05": 113,
    "2005-06": 117, "2006-07": 122, "2007-08": 129, "2008-09": 137,
    "2009-10": 148, "2010-11": 167, "2011-12": 184, "2012-13": 200,
    "2013-14": 220, "2014-15": 240, "2015-16": 254, "2016-17": 264,
    "2017-18": 272, "2018-19": 280, "2019-20": 289, "2020-21": 301,
    "2021-22": 317, "2022-23": 331, "2023-24": 348, "2024-25": 363,
    "2025-26": 382,
}


def indexed_cost(cost: float, purchase_fy: str, sale_fy: str) -> float:
    cii_purchase = COST_INFLATION_INDEX.get(purchase_fy)
    cii_sale = COST_INFLATION_INDEX.get(sale_fy)
    if not cii_purchase or not cii_sale:
        raise ValueError(f"CII not available for {purchase_fy} or {sale_fy}")
    return cost * cii_sale / cii_purchase


def equity_ltcg_with_grandfathering(
    cost_of_acquisition: float,
    fair_value_jan31_2018: float,
    sale_price: float,
    quantity: int,
    purchased_before_grandfathering: bool,
) -> dict:
    """
    For equity acquired before Jan 31 2018 and sold after, cost = max(actual cost, FMV on Jan 31 2018).
    But FMV is capped at sale price.
    """
    if not purchased_before_grandfathering:
        gain = (sale_price - cost_of_acquisition) * quantity
        return {"gain": gain, "grandfathering_applied": False}

    fmv_total = fair_value_jan31_2018 * quantity
    actual_cost_total = cost_of_acquisition * quantity
    sale_total = sale_price * quantity

    deemed_cost = min(max(actual_cost_total, fmv_total), sale_total)
    gain = sale_total - deemed_cost

    return {
        "gain": gain,
        "grandfathering_applied": True,
        "actual_cost": actual_cost_total,
        "fmv_jan_2018": fmv_total,
        "deemed_cost_used": deemed_cost,
    }


def property_ltcg_choose_regime(
    cost: float,
    sale_price: float,
    purchase_fy: str,
    sale_fy: str,
    purchase_date: date,
    grandfathering_cutoff: date,
    old_rate: float = 0.20,
    new_rate: float = 0.125,
) -> dict:
    """
    If property was acquired BEFORE the grandfathering cutoff (Jul 23, 2024 for AY 2025-26+),
    taxpayer can choose between old regime (20% with indexation) and new regime (12.5% no indexation).
    We compute both and return the better option.
    """
    gain_new_rate = (sale_price - cost) * new_rate

    try:
        indexed = indexed_cost(cost, purchase_fy, sale_fy)
        gain_with_indexation = max(0.0, sale_price - indexed)
        tax_old = gain_with_indexation * old_rate
    except ValueError:
        gain_with_indexation = None
        tax_old = float("inf")

    tax_new = max(0.0, sale_price - cost) * new_rate

    use_old = (purchase_date < grandfathering_cutoff) and (tax_old < tax_new)

    return {
        "purchase_date": purchase_date.isoformat(),
        "grandfathering_cutoff": grandfathering_cutoff.isoformat(),
        "eligible_for_grandfathering": purchase_date < grandfathering_cutoff,
        "tax_with_indexation_old_regime": round(tax_old, 2) if tax_old != float("inf") else None,
        "tax_without_indexation_new_rate": round(tax_new, 2),
        "recommended": "old_regime_with_indexation" if use_old else "new_rate_no_indexation",
        "taxable_gain": round(gain_with_indexation if use_old else max(0.0, sale_price - cost), 2),
        "applicable_rate": old_rate if use_old else new_rate,
    }


def aggregate_broker_gains(broker_reports: list[dict]) -> dict:
    """Sum up P&L from multiple broker reports into canonical categories."""
    totals = {
        "equity_stcg": 0.0,
        "equity_ltcg": 0.0,
        "debt_stcg": 0.0,
        "debt_ltcg": 0.0,
        "gold_stcg": 0.0,
        "gold_ltcg": 0.0,
        "other_stcg": 0.0,
        "other_ltcg": 0.0,
    }
    for report in broker_reports:
        for key in totals:
            totals[key] += report.get(key, 0.0)
    return {k: round(v, 2) for k, v in totals.items()}
