# Taxman — Indian ITR Filing with Claude Skills

A collection of Claude slash commands that guide an Indian resident through the
complete Income Tax Return filing workflow for any Assessment Year.

## Quick Start

```bash
# Let Claude handle everything (recommended):
/tax-setup

# Or run the installer directly if Python is already available:
python3 scripts/setup/setup.py
```

`/tax-setup` detects your OS (Ubuntu/Debian, Fedora, Arch, macOS, Windows),
creates `.venv/`, installs all packages, downloads Playwright Chromium, and
writes `.claude/settings.json` so the venv is active for every `/tax-*` skill
automatically — no `source .venv/bin/activate` needed.

## Workflow Overview

```
/tax-setup              → Install all tools (run once, re-run after OS change)
/tax-help               → Overview and next steps
/tax-init [AY]          → Start or resume a session (AY e.g. "2026-27")
/tax-status             → Check progress cheaply (~100 tokens)
/tax-parse <file>       → Parse a document (auto-detects type)
/tax-reconcile          → Flag 26AS vs Form-16 vs AIS discrepancies
/tax-compute            → Compute tax for old and new regime
/tax-review             → Final human review of all data
/tax-file               → Open portal with Playwright and fill ITR
/tax-update-rules <AY>  → Scaffold tax rules for a new Assessment Year
```

## Document Checklist by ITR Form

### ITR-1 (salary only, income < ₹50L, no foreign assets)
- Form 16 from each employer (Required)
- Form 26AS (Required)
- AIS / TIS (Required)
- Bank statements for interest income (Recommended)
- Investment proofs 80C/80D (Required if claiming deductions)

### ITR-2 (capital gains / foreign assets / multiple HP / income > ₹50L)
All of the above plus:
- Broker P&L report — Zerodha Console or Groww (Required if capital gains)
- Foreign asset details (Required if foreign assets)
- Home loan interest certificate (Required if housing property)
- Rent receipts / HRA documents (If claiming HRA)

## State File

All session data is stored in `state/session.json`. This file is gitignored.
Every skill reads from and writes to this file — you can safely start a new
Claude session and `/tax-status` will show exactly where you left off.

## Annual Rules Update

When a new Finance Budget is passed, run:
```
/tax-update-rules <new-AY>
```
This creates `scripts/calculators/rules/ay<YYYY><YY>.json` from the previous year
with a guided walkthrough to enter changed slabs, limits, and rates.

## Security

- `state/` and `documents/` are gitignored — sensitive data never leaves your machine
- Playwright runs in headed (visible) mode — you control the browser
- No credentials are stored; you handle login, OTP, and e-verification
- The tool never submits the ITR without your explicit typed confirmation

## Supported ITR Forms

| Form  | Who uses it                                     | Status   |
|-------|-------------------------------------------------|----------|
| ITR-1 | Salaried, income < ₹50L, no CG, no FA          | ✅ Full  |
| ITR-2 | CG / foreign assets / multiple HP / NRI         | ✅ Full  |
| ITR-3 | Business/profession income                      | 🚧 Stub  |
| ITR-4 | Presumptive taxation                            | 🚧 Stub  |

## Project Structure

```
.claude/commands/      ← Skill files (slash commands)
scripts/
  parsers/             ← Document parsers (Form 16, 26AS, AIS, broker, bank)
  calculators/         ← Tax computation, deductions, capital gains
    rules/             ← One JSON file per AY (ay2526.json, ay2627.json …)
  portal/              ← Playwright portal automation
  utils/               ← State manager, PDF utilities, validators
schemas/               ← JSON Schema for state and ITR data
tests/                 ← Unit tests (pytest)
state/                 ← Session data (gitignored)
documents/             ← User's tax documents (gitignored)
```

## Testing

