# /tax-file — Fill and Submit ITR via Portal

Launches Playwright, navigates to the Income Tax Portal, and fills all ITR sections.
All authentication, OTPs, and the final SUBMIT are done by the human.

$ARGUMENTS — optional: "--resume" to pick up from a paused portal session

## CRITICAL — Read before starting

- This opens a REAL browser connected to the LIVE income tax portal
- You (the human) must log in with your credentials and OTP
- All data entry is automated but you VERIFY each section before continuing
- The SUBMIT button is NOT clicked by automation — you must do it
- E-verification after submission is done by you
- Keep this session open until complete — do not start other heavy tasks
- The portal may time out after 15-20 minutes of inactivity
- Screenshots are saved to screenshots/ for your records

## Steps

### Step 1 — Pre-flight checks

Run: `python -m scripts.utils.state_manager status`

Verify:
- filing.status = "ready_to_file"
- regime_elected is set
- itr_form is set

If any check fails, print the issue and stop. User must run /tax-review first.

If filing.status = "submitted", print acknowledgement number and stop.

Read state/session.json.

### Step 2 — Install Playwright if needed

Run: `python -c "from playwright.sync_api import sync_playwright; print('OK')" 2>/dev/null || playwright install chromium`

### Step 3 — Launch portal

Run: `python -m scripts.portal.session` — but instead of running this as a script,
invoke the appropriate filler directly:

For ITR-1:
```
python -m scripts.portal.itr1_filler --state state/session.json
```

For ITR-2:
```
python -m scripts.portal.itr2_filler --state state/session.json
```

The filler will:
1. Launch a visible browser
2. Open incometax.gov.in
3. PAUSE — wait for you to log in with OTP

Inform the user: "A browser window is opening. Please log in to the Income Tax Portal.
Use your PAN + password, Aadhaar OTP, or Net Banking.
Press Enter in this terminal after you see your dashboard."

### Step 4 — Monitor the session

The filler script handles all human pauses internally. For each section, it will:
- Fill data automatically
- Print what was filled
- Show a PAUSE message in the terminal
- Wait for you to verify on screen and press Enter

Your job at each pause:
1. Look at the browser — does the filled data match your expected values?
2. If yes: press Enter in the terminal
3. If no: correct the field directly on the portal, then press Enter

### Step 5 — Final submission (YOU DO THIS)

After all sections are filled, the filler will pause with:
"ALL SECTIONS FILLED. Please review the ITR preview on the portal.
Download the ITR PDF and verify:
  - Name, PAN, Address
  - All income figures
  - All deduction amounts
  - Tax payable / refund amount
  - Bank account for refund

When satisfied, CLICK SUBMIT on the portal yourself.
After submission, the portal will show an acknowledgement number.
Enter it here: "

Wait for user to enter acknowledgement number.

Save: `python -m scripts.utils.state_manager set filing.ack_number "[ACK]"`
Save: `python -m scripts.utils.state_manager set filing.status submitted`
Save: `python -m scripts.utils.state_manager set filing.submitted_at "[ISO_TIMESTAMP]"`
Run: `python -m scripts.utils.state_manager checkpoint --name "itr_submitted" --description "Ack: [ACK]"`

### Step 6 — E-Verification reminder

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ITR SUBMITTED SUCCESSFULLY
Acknowledgement Number: [ACK]

IMPORTANT — E-VERIFY YOUR RETURN WITHIN 30 DAYS

You must e-verify to complete the filing. Choose any one method:
  1. Aadhaar OTP (fastest — available on portal now)
  2. EVC via Net Banking
  3. EVC via Bank Account / Demat
  4. Digital Signature Certificate (DSC)
  5. Send signed ITR-V to CPC Bengaluru by speed post (last resort)

On the portal: go to e-File → Income Tax Returns → e-Verify Return

Without e-verification, your return is INVALID.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 7 — Session timeout recovery (if applicable)

If during the filing process the portal redirects to the login page:
  The filler script will detect this and print:
  "SESSION TIMED OUT — Please log in again. Press Enter when dashboard is visible."
  You log in again; automation resumes where it left off.

### Error handling

If the portal shows a validation error:
  The filler will take a screenshot and print the error text.
  Common errors and fixes:
  - "Duplicate filing": Check if return was already submitted. Run /tax-status.
  - "Invalid bank account": Verify IFSC and account number. Use `python -m scripts.utils.state_manager set taxpayer.bank.ifsc [IFSC]`
  - "TDS mismatch": Reconcile with Form 26AS. Run /tax-reconcile again.
  - "Income mismatch": Check the specific field mentioned and correct via /tax-status set.
