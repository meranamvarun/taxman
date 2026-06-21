# /tax-init — Initialize or Resume a Tax Filing Session

$ARGUMENTS — optional Assessment Year, e.g. "2026-27"

## Token note
This skill uses ~500 tokens. If your session is already low on context, save state first with /tax-status.

## Steps

### Step 1 — Check for existing session

Run: `python -m scripts.utils.state_manager status`

- If the command succeeds (session exists), ask the user:
  "A session exists for [AY] ([taxpayer name]). Do you want to resume it or start fresh? (resume / fresh)"
  - If "resume": print the progress summary and stop here — user should run /tax-status for next step.
  - If "fresh": run `python -m scripts.utils.state_manager backup` to back up existing state, then continue.

### Step 2 — Collect taxpayer information

Ask the user for the following (all required unless marked optional):

1. Assessment Year — use $ARGUMENTS if provided, else ask. Validate format YYYY-YY (e.g. 2026-27).
   Run `python -m scripts.calculators.tax_rules` to confirm rules file exists for this AY.
   If no rules file exists, inform the user to run `/tax-update-rules [AY]` first.

2. Full name (as on PAN card)

3. PAN number — validate format (5 letters + 4 digits + 1 letter, all uppercase)

4. Date of birth (DD/MM/YYYY) — determines senior/super-senior citizen status

5. Residential status:
   - Resident (RNOR also counts here for most purposes)
   - NRI
   If NRI: warn that some deductions are not available and DTAA relief may apply.

6. Mobile number registered with Income Tax Dept

7. Email registered with Income Tax Dept

8. Primary bank account number and IFSC (for refund)

### Step 3 — Determine income sources

Ask the user the following questions. Based on answers, determine the ITR form.

a) How many employers did you have this financial year? (0 / 1 / 2+)
b) Did you sell any stocks, mutual funds, or property this year? (yes/no)
c) Do you have any foreign bank accounts, investments, or property? (yes/no)
d) Do you have rental income or housing loan interest deduction to claim? (yes/no)
e) Any other income — freelance, interest, dividends, gifts? (yes/no)
f) Is this a REVISED return? (yes/no) — if yes, ask for original acknowledgement number
g) Are you filing AFTER the due date (July 31)? (yes/no) — note this means belated return u/s 139(4); capital losses cannot be carried forward

**ITR Form selection logic:**
- Foreign assets OR foreign income → ITR-2 (mandatory)
- Capital gains (stocks, MF, property) → ITR-2
- Multiple house properties → ITR-2
- Housing property loss > ₹2L to carry forward → ITR-2
- Income > ₹50L (likely based on answers) → ITR-2
- Only salary income < ₹50L, no capital gains, no foreign assets → ITR-1
- When in doubt → ITR-2 (always safer)

Print the determined form and explain why.

### Step 4 — Initialize state

Run:
```
python -m scripts.utils.state_manager init \
  --ay "[AY]" \
  --pan "[PAN]" \
  --name "[NAME]" \
  --dob "[DOB-ISO]" \
  --mobile "[MOBILE]" \
  --email "[EMAIL]" \
  --residential-status "[resident|nri]" \
  --itr-form "[ITR-1|ITR-2]"
```

Then manually set additional fields using:
```
python -m scripts.utils.state_manager set taxpayer.bank.account_number "[ACCOUNT]"
python -m scripts.utils.state_manager set taxpayer.bank.ifsc "[IFSC]"
python -m scripts.utils.state_manager set filing.is_revised [true|false]
python -m scripts.utils.state_manager set filing.is_belated [true|false]
```
If revised, also: `python -m scripts.utils.state_manager set filing.original_ack "[ACK_NUMBER]"`

### Step 5 — Create document folders

Run:
```
mkdir -p documents/form16 documents/form26as documents/ais documents/banks documents/brokers documents/investments documents/foreign_assets
```

### Step 6 — Print document checklist

Based on the ITR form and income sources selected, print a formatted checklist:

**Required:**
- [ ] Form 16 (from each employer) → documents/form16/
- [ ] Form 26AS → documents/form26as/  (download from incometax.gov.in → e-File → View 26AS)
- [ ] AIS (Annual Information Statement) → documents/ais/ (download from portal → e-File → AIS)

**Required if applicable:**
- [ ] Broker P&L report → documents/brokers/ [if capital gains]
  - Zerodha: console.zerodha.com → P&L → Download as CSV
  - Groww: groww.in → Reports → P&L → Download
- [ ] Bank statements → documents/banks/ [for interest income]
  - Download as PDF or CSV from your bank's net banking
- [ ] Investment proofs → documents/investments/ [for deductions]
  - PPF passbook / statement
  - LIC premium receipt
  - ELSS / MF statements
  - Home loan interest + principal certificate
  - Health insurance premium receipt
  - NPS statement
- [ ] Foreign asset details → documents/foreign_assets/ [if foreign assets]
  - Foreign bank account statements
  - Foreign investment statements

### Step 7 — Save checkpoint

Run: `python -m scripts.utils.state_manager checkpoint --name "session_initialized" --description "Taxpayer info collected, ITR form determined"`

Print: "Session initialized. Next step: drop documents in the folders above and run /tax-parse <filename>"
