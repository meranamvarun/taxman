"""
Tax computation for old and new regime.

Handles:
- Slab tax for general / senior / super-senior
- Special rate tax (capital gains, VDA) computed separately from slab income
- Rebate u/s 87A with marginal relief
- Surcharge with LTCG equity cap at 15%
- Health & Education Cess at 4%

CLI:
  python -m scripts.calculators.tax_calculator --ay 2026-27 --state state/session.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from scripts.calculators import tax_rules


def _slab_tax(income: float, slabs: list[dict]) -> float:
    tax = 0.0
    for slab in slabs:
        lo = slab["from"]
        hi = slab["to"]
        rate = slab["rate"] / 100
        if income <= lo:
            break
        taxable = (min(income, hi) - lo) if hi else (income - lo)
        tax += taxable * rate
    return tax


def _rebate_87a(slab_tax: float, total_income: float, rules_87a: dict, marginal_relief: bool) -> float:
    max_income = rules_87a["max_income"]
    max_rebate = rules_87a["max_rebate"]
    if total_income > max_income:
        return 0.0
    rebate = min(slab_tax, max_rebate)
    if marginal_relief and total_income > max_income - 100000:
        # Marginal relief: extra tax over the threshold can't exceed extra income
        excess_income = max(0.0, total_income - max_income)
        rebate = max(0.0, slab_tax - excess_income)
    return rebate


def _surcharge(tax: float, total_income: float, slabs: list[dict], cap: float | None = None) -> float:
    rate = 0.0
    for slab in slabs:
        if total_income > slab["from"]:
            rate = slab["rate"] / 100
    if cap is not None:
        rate = min(rate, cap / 100)
    return tax * rate


def compute_regime(
    income_data: dict,
    deductions: dict,
    rules: dict,
    regime: str,
    taxpayer_category: str,
) -> dict:
    """
    Compute tax for one regime ('old' or 'new').
    Returns detailed breakdown dict.
    """
    r = rules[f"{regime}_regime"]
    cg_rules = rules["capital_gains"]

    # --- Salary income ---
    gross_salary = income_data["salary"]["gross"]
    std_ded = r["standard_deduction_salary"]
    professional_tax = income_data["salary"].get("professional_tax", 0)
    net_salary = max(0.0, gross_salary - std_ded - professional_tax)

    # --- Deductions (only old regime; new regime allows 80CCD2 + SD only) ---
    if regime == "old":
        allowed_deds = _compute_old_regime_deductions(deductions, rules, gross_salary, taxpayer_category)
    else:
        # New regime: only 80CCD2 (employer NPS) is allowed beyond SD
        allowed_deds = deductions.get("80CCD2", 0)

    # --- House property ---
    hp_income = income_data["house_property"]["net"]

    # --- Other sources ---
    os_income = sum(income_data["other_sources"].values())

    # --- Foreign source income (added to gross) ---
    foreign_income = sum(income_data.get("foreign_source", {}).values())

    # --- Slab income (excludes special-rate capital gains) ---
    slab_income = net_salary + hp_income + os_income + foreign_income - allowed_deds
    slab_income = max(0.0, slab_income)

    # Add non-special CG (debt MF, property STCG at slab rate)
    slab_income_with_slab_cg = slab_income + _slab_rate_cg(income_data)

    # --- Special rate capital gains ---
    equity_stcg = income_data["capital_gains"]["equity_stcg"]
    equity_ltcg_raw = income_data["capital_gains"]["equity_ltcg"]
    exemption = cg_rules["equity_ltcg_exemption"]
    equity_ltcg = max(0.0, equity_ltcg_raw - exemption)
    vda = income_data["capital_gains"].get("vda", 0)
    gold_ltcg = income_data["capital_gains"].get("gold_ltcg", 0)
    property_ltcg = income_data["capital_gains"].get("property_ltcg", 0)

    # --- Total income for rebate/surcharge threshold ---
    total_income = (
        slab_income_with_slab_cg
        + equity_stcg
        + equity_ltcg_raw
        + vda
        + gold_ltcg
        + property_ltcg
    )

    # --- Slab tax ---
    if regime == "old":
        key = f"slabs_{taxpayer_category}"
        slabs = r.get(key, r["slabs_general"])
    else:
        slabs = r["slabs"]
    slab_tax = _slab_tax(slab_income_with_slab_cg, slabs)

    # --- Special rate taxes ---
    stcg_tax = equity_stcg * (cg_rules["equity_stcg_rate"] / 100)
    ltcg_tax = equity_ltcg * (cg_rules["equity_ltcg_rate"] / 100)
    vda_tax = vda * (cg_rules["vda_rate"] / 100)
    gold_ltcg_tax = gold_ltcg * (cg_rules.get("gold_ltcg_rate", 12.5) / 100)
    property_ltcg_tax = property_ltcg * (cg_rules["property_ltcg_rate"] / 100)
    special_tax = stcg_tax + ltcg_tax + vda_tax + gold_ltcg_tax + property_ltcg_tax

    # --- Rebate 87A (applies only to slab tax, not special-rate tax) ---
    r87 = r["rebate_87a"]
    rebate = _rebate_87a(slab_tax, slab_income_with_slab_cg, r87, r.get("marginal_relief_87a", False))
    slab_tax_after_rebate = max(0.0, slab_tax - rebate)

    total_before_surcharge = slab_tax_after_rebate + special_tax

    # --- Surcharge ---
    regime_key = "old_regime" if regime == "old" else "new_regime"
    surcharge_slabs = rules["surcharge"][regime_key]
    surcharge_on_slab = _surcharge(slab_tax_after_rebate, total_income, surcharge_slabs)
    # Equity CG surcharge capped at 15%
    cg_sur_cap = rules["surcharge"].get("capital_gains_equity_cap", 15)
    surcharge_on_cg = _surcharge(stcg_tax + ltcg_tax, total_income, surcharge_slabs, cap=cg_sur_cap)
    surcharge_on_other_cg = _surcharge(vda_tax + gold_ltcg_tax + property_ltcg_tax, total_income, surcharge_slabs)
    total_surcharge = surcharge_on_slab + surcharge_on_cg + surcharge_on_other_cg

    tax_before_cess = total_before_surcharge + total_surcharge

    # --- Cess 4% ---
    cess = tax_before_cess * (rules["cess_rate"] / 100)

    total_tax = math.ceil(tax_before_cess + cess)

    # --- TDS already paid ---
    tds_paid = income_data["salary"]["total_tds"]
    advance_paid = sum(e.get("amount", 0) for e in income_data.get("advance_tax_entries", []))

    balance = total_tax - tds_paid - advance_paid

    return {
        "taxable_income": round(slab_income_with_slab_cg + equity_stcg + equity_ltcg_raw + vda + gold_ltcg + property_ltcg),
        "slab_income": round(slab_income_with_slab_cg),
        "slab_tax": round(slab_tax, 2),
        "rebate_87a": round(rebate, 2),
        "slab_tax_after_rebate": round(slab_tax_after_rebate, 2),
        "special_rate_tax": round(special_tax, 2),
        "surcharge": round(total_surcharge, 2),
        "cess": round(cess, 2),
        "total_tax": total_tax,
        "tds_paid": round(tds_paid, 2),
        "advance_tax_paid": round(advance_paid, 2),
        "balance": round(balance),
        "refund_due": round(balance) < 0,
    }


def _slab_rate_cg(income_data: dict) -> float:
    cg = income_data["capital_gains"]
    return (
        cg.get("debt_stcg", 0)
        + cg.get("debt_ltcg", 0)
        + cg.get("property_stcg", 0)
        + cg.get("other_stcg", 0)
        + cg.get("other_ltcg", 0)
    )


def _compute_old_regime_deductions(deductions: dict, rules: dict, gross_salary: float, taxpayer_category: str) -> float:
    lim = rules["deduction_limits"]

    c80c = min(
        deductions.get("80C", 0) + deductions.get("80CCC", 0) + deductions.get("80CCD1", 0),
        lim["80C_80CCC_80CCD1_combined_max"],
    )
    c80ccd1b = min(deductions.get("80CCD1B", 0), lim["80CCD1B_max"])
    c80ccd2 = min(deductions.get("80CCD2", 0), gross_salary * lim["80CCD2_max_percent_salary"] / 100)

    if taxpayer_category in ("senior", "super_senior"):
        d80d_self_lim = lim["80D_self_senior"]
        d80d_par_lim = lim["80D_parents_senior"]
    else:
        d80d_self_lim = lim["80D_self_below_60"]
        d80d_par_lim = lim["80D_parents_below_60"]

    c80d = min(deductions.get("80D_self", 0), d80d_self_lim) + min(deductions.get("80D_parents", 0), d80d_par_lim)
    c80e = deductions.get("80E", 0)

    c80g = 0.0
    for donation in deductions.get("80G", []):
        pct = donation.get("deductible_percent", 50)
        qualified = donation.get("amount", 0) * pct / 100
        c80g += qualified

    if taxpayer_category == "super_senior":
        c80ttb = min(deductions.get("80TTB", 0), lim["80TTB_max"])
        c80tta = 0
    elif taxpayer_category == "senior":
        c80ttb = min(deductions.get("80TTB", 0), lim["80TTB_max"])
        c80tta = 0
    else:
        c80tta = min(deductions.get("80TTA", 0), lim["80TTA_max"])
        c80ttb = 0

    hra = deductions.get("HRA_exempt", 0)
    lta = deductions.get("LTA_exempt", 0)

    return c80c + c80ccd1b + c80ccd2 + c80d + c80e + c80g + c80tta + c80ttb + hra + lta


def compare_regimes(income_data: dict, deductions: dict, rules: dict, taxpayer_category: str) -> dict:
    old = compute_regime(income_data, deductions, rules, "old", taxpayer_category)
    new = compute_regime(income_data, deductions, rules, "new", taxpayer_category)

    if old["total_tax"] <= new["total_tax"]:
        recommended = "old"
        savings = new["total_tax"] - old["total_tax"]
    else:
        recommended = "new"
        savings = old["total_tax"] - new["total_tax"]

    return {
        "old": old,
        "new": new,
        "recommended_regime": recommended,
        "savings_by_choosing_recommended": savings,
    }


def _cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ay", required=True)
    parser.add_argument("--state", default="state/session.json")
    args = parser.parse_args()

    with open(args.state) as f:
        state = json.load(f)

    rules = tax_rules.load(args.ay)
    from scripts.utils.validators import taxpayer_category as get_cat
    from datetime import date
    dob_str = state["taxpayer"].get("dob")
    if dob_str:
        dob = date.fromisoformat(dob_str)
        cat = get_cat(dob, args.ay)
    else:
        cat = "general"

    income_data = {**state["income"], "advance_tax_entries": state.get("advance_tax_paid", [])}
    result = compare_regimes(income_data, state["deductions"], rules, cat)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
