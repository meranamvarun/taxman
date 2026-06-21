# /tax-parse — Parse a Tax Document

$ARGUMENTS — file path relative to project root, e.g. "documents/form16/emp_form16.pdf"

Optionally: "documents/brokers/zerodha_pnl.csv --type broker --broker zerodha"

## Token note
Parsing a typical document uses 500–1500 tokens depending on PDF size.
If your Claude session is running low on context (you've been working for a long time),
save state first by running /tax-status, then start a new session and run /tax-parse again —
the state file will have everything needed.

## Steps

### Step 1 — Load state

Run: `python -m scripts.utils.state_manager status`
If it fails, ask user to run /tax-init first.

### Step 2 — Validate the file

Check that the file path from $ARGUMENTS exists. If not, print the contents of the
relevant documents/ subfolder so the user can see what's available:
- List files in documents/form16/, documents/form26as/, documents/ais/, documents/banks/, documents/brokers/, documents/investments/, documents/foreign_assets/

### Step 3 — Detect document type

Parse $ARGUMENTS to extract:
- file_path (first token)
- --type flag (if provided): form16 | form26as | ais | bank | broker | investment
- --bank flag (if provided): sbi | hdfc | icici | axis | auto
- --broker flag (if provided): zerodha | groww | auto
- --investment-type flag (if provided): ppf | lic | elss | nps | homeloan | health | eduloan | donation | nsc | auto

If no --type given, the router will auto-detect from filename.

### Step 4 — Run the parser

Run:
```
python -m scripts.parsers.router "[file_path]" [--type TYPE] [--bank BANK] [--broker BROKER] [--investment-type ITYPE]
```

Capture the JSON output.

### Step 5 — Check confidence

- If confidence is "low": Print all warnings. Ask the user: "Parser confidence is LOW. Do you want to enter this data manually? (yes / no / skip)"
  - "yes" → proceed to manual entry (Step 6)
  - "no" → continue with low-confidence data, flagged
  - "skip" → skip this document, do not update state

- If confidence is "medium": Show warnings, continue but flag for review in /tax-reconcile.

- If confidence is "high": Proceed.

### Step 6 — Show extracted data

Display the key extracted fields in a human-readable table. For each document type, show:

**form16:**
  Employer, TAN, Employee PAN, Period, Gross Salary, Standard Deduction, Total TDS, Taxable Salary

**form26as:**
  PAN, Total TDS (Part A), Total Advance Tax, TDS entries by deductor

**ais:**
  Salary, Interest (savings + FD), Dividend, Capital Gains (equity, property), Rent

**bank:**
  Bank detected, Savings interest, FD interest, Total interest

**broker:**
  Broker detected, Equity STCG, Equity LTCG, Debt STCG/LTCG, Total

**investment:**
  Category (80C/80D/80E/80G), Amount, Subcategory

Ask the user: "Does this look correct? (yes / correct [field] [value] / skip)"
- "yes" → proceed to Step 7
- "correct [field] [value]" → update the specified field in the parsed data, then re-ask
- "skip" → skip without saving

### Step 7 — Merge into state

Based on document type, merge the parsed data into the appropriate section of state.json.
Use `python -m scripts.utils.state_manager set [path] [value]` for each key field, or
directly update state/session.json for complex nested updates.

**Merge logic by type:**

**form16:** Add employer entry to income.salary.employers[]. Sum up total_tds.
  Multiple Form 16s → append, don't overwrite.
  Check if same employer already in list (by TAN) to avoid duplicates.

**form26as:** Store tds_credits list. Compare total_tds with form16 total_tds.
  If difference > ₹1000, flag as discrepancy.

**ais:** Update income.other_sources.savings_interest, fd_interest, dividend.
  If AIS salary differs from Form 16 gross by > ₹5000, flag discrepancy.

**bank:** Add savings_interest and fd_interest to income.other_sources.
  If form26as was already parsed, compare interest amounts — flag differences.

**broker:** Update income.capital_gains with the broker's P&L totals.
  Multiple broker files → sum the capital gains figures.

**investment:** Route by category:
  80C → deductions.80C (accumulate, will be capped in /tax-compute)
  80D → deductions.80D_self / deductions.80D_parents
  80E → deductions.80E
  80G → append to deductions.80G list
  NPS → deductions.80CCD1 / 80CCD1B / 80CCD2
  Home loan → deductions.80C (principal) + store interest separately for 24b

### Step 8 — Save checkpoint

Run: `python -m scripts.utils.state_manager checkpoint --name "parsed_[doctype]_[filename]" --description "..."`

Print summary: "Parsed [doc_type] successfully. [key stats]. Run /tax-parse [next file] or /tax-status to see progress."

### Step 9 — Foreign assets handling

If the file is in documents/foreign_assets/, ask the user to provide:
  - Asset type (bank account / equity / property / other)
  - Country
  - Asset details (see state.foreign_assets schema)

Collect interactively and save to state.foreign_assets using state_manager set commands.

Print: "Foreign asset added. Note: Schedule FA on the portal will need to be filled manually during /tax-file — this data will be used as a reference."
