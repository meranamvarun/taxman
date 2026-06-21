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
