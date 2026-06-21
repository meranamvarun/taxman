# /tax-status — Check Progress

A lightweight skill (~150 tokens) that shows the current filing status. Safe to run at the start of any new session to orient yourself.

## Steps

1. Run: `python -m scripts.utils.state_manager status`
   If the command fails (no session), print: "No session found. Run /tax-init to start."

2. Display the result as a formatted status table:

```
SESSION STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AY          : [ay]
Taxpayer    : [name] ([pan])
ITR Form    : [itr_form]
Regime      : [regime_elected or "Not selected yet"]
Last Updated: [last_updated]

DOCUMENTS PARSED
  [✓] form16        → [parsed / ✗ not yet]
  [✓] form26as      → [parsed / ✗ not yet]
  [✓] ais           → [parsed / ✗ not yet]
  [✓] bank_statement→ [parsed / ✗ not yet]
  [✓] broker        → [parsed / ✗ not yet]
  [✓] investment    → [parsed / ✗ not yet]

CHECKPOINTS COMPLETED
  [list each checkpoint name and timestamp]

FILING STATUS: [not_started / in_progress / ready_to_file / submitted]

UNRESOLVED DISCREPANCIES: [count]

NEXT STEP: [suggest the next /tax-* command]
```

3. For the NEXT STEP suggestion:
   - No documents parsed → /tax-parse <first document>
   - Some documents missing → /tax-parse <next document>
   - All key documents parsed, no reconciliation done → /tax-reconcile
   - Reconciled but not computed → /tax-compute
   - Computed but not reviewed → /tax-review
   - Reviewed → /tax-file
   - Submitted → "Filing complete! Acknowledgement: [ack_number]"
