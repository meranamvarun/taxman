"""
ITR-2 form filler — includes all ITR-1 sections plus:
  - Schedule CG (Capital Gains)
  - Schedule OS (Other Sources, detailed)
  - Schedule VDA (Virtual Digital Assets)
  - Schedule AL (Assets & Liabilities, if income > ₹50L)
  - Schedule FA (Foreign Assets)
  - Schedule FSI (Foreign Source Income)
  - Schedule TR (Tax Relief / DTAA)

CLI:
  python -m scripts.portal.itr2_filler --state state/session.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from scripts.portal import session as sess
from scripts.portal import navigator as nav
from scripts.portal.itr1_filler import (
    _fill_personal, _fill_deductions, _fill_tax_paid
)


def fill_itr2(page, state: dict) -> None:
    tp = state["taxpayer"]
    income = state["income"]
    deds = state["deductions"]
    cg = income["capital_gains"]
    fa = state.get("foreign_assets", {})

    # 1. Personal
    print("  Filling Personal Information...")
    _fill_personal(page, tp)
    sess.human_pause(page, "Verify personal information. Press Enter to continue.", "personal")

    # 2. Salary income
    print("  Filling Salary section...")
    _fill_salary_itr2(page, income["salary"])
    sess.human_pause(page, "Verify salary figures against Form 16. Press Enter.", "salary")

    # 3. House Property
    print("  Filling House Property section...")
    _fill_house_property(page, income["house_property"])
    sess.human_pause(page, "Verify house property income/loss. Press Enter.", "house_property")

    # 4. Capital Gains
    print("  Filling Capital Gains section...")
    _fill_capital_gains(page, cg)
    sess.human_pause(
        page,
        "Capital gains section filled. Verify equity STCG/LTCG and other gains.\n"
        "  LTCG equity exemption of ₹1,25,000 is applied by portal automatically.\n"
        "  Press Enter to continue.",
        "capital_gains",
    )

    # 5. Other Sources
    print("  Filling Other Sources section...")
    _fill_other_sources(page, income["other_sources"])
    sess.human_pause(page, "Verify interest and dividend income. Press Enter.", "other_sources")

    # 6. Deductions
    print("  Filling Deductions (VI-A)...")
    _fill_deductions(page, deds)
    sess.human_pause(page, "Verify all deductions. Press Enter.", "deductions")

    # 7. Foreign Assets (Schedule FA)
    if _has_foreign_assets(fa):
        print("  Filling Schedule FA (Foreign Assets)...")
        _fill_schedule_fa(page, fa)
        sess.human_pause(
            page,
            "Schedule FA (Foreign Assets) filled.\n"
            "  Verify each foreign account/asset entry carefully.\n"
            "  Press Enter to continue.",
            "schedule_fa",
        )

    # 8. Foreign Source Income (Schedule FSI)
    if _has_foreign_income(income.get("foreign_source", {})):
        print("  Filling Schedule FSI (Foreign Source Income)...")
        _fill_schedule_fsi(page, income["foreign_source"], fa.get("dtaa_relief", []))
        sess.human_pause(page, "Verify foreign source income and DTAA relief. Press Enter.", "fsi")

    # 9. Schedule AL (if required)
    if _requires_schedule_al(income, state.get("tax_computation", {})):
        sess.human_pause(
            page,
            "Schedule AL (Assets & Liabilities) is required since income > ₹50L.\n"
            "  Please fill in the assets and liabilities details manually on the portal.\n"
            "  This includes movable assets, immovable property, investments, loans, etc.\n"
            "  Press Enter once Schedule AL is filled.",
            "schedule_al",
        )

    # 10. Tax Paid
    print("  Filling Tax Paid section...")
    _fill_tax_paid(page, state)
    sess.human_pause(page, "Verify TDS and advance tax entries. Press Enter.", "tax_paid")

    print("  ITR-2 sections complete. Proceeding to preview...")


def _fill_salary_itr2(page, salary: dict) -> None:
    gross = int(salary.get("gross", 0))
    std_ded = int(salary.get("standard_deduction", 50000))
    prof_tax = int(salary.get("professional_tax", 0))

    sess.safe_fill(page, "input[id*='grossSalary'], input[name*='grossSalary']", str(gross), "gross salary")
    time.sleep(0.3)
    sess.safe_fill(page, "input[id*='stdDeduction'], input[name*='stdDeduction']", str(std_ded), "standard deduction")
    time.sleep(0.2)
    if prof_tax:
        sess.safe_fill(page, "input[id*='profTax'], input[name*='profTax']", str(prof_tax), "professional tax")


def _fill_house_property(page, hp: dict) -> None:
    net = int(hp.get("net", 0))
    if net == 0:
        return
    sess.safe_fill(page, "input[id*='houseProperty'], input[name*='houseProperty']", str(net), "HP income")


def _fill_capital_gains(page, cg: dict) -> None:
    # Equity STCG (20%)
    if cg.get("equity_stcg", 0):
        sess.safe_fill(page, "input[id*='equitySTCG'], input[name*='equitySTCG']",
                       str(int(cg["equity_stcg"])), "equity STCG")
        time.sleep(0.2)

    # Equity LTCG (12.5%, exemption applied by portal)
    if cg.get("equity_ltcg", 0):
        sess.safe_fill(page, "input[id*='equityLTCG'], input[name*='equityLTCG']",
                       str(int(cg["equity_ltcg"])), "equity LTCG")
        time.sleep(0.2)

    # Other STCG (slab rate)
    other_stcg = int(cg.get("debt_stcg", 0) + cg.get("property_stcg", 0) + cg.get("other_stcg", 0))
    if other_stcg:
        sess.safe_fill(page, "input[id*='otherSTCG'], input[name*='otherSTCG']",
                       str(other_stcg), "other STCG")
        time.sleep(0.2)

    # Other LTCG (12.5% or slab depending on asset)
    property_ltcg = int(cg.get("property_ltcg", 0))
    gold_ltcg = int(cg.get("gold_ltcg", 0))
    if property_ltcg:
        sess.safe_fill(page, "input[id*='propertyLTCG'], input[name*='propertyLTCG']",
                       str(property_ltcg), "property LTCG")
        time.sleep(0.2)

    # VDA (30%)
    if cg.get("vda", 0):
        sess.safe_fill(page, "input[id*='vda'], input[name*='vda']",
                       str(int(cg["vda"])), "VDA gains")


def _fill_other_sources(page, os: dict) -> None:
    total_interest = int(os.get("savings_interest", 0) + os.get("fd_interest", 0))
    if total_interest:
        sess.safe_fill(page, "input[id*='interest'], input[name*='otherInterest']",
                       str(total_interest), "interest income")
        time.sleep(0.2)

    dividend = int(os.get("dividend", 0))
    if dividend:
        sess.safe_fill(page, "input[id*='dividend'], input[name*='dividend']",
                       str(dividend), "dividend income")

    other = int(os.get("other", 0))
    if other:
        sess.safe_fill(page, "input[id*='otherSources'], input[name*='otherSources']",
                       str(other), "other income")


def _fill_schedule_fa(page, fa: dict) -> None:
    """Fill Schedule FA — Foreign Assets. Each entry requires manual verification."""
    bank_accounts = fa.get("bank_accounts", [])
    for i, acct in enumerate(bank_accounts):
        print(f"    Adding foreign bank account {i+1}: {acct.get('bank_name', '')} ({acct.get('country', '')})")
        sess.human_pause(
            page,
            f"  Please add foreign bank account #{i+1} manually:\n"
            f"    Country: {acct.get('country', '')}\n"
            f"    Bank: {acct.get('bank_name', '')}\n"
            f"    Account: {acct.get('account_number', '')}\n"
            f"    Peak Balance: {acct.get('peak_balance', '')}\n"
            f"    Closing Balance: {acct.get('closing_balance', '')}\n"
            f"    Interest: {acct.get('interest_credited', 0)}\n"
            "  Click 'Add' in Schedule FA, fill the form, and press Enter when done.",
            f"schedule_fa_bank_{i+1}",
        )

    for i, asset in enumerate(fa.get("equity_debt", [])):
        print(f"    Adding foreign equity/debt {i+1}: {asset.get('entity_name', '')}")
        sess.human_pause(
            page,
            f"  Please add foreign equity/debt #{i+1} manually:\n"
            f"    Entity: {asset.get('entity_name', '')}\n"
            f"    Country: {asset.get('country', '')}\n"
            f"    Investment cost: {asset.get('cost', '')}\n"
            f"    Fair market value: {asset.get('fmv', '')}\n"
            "  Fill in Schedule FA → Part C and press Enter when done.",
            f"schedule_fa_equity_{i+1}",
        )

    for i, prop in enumerate(fa.get("immovable_property", [])):
        sess.human_pause(
            page,
            f"  Please add foreign immovable property #{i+1} manually:\n"
            f"    Country: {prop.get('country', '')}\n"
            f"    Address: {prop.get('address', '')}\n"
            f"    Acquisition year: {prop.get('year_acquired', '')}\n"
            f"    Cost: {prop.get('cost', '')}\n"
            "  Fill in Schedule FA → Part D and press Enter when done.",
            f"schedule_fa_property_{i+1}",
        )


def _fill_schedule_fsi(page, foreign_income: dict, dtaa_relief: list) -> None:
    total = sum(foreign_income.values())
    if total <= 0:
        return
    sess.human_pause(
        page,
        f"  Please fill Schedule FSI (Foreign Source Income) manually:\n"
        f"    Total foreign income: ₹{total:,.0f}\n"
        f"    Breakdown: {json.dumps(foreign_income)}\n"
        f"    DTAA relief entries: {len(dtaa_relief)}\n"
        "  Refer to your foreign tax documents and press Enter when done.",
        "schedule_fsi",
    )


def _has_foreign_assets(fa: dict) -> bool:
    return any(
        bool(fa.get(k))
        for k in ["bank_accounts", "custodial_accounts", "equity_debt", "immovable_property", "other_assets", "trusts"]
    )


def _has_foreign_income(fi: dict) -> bool:
    return any(v > 0 for v in fi.values())


def _requires_schedule_al(income: dict, tax_comp: dict) -> bool:
    total = (
        income["salary"].get("gross", 0)
        + income["other_sources"].get("fd_interest", 0)
        + income["other_sources"].get("savings_interest", 0)
        + income["other_sources"].get("dividend", 0)
    )
    return total > 5000000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="state/session.json")
    args = parser.parse_args()

    with open(args.state) as f:
        state = json.load(f)

    pw, browser, page = sess.launch()
    try:
        sess.open_portal(page)
        sess.wait_for_login(page)
        nav.navigate_to_file_itr(page)
        nav.select_ay_and_mode(page, state["session"]["ay"])
        nav.select_itr_form(page, "ITR-2")
        fill_itr2(page, state)
    finally:
        input("  Press Enter to close browser...")
        sess.close(pw, browser)


if __name__ == "__main__":
    main()
