# /tax-update-rules — Create Tax Rules for a New Assessment Year

$ARGUMENTS — New Assessment Year, e.g. "2027-28"

Run this every year after the Finance Budget is passed (typically in February).
It creates a new rules file by walking you through changes from the previous year.

## Token note
This skill uses ~300 tokens plus however long the interactive session takes.

## Steps

### Step 1 — Validate argument

If $ARGUMENTS is empty, ask: "Which Assessment Year do you want to create rules for? (e.g. 2027-28)"

Validate AY format. Must be YYYY-YY where end year = start year + 1.

### Step 2 — Check existing rules

Run: `python -m scripts.calculators.tax_rules` to list available AYs:
```python
from scripts.calculators import tax_rules
print(tax_rules.list_available())
```

If rules for $ARGUMENTS already exist, ask:
"Rules for [AY] already exist. Do you want to overwrite them? (yes / no)"
If no, stop.

### Step 3 — Gather budget changes

Before running the interactive update script, ask the user to paste or describe
the key changes from the new Finance Budget:

"Please describe the key tax changes from the new budget. For example:
  - New regime slabs changed (describe new slab structure)
  - Standard deduction changed to ₹X
  - Rebate 87A threshold/amount changed
  - Capital gains rates changed
  - Deduction limits changed (80C, 80D, etc.)
  - Surcharge changes
  - Any new sections added/removed

You can paste text from news articles or the budget speech. I will extract the changes."

Extract structured changes from the user's description.

### Step 4 — Run the update script

Run:
```
python -m scripts.update_rules [AY]
```

This will run an interactive prompt for each tax parameter. Guide the user through
each prompt, pre-filling answers from the changes extracted in Step 3.

### Step 5 — Verify the new rules file

After the script completes, read the new file:
```
cat scripts/calculators/rules/ay[YYYY][YY].json
```

Display a diff summary vs the previous year's file, highlighting changes:
- Changed slabs (show old vs new)
- Changed limits (show old vs new amounts)
- Changed rates (show old vs new %)

Ask: "Does this look correct? (yes / fix [field] [value])"

If fix: update the specific field and re-display.

### Step 6 — Test with a sample computation

Run a quick test computation with sample numbers:
- Income: ₹10,00,000 salary, no deductions, new regime
- Expected: show tax computed under new rules

Print the result and ask: "Does this tax amount match what you'd expect for ₹10L income under the new AY?"

### Step 7 — Checkpoint

Print:
"Tax rules for AY [AY] created and saved.
File: scripts/calculators/rules/ay[YYYY][YY].json

You can now use this for new filings with /tax-init [AY].
If you find any errors, edit the JSON file directly or re-run /tax-update-rules [AY]."
