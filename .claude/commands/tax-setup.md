# /tax-setup — Install All Required Tools

$ARGUMENTS — optional flags passed through to setup.py:
  --check            Check what's installed without installing anything
  --skip-tesseract   Skip Tesseract OCR (only needed for scanned PDFs)
  --skip-browser     Skip Playwright browser download (install later)

Detects the operating system and installs everything needed to run taxman:
Python packages, Playwright Chromium browser, and optionally Tesseract OCR.
Also configures .claude/settings.json so the venv is used automatically
by all /tax-* skill files without manual activation.

## What gets installed

| Tool | Why | Required |
|------|-----|----------|
| Python 3.11+ | Run all scripts | Yes |
| .venv/ (virtualenv) | Isolate packages | Yes |
| pdfplumber | Extract text from PDFs | Yes |
| Pillow + pytesseract | OCR for scanned PDFs | Yes |
| openpyxl + pandas | Parse Excel/CSV broker reports | Yes |
| playwright | Browser automation for portal | Yes |
| rich + jsonschema | Terminal output + validation | Yes |
| Playwright Chromium | Browser for ITR portal | Yes |
| Tesseract OCR binary | Scanned Form 16 / 26AS | Optional |

## Steps

### Step 0 — Show detected OS info

First, check what's already installed:

Run: `python3 scripts/setup/verify.py 2>/dev/null || python scripts/setup/verify.py`

If exit code is 0, print: "Everything is already installed. Run /tax-help to start filing."
and stop here.

If exit code is 2, print: "Required tools are installed. Only Tesseract OCR is missing (optional)."
Ask: "Do you still want to run setup? (y/N)"

Otherwise, continue to Step 1.

### Step 1 — Run the setup script

Run the setup script passing through any $ARGUMENTS:

```
python3 scripts/setup/setup.py $ARGUMENTS
```

If python3 is not found, try:
```
python scripts/setup/setup.py $ARGUMENTS
```

If neither works, print:
```
Python 3 is not installed or not in your PATH.

Please install Python 3.11+ for your operating system:

  Ubuntu / Debian:   sudo apt install python3.11 python3.11-venv
  Fedora / RHEL:     sudo dnf install python3.11
  Arch Linux:        sudo pacman -S python
  macOS:             brew install python@3.11  (requires Homebrew: https://brew.sh)
  Windows:           https://www.python.org/downloads/
                     ← check "Add Python to PATH" during install

After installing Python, re-run /tax-setup.
```

### Step 2 — Handle setup output

The setup script runs interactively and prints its own status.
Watch for and handle these prompts from the script:
- "Install Tesseract now? (y/N):" — echo through to the user
- Any sudo password prompts — those go directly to the terminal

### Step 3 — Verify final state

After setup.py completes, run the verifier to confirm everything works:

```
.venv/bin/python scripts/setup/verify.py
```

If verification fails, read the error output and suggest the specific fix.

Common issues and fixes:

**Playwright browser download failed** (network/timeout):
  Print: "Playwright browser failed. Install it manually:"
  ```
  .venv/bin/python -m playwright install chromium
  ```

**apt requires sudo but user has no sudo**:
  Print: "System package install requires sudo. Ask your admin to run:"
  For Ubuntu/Debian: `sudo apt install python3.11 python3.11-venv tesseract-ocr`
  For Fedora: `sudo dnf install python3.11 tesseract`

**Windows — winget / choco not found**:
  Print instructions to install Python from python.org manually, then re-run.

**macOS — brew not found**:
  Print: "Homebrew is required on macOS. Install it:"
  ```
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
  Then re-run /tax-setup.

**pip install fails with "externally managed environment"**:
  This should not happen since setup.py uses a venv, but if it does:
  Print: "This indicates setup.py ran pip outside the venv. Please report this issue."
  Workaround: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

### Step 4 — Confirm .claude/settings.json

After successful setup, check that .claude/settings.json was written correctly:

Read `.claude/settings.json` and confirm:
- `env.PATH` starts with the absolute path to `.venv/bin` (Linux/macOS) or `.venv\Scripts` (Windows)

Print:
```
.claude/settings.json configured — the venv is now active for all /tax-* commands.
You do NOT need to run 'source .venv/bin/activate' manually.
```

If the settings file was NOT written (e.g. setup failed before Step 7), do it manually:
Read the venv python path from the output, then update .claude/settings.json:
```json
{
  "env": {
    "PATH": "/absolute/path/to/.venv/bin:/usr/local/bin:/usr/bin:/bin"
  }
}
```

### Step 5 — Platform-specific notes

**Linux (Fedora/RHEL):**
  If Playwright install-deps fails due to missing packages, the user may need:
  `sudo dnf install libX11 libXcomposite libXdamage libXfixes libXrandr nss`

**macOS (Apple Silicon M1/M2/M3):**
  If Playwright Chromium fails to launch, the user may need Rosetta:
  `softwareupdate --install-rosetta`

**Windows:**
  - Playwright must be installed with admin rights for system deps
  - Path separator is `\` not `/` — setup.py handles this automatically
  - Windows Defender may flag Chromium download — allow it
  - If venv creation fails, check execution policy:
    `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Step 6 — Final success message

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TAXMAN SETUP COMPLETE

Your environment is ready. Start with:
  /tax-help             Show overview and next steps
  /tax-init 2026-27     Begin a new filing session
  /tax-status           Check an existing session

To verify setup later:  python scripts/setup/verify.py
To re-run setup:        /tax-setup
To add new AY rules:    /tax-update-rules 2027-28
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
