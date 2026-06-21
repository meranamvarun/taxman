# /tax-review — Final Human Review Before Filing

Presents a complete, human-readable ITR draft and allows corrections before locking the state for filing.

## Token note
This skill uses ~400 tokens. Run after /tax-compute.

## Steps

### Step 1 — Load state

Run: `python -m scripts.utils.state_manager status`
Verify filing_status is not already "submitted". If submitted, print ack number and stop.

Read state/session.json fully.

### Step 2 — Print complete ITR draft

Display all sections that will be filed:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ITR DRAFT — [ITR-1/ITR-2] — AY [AY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERSONAL INFORMATION
  Name              : [name]
  PAN               : [pan]
  Date of Birth     : [dob]
  Mobile            : [mobile]
  Email             : [email]
  Residential Status: [status]
  Bank Account      : [account] ([bank]) IFSC: [ifsc]
  Filing Type       : [Original / Revised (Ack: [original_ack])]
                      [On time / Belated u/s 139(4)]
  Tax Regime        : [OLD / NEW]

INCOME DETAILS
  A. Salary Income
     [For each employer:]
     Employer: [name] (TAN: [tan])
     Gross Salary      : ₹[X]
     Standard Deduction: ₹[std_ded]
     Professional Tax  : ₹[prof_tax]
     Net Salary        : ₹[net]

  B. House Property
     [For each property or "None"]
     Annual Lettable Value: ₹[X]
     Less: Municipal Tax  : ₹[X]
     Net Annual Value     : ₹[X]
     Less: 30% std ded    : ₹[X]
     Less: Interest (24b) : ₹[X]
     HP Income/(Loss)     : ₹[X]

  C. Capital Gains                    [ITR-2 only]
     Equity STCG (20%)   : ₹[X]
     Equity LTCG (12.5%) : ₹[X]  [before ₹1.25L exemption]
     Other STCG (slab)   : ₹[X]
     Property LTCG       : ₹[X]
     VDA (30%)           : ₹[X]
     Net Capital Gains   : ₹[X]

  D. Other Sources
     Savings Interest    : ₹[X]
     FD Interest         : ₹[X]
     Dividend            : ₹[X]
     Other               : ₹[X]

  E. Foreign Source Income            [ITR-2 only]
     [details or "None"]

  GROSS TOTAL INCOME : ₹[X]

DEDUCTIONS (CHAPTER VI-A)             [Old regime only; New regime: only 80CCD2]
  80C (PPF/ELSS/LIC/etc.)  : ₹[X] [capped at ₹1,50,000]
  80CCD1B (NPS voluntary)  : ₹[X] [capped at ₹50,000]
  80CCD2 (employer NPS)    : ₹[X]
  80D (health insurance)   : ₹[X] [self: ₹X, parents: ₹X]
  80E (education loan)     : ₹[X]
  80G (donations)          : ₹[X]
  80TTA/TTB (int. on SB)   : ₹[X]
  HRA Exemption            : ₹[X]
  TOTAL DEDUCTIONS         : ₹[X]

TAX COMPUTATION
  Taxable Income    : ₹[X]
  Slab Tax          : ₹[X]
  Rebate u/s 87A    : ₹[X]
  Capital Gains Tax : ₹[X]
  Surcharge         : ₹[X]
  Cess (4%)         : ₹[X]
  TOTAL TAX         : ₹[X]

TAX PAID
  TDS (salary)      : ₹[X]
  TDS (other)       : ₹[X]
  Advance Tax       : ₹[X]
  Self-Assessment   : ₹[X]
  TOTAL PAID        : ₹[X]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[REFUND DUE: ₹X] or [TAX PAYABLE: ₹X]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOREIGN ASSETS (Schedule FA)         [ITR-2 only, if applicable]
  Foreign Bank Accounts: [count] accounts in [countries]
  Foreign Investments  : [count]
  [Details will be filled manually on portal]
```

### Step 3 — Allow corrections

Ask: "Do you want to correct any value before filing? (yes / no)"

If yes:
  Ask: "Which field? (e.g. 'income.capital_gains.equity_stcg', 'deductions.80C', or describe it)"
  Ask: "New value: ₹"
  Run: `python -m scripts.utils.state_manager set [path] [value]`
  Print: "Updated. Run /tax-compute again to refresh tax calculation if this changes your tax liability."
  Ask again: "Any other corrections? (yes / no)"

Repeat until no more corrections.

### Step 4 — Pre-filing checklist

Print this checklist and ask user to confirm each:

```
PRE-FILING CHECKLIST
Please confirm each item:

[ ] 1. All Form 16s have been parsed (one per employer)
[ ] 2. Form 26AS has been verified — TDS figures match
[ ] 3. AIS has been checked for any unreported income
[ ] 4. Bank interest income is included
[ ] 5. All capital gains have been declared (check broker P&L)
[ ] 6. All deduction proofs are available (80C/80D receipts)
[ ] 7. Bank account details for refund are correct
[ ] 8. Tax regime selection is confirmed: [OLD/NEW]
[ ] 9. If balance tax due: Self-assessment tax has been paid (Challan 280)
[ ] 10. If Form 10E required: Filed before this ITR [mark N/A if not applicable]
[ ] 11. Foreign assets are accurately listed [mark N/A if none]
```

Ask: "Are all items confirmed? (yes / no)"
If no: ask which item needs attention and help resolve it.

### Step 5 — Lock state for filing

Run: `python -m scripts.utils.state_manager set filing.status ready_to_file`
Run: `python -m scripts.utils.state_manager checkpoint --name "review_complete" --description "ITR draft approved for filing"`

Print:
"Review complete. State locked for filing.
Next step: Run /tax-file to open the Income Tax Portal with Playwright and fill your ITR.
Remember:
  • YOU will handle login and OTP
  • YOU will do the final submit
  • YOU will e-verify after submission"
