# /tax-reconcile — Reconcile Income & TDS Figures

Compares Form 16 vs Form 26AS vs AIS and flags discrepancies that must be resolved before filing.

## Token note
This skill uses ~600 tokens. Run after all documents have been parsed.

## Steps

### Step 1 — Load state

Run: `python -m scripts.utils.state_manager status`
Check that at least form16 and form26as (or ais) have been parsed.
If neither has been parsed, print: "Please run /tax-parse on your Form 16 and Form 26AS first."

### Step 2 — Extract figures from state

Read state/session.json and extract:
- form16_salary_tds = sum of total_tds_deducted across all employers in income.salary.employers
- form16_gross_salary = sum of gross_salary across all employers
- form26as_total_tds = sum of tds_deducted in tds_credits
- ais_salary = income from AIS (if parsed)
- ais_savings_interest, ais_fd_interest = from AIS
- bank_savings_interest, bank_fd_interest = from bank statements (if parsed)

### Step 3 — TDS Reconciliation

Compare form16_salary_tds vs form26as_total_tds:

If difference > ₹500:
  Print: "⚠ TDS MISMATCH: Form 16 shows ₹[X] but Form 26AS shows ₹[Y] — difference: ₹[Z]"
  Ask user: "Which figure is correct? Form 16 / Form 26AS / Enter correct amount"
  - "Form 26AS" is generally preferred (it's what the IT dept sees)
  - Save resolved value to state

If deductor in Form 26AS doesn't match any employer TAN in Form 16:
  Flag: "TDS from [deductor] appears in 26AS but not in any Form 16. Is this a previous employer?"

### Step 4 — Salary reconciliation

Compare form16_gross_salary vs ais_salary (if AIS parsed):
If difference > ₹10000:
  Print: "⚠ SALARY MISMATCH: Form 16 shows ₹[X], AIS shows ₹[Y]"
  Explanation: "Discrepancies can occur if employer reported differently, or if perquisites are counted differently."
  Ask: "Which salary figure should we use? Form 16 / AIS / Manual entry"

### Step 5 — Interest income reconciliation

If both bank statements and AIS/26AS interest data exist:

Compare bank_savings_interest vs ais_savings_interest:
If difference > ₹500: flag discrepancy

Compare bank_fd_interest vs form26as TDS entries for interest (TAN starting with banks):
If significant difference: flag

For each flagged discrepancy: ask user which figure to use. Common advice:
- Use the HIGHER figure (more conservative) to avoid underreporting
- 26AS/AIS figures are what IT dept has; use those as minimum baseline

### Step 6 — Capital gains cross-check

If broker P&L was parsed AND AIS capital gains data exists:
  Compare equity STCG from broker vs AIS capital gains equity
  If difference > ₹1000: flag
  Explanation: "Broker P&L is usually accurate. AIS may include all transactions including those not yet settled."

### Step 7 — Dividend reconciliation

If AIS dividend figure exists vs income.other_sources.dividend in state:
If not already populated from AIS: update income.other_sources.dividend with AIS figure.
Flag if manually entered dividend differs significantly from AIS.

### Step 8 — Prior year losses prompt

If income.capital_gains has any equity_stcg or other_stcg > 0:
  Ask: "Do you have any brought-forward capital losses from previous years?"
  If yes:
    Ask for: equity STCL, other STCL, other LTCL amounts
    Save to prior_year_losses in state
    Print: "Carried-forward losses noted. They will be applied in /tax-compute."

  Note: If filing.is_belated = true, warn: "Belated returns cannot carry forward capital losses."

### Step 9 — 80C employer vs own contributions

Check if form16 part_b deductions_by_employer.80C > 0.
If so, check if deductions.80C in state is already counting those amounts.
Warn if double-counting detected.

### Step 10 — Check for u/s 89 (arrears)

Scan form16 gross salary for any notes about arrears.
Ask: "Did you receive any salary arrears in this year that relate to a previous financial year?"
If yes: "You may be eligible for relief u/s 89. Please file Form 10E on the income tax portal BEFORE submitting your ITR. Failure to file Form 10E before ITR submission will result in disallowance."
Flag in state: `python -m scripts.utils.state_manager set filing.requires_form_10e true`

### Step 11 — Save all resolved discrepancies

For each discrepancy found, run:
```
python -m scripts.utils.state_manager set discrepancies [updated-list-json]
```

Run: `python -m scripts.utils.state_manager checkpoint --name "reconciliation_done"`

### Step 12 — Summary

Print reconciliation report:
- Total discrepancies found: N
- Resolved: N
- Unresolved: N (if any, name them)
- Income figures confirmed for ITR:
  - Salary: ₹[X]
  - Other Sources: ₹[Y]
  - Capital Gains: ₹[Z]

If unresolved discrepancies remain, advise user before proceeding.
Next step: /tax-compute
