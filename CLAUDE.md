# Taxman — Indian ITR Filing with Claude Skills

A collection of Claude slash commands that guide an Indian resident through the complete
Income Tax Return filing workflow for any Assessment Year.

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
| ITR-2 | CG / foreign assets / multiple HP / NRI        | ✅ Full  |
| ITR-3 | Business/profession income                     | 🚧 Stub  |
| ITR-4 | Presumptive taxation                           | 🚧 Stub  |

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
state/                 ← Session data (gitignored)
documents/             ← User's tax documents (gitignored)
```