The project uses [pytest](https://docs.pytest.org/) with 127 unit tests covering
calculators, validators, state management, and document routing.

### Running Tests

```bash
# Run the full suite
pytest

# With coverage report
pytest --cov=scripts

# Run a specific module
pytest tests/calculators/test_tax_calculator.py

# Run a single test class or method
pytest tests/calculators/test_tax_calculator.py::TestSlabTax
pytest tests/utils/test_validators.py::TestValidatePAN::test_valid
```

### Test Structure

```
tests/
  conftest.py                          ← Shared fixtures (AY rules, income/deduction templates, sample state)
  calculators/
    test_tax_calculator.py             ← Slab tax, rebate 87A, surcharge, cess, regime comparison
    test_deduction_calculator.py       ← HRA exemption (metro/non-metro), 80G deductions
    test_capital_gains_calc.py         ← CII indexation, equity LTCG grandfathering, property LTCG regime choice
    test_tax_rules.py                  ← Rule loading, missing AY, validation
  parsers/
    test_router.py                     ← Document type detection from filenames
  utils/
    test_state_manager.py              ← Init, load/save, get/set paths, checkpoints, backup
    test_validators.py                 ← PAN, IFSC, AY, DOB, mobile, amount, taxpayer category
```

### What's Tested

| Area | Tests | What's covered |
|------|-------|----------------|
| Tax calculator | 22 | Slab tax for old/new regime, rebate u/s 87A with marginal relief, surcharge with equity cap, cess, full regime computation, regime comparison |
| Deductions | 11 | HRA exemption (metro vs non-metro, zero rent, edge cases), 80G donation deductions |
| Capital gains | 14 | CII indexed cost, equity LTCG grandfathering (FMV cap, loss scenarios), property LTCG old-vs-new regime, broker P&L aggregation |
| Tax rules | 5 | Rule file loading, missing AY error, validation of required keys, listing available AYs |
| Validators | 20 | PAN format, IFSC format, AY format, DOB parsing (ISO + DD/MM/YYYY), mobile normalization, amount parsing, taxpayer category by age |
| State manager | 14 | Session init, load/save with atomic writes, nested get/set, checkpoints, document tracking, discrepancy logging, backup, progress summary |
| Parser router | 4 | Filename-based document type detection, hint override, case insensitivity |

### Writing New Tests

- Add test files under the matching `tests/` subdirectory (mirrors `scripts/`)
- Use fixtures from `conftest.py` — `ay2526_rules`, `minimal_income`, `zero_deductions`, `sample_state`
- For state manager tests, the `isolate_state` autouse fixture redirects all I/O to `tmp_path`
- Use `monkeypatch` to swap module-level constants (e.g. `RULES_DIR`, `STATE_PATH`)
- Use `pytest.mark.parametrize` for input/output variations

### Dependencies

Testing dependencies are included in `requirements.txt`:
- `pytest>=8.0.0`
- `pytest-cov>=5.0.0`

## Contributing

Taxman is an open project and contributions are welcome at every level of
experience. Here are the most impactful ways to help:

### 1. Test with Real-Life Data and Report Issues

The single most valuable contribution is running the workflow against **your own
tax documents** (Form 16, 26AS, AIS, broker P&L) and reporting what breaks.

- Run `/tax-init`, parse your documents with `/tax-parse`, and compare the
  extracted figures against the originals
- Run `/tax-compute` and cross-check the computed tax against the IT portal's
  pre-filled figures or a CA's computation
- Open an issue with:
  - Which step failed or produced wrong numbers
  - The AY and ITR form type
  - Expected vs actual values (redact sensitive details — PAN, name, exact salary)
  - Screenshots of the discrepancy if possible

**You don't need to write a single line of code** — just reporting "Form 16 parser
missed employer #2" or "LTCG exemption applied twice" saves everyone time.

### 2. Fix a Bug You Found and Raise a PR

If you found an issue in step 1 and want to fix it yourself:

- Fork the repo and create a branch from `main`
- Fix the parser, calculator, or validator that produced the wrong result
- Add or update a unit test that would have caught the bug
  (see [Writing New Tests](#writing-new-tests) above)
- Run `pytest` to make sure all 127+ tests pass
- Open a PR describing the bug, the root cause, and the fix

Even small fixes matter — an off-by-one in a slab boundary or a missed regex
pattern in the Form 16 parser can affect thousands of users.

### 3. Improve Parser and Calculator Coverage with Diverse Data

Different employers, banks, and brokers produce wildly different document
formats. Help us handle more of them:

- **Parsers**: Test with Form 16 PDFs from different employers (TCS, Infosys,
  startups, government), bank statements from various banks (SBI, HDFC, ICICI,
  Kotak), and broker reports from Zerodha, Groww, Upstox, Angel One, etc.
- **Calculators**: Test edge cases — senior citizen slabs, NRI taxation, large
  capital gains with surcharge, multiple house properties, carry-forward losses
- **Validators**: Try unusual but valid inputs — PANs with specific 4th-letter
  meanings, old-format IFSC codes, edge-case date formats

For each, add parametrized test cases in the relevant test file with anonymized
data so the test suite grows with real-world variety.

### 4. Expand ITR Form Support

ITR-3 (business income) and ITR-4 (presumptive taxation) are currently stubs.
If you file under these forms, you can help by:

- Documenting the additional fields and schedules these forms require
- Extending the calculator to handle business income, presumptive income
  (44AD/44ADA), or partnership income
- Adding portal automation steps in `scripts/portal/` for the new form flows

### 5. Improve Portal Automation

The Playwright-based portal filler (`scripts/portal/`) works with the current
IT portal layout, but the portal changes frequently. Contributions here include:

- Fixing broken selectors when the portal updates its UI
- Adding support for new schedules (Schedule FA, Schedule FSI, Schedule TR)
- Improving error recovery — what happens when the portal times out mid-fill

### 6. Add or Update Tax Rules for New Assessment Years

When the Finance Budget introduces new slabs, rates, or deduction limits:

- Run `/tax-update-rules <new-AY>` to scaffold the rules file
- Verify every field against the Finance Act / Budget documents
- Add golden tests in `test_tax_calculator.py` that validate known tax amounts
  for the new AY

### Getting Started as a Contributor

```bash
# Clone and set up
git clone https://github.com/meranamvarun/taxman.git
cd taxman
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Run tests to make sure everything works
pytest

# Start a session to explore the workflow
# (inside Claude Code)
/tax-init 2025-26
```

All sensitive data stays local — `state/` and `documents/` are gitignored, so
you can safely test with real documents without risk of committing them.
