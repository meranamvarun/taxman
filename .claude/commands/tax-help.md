# /tax-help — Taxman Overview

Display project overview, available commands, and prerequisites. Then check if a session exists and show current progress.

## Steps

1. Print the following overview:

```
TAXMAN — Indian Income Tax Filing Assistant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMMANDS
  /tax-init [AY]       Start or resume a session (e.g. /tax-init 2026-27)
  /tax-status          Check current progress (cheap, ~100 tokens)
  /tax-parse <file>    Parse a tax document (auto-detects type)
  /tax-reconcile       Flag mismatches between Form 16, 26AS, and AIS
  /tax-compute         Compute tax under old and new regime
  /tax-review          Final review of all data before filing
  /tax-file            Open portal and fill ITR with Playwright
  /tax-update-rules AY Create rules file for a new Assessment Year

DOCUMENT FOLDER
  Drop your documents here before parsing:
    documents/form16/        → Form 16 PDFs (one per employer)
    documents/form26as/      → Form 26AS PDF
    documents/ais/           → AIS / TIS PDF
    documents/banks/         → Bank statements (PDF or CSV)
    documents/brokers/       → Zerodha/Groww P&L CSV
    documents/investments/   → 80C/80D/80G proof PDFs
    documents/foreign_assets/→ Foreign account/asset details

PREREQUISITES
  pip install -r requirements.txt
  playwright install chromium
  (For scanned PDFs) sudo apt install tesseract-ocr
```

2. Check if `state/session.json` exists:
   - If it exists, run: `python -m scripts.utils.state_manager status`
   - Print the result in a readable table showing AY, name, documents parsed, and next step
   - If it does not exist, print: "No active session. Run /tax-init to begin."

3. Suggest the next action based on status.
