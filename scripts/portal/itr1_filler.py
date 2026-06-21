"""
ITR-1 form filler.

Fills all sections of ITR-1 (Sahaj) from the state dict.
Human pauses after each section for verification.

Sections:
  1. Personal Information
  2. Gross Total Income (Salary + Other Sources + HP)
  3. Deductions (Chapter VI-A)
  4. Tax Computation
  5. Tax Paid Details

CLI:
  python -m scripts.portal.itr1_filler --state state/session.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from scripts.portal import session as sess
from scripts.portal import navigator as nav


def fill_itr1(page, state: dict) -> None:
    tp = state["taxpayer"]
    income = state["income"]
    deds = state["deductions"]

    # 1. Personal Information
    print("  Filling Personal Information...")
    _fill_personal(page, tp)
    sess.human_pause(
        page,
        "Personal information section filled.\n"
        "  Please verify name, address, bank account, and filing type.\n"
        "  Press Enter to continue to Income section.",
        step_name="personal_info",
    )

    # 2. Income
    print("  Filling Income section...")
    _fill_income_itr1(page, income)
    sess.human_pause(
        page,
        "Income section filled (Salary, House Property, Other Sources).\n"
        "  Verify each figure against your Form 16 and AIS.\n"
        "  Press Enter to continue to Deductions.",
        step_name="income",
    )

    # 3. Deductions
    print("  Filling Deductions section...")
    _fill_deductions(page, deds)
    sess.human_pause(
        page,
        "Deductions section filled.\n"
        "  Verify 80C, 80D, and any other deductions.\n"
        "  Press Enter to continue to Tax Details.",
        step_name="deductions",
    )

    # 4. Tax computation is auto-calculated by portal — just verify
    sess.human_pause(
        page,
        "Review the Tax Computation section computed by the portal.\n"
        "  Compare with your computed figures in state/session.json.\n"
        "  If discrepancy > ₹100, press Ctrl+C to abort and re-check with /tax-compute.\n"
        "  Otherwise press Enter to continue.",
        step_name="tax_computation",
    )

    # 5. Tax Paid
    print("  Filling Tax Paid section...")
    _fill_tax_paid(page, state)
    sess.human_pause(
        page,
        "TDS and advance tax section filled.\n"
        "  Verify TDS entries match your Form 26AS.\n"
        "  Press Enter to Preview.",
        step_name="tax_paid",
    )

    print("  ITR-1 sections complete. Proceeding to preview...")


def _fill_personal(page, tp: dict) -> None:
    # Most personal info is pre-filled from PAN database; verify don't overwrite
    bank = tp.get("bank", {})
    if bank.get("account_number"):
        sess.safe_fill(page, "input[name*='bankAccountNumber'], input[id*='accountNumber']",
                       bank["account_number"], "bank account")
    if bank.get("ifsc"):
        sess.safe_fill(page, "input[name*='ifsc'], input[id*='ifsc']", bank["ifsc"], "IFSC")
    if tp.get("mobile"):
        sess.safe_fill(page, "input[name*='mobile'], input[id*='Mobile']", tp["mobile"], "mobile")
    if tp.get("email"):
        sess.safe_fill(page, "input[name*='email'], input[id*='Email']", tp["email"], "email")


def _fill_income_itr1(page, income: dict) -> None:
    salary = income["salary"]
    net_salary = salary.get("net", 0) or salary.get("gross", 0) - salary.get("standard_deduction", 50000)

    sess.safe_fill(page, "input[name*='salary'], input[id*='grossSalary']",
                   str(int(salary.get("gross", 0))), "gross salary")
    time.sleep(0.3)

    hp = income["house_property"]["net"]
    if hp != 0:
        sess.safe_fill(page, "input[name*='houseProperty'], input[id*='netHP']",
                       str(int(hp)), "house property income")
        time.sleep(0.3)

    other = sum(income["other_sources"].values())
    if other > 0:
        sess.safe_fill(page, "input[name*='otherSources'], input[id*='otherIncome']",
                       str(int(other)), "other sources")


def _fill_deductions(page, deds: dict) -> None:
    c80c = (deds.get("80C", 0) + deds.get("80CCC", 0) + deds.get("80CCD1", 0))
    if c80c:
        sess.safe_fill(page, "input[id*='80C'], input[name*='deduction80C']",
                       str(int(min(c80c, 150000))), "80C")
        time.sleep(0.2)

    c80ccd1b = deds.get("80CCD1B", 0)
    if c80ccd1b:
        sess.safe_fill(page, "input[id*='80CCD1B'], input[name*='deduction80CCD1B']",
                       str(int(min(c80ccd1b, 50000))), "80CCD1B")

    c80d = deds.get("80D_self", 0) + deds.get("80D_parents", 0)
    if c80d:
        sess.safe_fill(page, "input[id*='80D'], input[name*='deduction80D']",
                       str(int(c80d)), "80D")

    c80e = deds.get("80E", 0)
    if c80e:
        sess.safe_fill(page, "input[id*='80E'], input[name*='deduction80E']",
                       str(int(c80e)), "80E")


def _fill_tax_paid(page, state: dict) -> None:
    for tds in state.get("tds_credits", []):
        # TDS on salary is pre-populated from 26AS; we only need to verify
        pass
    # Self-assessment tax, if any
    for sat in state.get("self_assessment_tax_paid", []):
        sess.safe_fill(page, "input[name*='selfAssessment'], input[id*='selfAssessment']",
                       str(int(sat.get("amount", 0))), "self assessment tax")


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
        nav.select_itr_form(page, "ITR-1")
        fill_itr1(page, state)
    finally:
        input("  Press Enter to close browser...")
        sess.close(pw, browser)


if __name__ == "__main__":
    main()
