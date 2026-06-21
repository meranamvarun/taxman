# /tax-compute — Compute Tax Liability

Runs the tax calculator for both old and new regime, shows comparison, and recommends the better option.

## Token note
This skill uses ~800 tokens. Requires /tax-parse and /tax-reconcile to have been run first.

## Steps

### Step 1 — Load and validate state

Run: `python -m scripts.utils.state_manager status`

Check that income.salary.gross > 0 (or at least one income source has data).
If all income is zero, warn: "No income data found. Please run /tax-parse first."

Read state/session.json.
Note the AY from session.ay.

### Step 2 — Compute HRA exemption (if applicable)

If the taxpayer has HRA in Form 16 (income.salary.employers[*].part_b.hra_received > 0):
  Ask: "What is your annual rent paid? (₹) — enter 0 if not renting"
  Ask: "Which city do you live in? (for HRA metro/non-metro calculation)"

  Run:
  ```python
  from scripts.calculators.deduction_calculator import compute_hra_exemption
  # Use values from state + user input
  ```

  Display the HRA exemption calculation:
  - Limit 1 (actual HRA received): ₹X
  - Limit 2 (50%/40% of basic): ₹Y
  - Limit 3 (rent - 10% of basic): ₹Z
  - HRA exempt (minimum of above): ₹[min]

  Save: `python -m scripts.utils.state_manager set deductions.HRA_exempt [amount]`

  Note: HRA exemption is only available under the OLD regime.

### Step 3 — Finalize 80C figure

The 80C limit is ₹1,50,000. Sum all 80C sub-components:
PPF + ELSS + LIC + NSC + Home loan principal + SCSS + Sukanya + 80CCD1

If total > ₹1,50,000, cap at ₹1,50,000 and inform user:
"Total 80C investments ₹[X] exceed the ₹1.5L limit. Only ₹1,50,000 will be claimed."

Save capped value.

### Step 4 — Apply prior year losses

If prior_year_losses has any non-zero values:
  Apply to capital gains:
  - equity_stcl (from prior year) reduces current year equity STCG first, then equity LTCG
  - other_stcl reduces other STCG first
  - other_ltcl reduces other LTCG (not STCG)

  Print: "Prior year losses applied. Net capital gains after offset: ₹[X]"
  Save adjusted capital gains to state.

### Step 5 — Run tax calculation

Run: `python -m scripts.calculators.tax_calculator --ay [AY] --state state/session.json`

Capture and parse the JSON output containing old and new regime computations.

### Step 6 — Display comparison table

```
TAX COMPUTATION — AY [AY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                              OLD REGIME    NEW REGIME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gross Salary                  ₹X,XX,XXX     ₹X,XX,XXX
(-) Standard Deduction        ₹  50,000     ₹  75,000
(-) Deductions (VI-A)         ₹X,XX,XXX     ₹      0
(+) House Property            ₹X,XX,XXX     ₹X,XX,XXX
(+) Capital Gains (slab)      ₹X,XX,XXX     ₹X,XX,XXX
(+) Other Sources             ₹X,XX,XXX     ₹X,XX,XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Taxable Income (slab)         ₹X,XX,XXX     ₹X,XX,XXX
Slab Tax                      ₹X,XX,XXX     ₹X,XX,XXX
(-) Rebate u/s 87A            ₹     XXX     ₹X,XX,XXX
(+) Capital Gains Tax         ₹X,XX,XXX     ₹X,XX,XXX
(+) Surcharge                 ₹     XXX     ₹     XXX
(+) Cess (4%)                 ₹     XXX     ₹     XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL TAX LIABILITY           ₹X,XX,XXX     ₹X,XX,XXX
(-) TDS Already Paid          ₹X,XX,XXX     ₹X,XX,XXX
(-) Advance Tax Paid          ₹     XXX     ₹     XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BALANCE (payable / refund)    ₹X,XX,XXX     ₹X,XX,XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDED                   [→ NEW / OLD saves ₹X,XXX]
```

### Step 7 — Regime decision

Print the recommendation with savings amount.

Ask: "Which tax regime do you want to file under? (old / new / recommended)"
- Use recommended if user types "recommended" or just presses Enter.

Save: `python -m scripts.utils.state_manager set regime_elected [old|new]`

Important notes to print:
- If old regime recommended: "Note: Opt for old regime declaration must be submitted to employer before year-end; if not done, you may still file under old regime but any TDS shortfall must be paid as self-assessment tax."
- If balance > 0: "You have a tax balance of ₹[X] to pay. Pay via Challan 280 at tin.tin.nsdl.com BEFORE filing the return. Save the BSR code and challan number."
- If balance < 0: "You will receive a refund of ₹[|X|]. Refunds are typically credited within 4-6 weeks of filing."

### Step 8 — Self-assessment tax (if balance due)

If tax balance > 0 AND filing.is_belated = false:
  Print: "TAX DUE: ₹[X]. You must pay this as Self-Assessment Tax (Challan 280, Code 300) before filing."
  Ask: "Have you already paid self-assessment tax? (yes / no)"
  If yes:
    Ask for: BSR code, date of payment, challan serial number, amount paid
    Save to self_assessment_tax_paid in state.
  If no:
    Print: "Please pay at: https://www.tin-nsdl.com or the portal's e-Pay Tax section."
    Print: "After payment, run /tax-compute again and enter the challan details."
    Stop here.

### Step 9 — Check for LTCG grandfathering

If income.capital_gains.equity_ltcg > 0:
  Ask: "Did you sell any listed equity shares/equity MF units that you originally purchased BEFORE January 31, 2018?"
  If yes:
    Print: "For those pre-2018 holdings, the cost of acquisition for LTCG is the HIGHER of:
      (a) your actual purchase price, OR
      (b) the fair market value (NAV) as on January 31, 2018
    but capped at the actual sale price.
    Please ensure your broker's P&L report has already applied this grandfathering.
    If not, you may need to compute adjusted LTCG and correct the broker figure using:
    /tax-status → set income.capital_gains.equity_ltcg [corrected_amount]"

### Step 10 — Save and checkpoint

Save computed results to state.tax_computation.
Run: `python -m scripts.utils.state_manager checkpoint --name "tax_computed" --description "Regime: [regime], Balance: [balance]"`

Print: "Tax computation complete. Next step: /tax-review"
