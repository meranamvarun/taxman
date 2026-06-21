"""
Taxman setup — installs all required tools for the current OS.

Handles:
  - Ubuntu/Debian  (apt)
  - Fedora/RHEL    (dnf)
  - Arch Linux     (pacman)
  - macOS          (brew)
  - Windows        (winget / choco / manual)

Steps:
  1. Detect OS + package manager
  2. Check / install Python 3.11+
  3. Create .venv/ virtual environment
  4. Install pip packages from requirements.txt into venv
  5. Install Playwright Chromium browser
  6. Check / install Tesseract OCR (optional)
  7. Write .claude/settings.json to inject venv into PATH for all skill files
  8. Print activation summary

CLI:
  python scripts/setup/setup.py            # Full install
  python scripts/setup/setup.py --check    # Check only, no installs
  python scripts/setup/setup.py --skip-tesseract
  python scripts/setup/setup.py --skip-browser
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
VENV_DIR = PROJECT_ROOT / ".venv"
CLAUDE_SETTINGS = PROJECT_ROOT / ".claude" / "settings.json"


# ── Colour helpers (no external deps at setup time) ──────────────────────────

def _c(code: str, text: str) -> str:
    if os.name == "nt":
        return text
    return f"\033[{code}m{text}\033[0m"


def ok(msg: str)   -> None: print(_c("32", f"  ✓ {msg}"))
def warn(msg: str) -> None: print(_c("33", f"  ⚠ {msg}"))
def err(msg: str)  -> None: print(_c("31", f"  ✗ {msg}"))
def hdr(msg: str)  -> None: print(_c("1;36", f"\n{msg}"))
def info(msg: str) -> None: print(f"    {msg}")


# ── Subprocess helpers ────────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    kwargs: dict = {"check": check}
    if capture:
        kwargs.update(capture_output=True, text=True)
    return subprocess.run(cmd, **kwargs)


def _sudo(cmd: list[str]) -> None:
    """Run a command with sudo; no-op if already root."""
    full = (["sudo"] + cmd) if os.geteuid() != 0 else cmd
    print(f"    Running: {' '.join(full)}")
    _run(full)


# ── Step 1: OS Detection ──────────────────────────────────────────────────────

def detect_os() -> dict:
    from scripts.setup.detect import detect
    env = detect(PROJECT_ROOT)
    return env


# ── Step 2: Python check / install ───────────────────────────────────────────

def ensure_python(env, check_only: bool) -> str:
    hdr("Step 2 — Python 3.11+")

    if env.python_ok:
        ok(f"Python {env.python_version} found at '{env.python_cmd}'")
        return env.python_cmd

    warn(f"Python 3.11+ not found (found: '{env.python_version or 'nothing'}').")

    if check_only:
        err("Install Python 3.11+ for your OS and re-run /tax-setup.")
        return ""

    install_cmds = {
        "apt":    ["apt-get", "install", "-y", "python3.11", "python3.11-venv", "python3-pip"],
        "dnf":    ["dnf", "install", "-y", "python3.11"],
        "pacman": ["pacman", "-S", "--noconfirm", "python"],
        "brew":   ["brew", "install", "python@3.11"],
    }

    cmd = install_cmds.get(env.pkg_manager)
    if cmd:
        info(f"Installing Python via {env.pkg_manager}...")
        _sudo(cmd)
        ok("Python installed.")
        return "python3.11" if env.pkg_manager != "brew" else "python3"
    else:
        _python_manual_instructions(env)
        sys.exit(1)


def _python_manual_instructions(env) -> None:
    err("Cannot auto-install Python on your system.")
    if env.system == "windows":
        info("Download Python 3.11+ from: https://www.python.org/downloads/")
        info("During install, check 'Add Python to PATH'.")
    elif env.system == "macos":
        info("Install Homebrew first: https://brew.sh")
        info("Then run: brew install python@3.11")
    else:
        info(f"Install python3.11 and python3.11-venv using your distro's package manager.")
    info("After installing Python, re-run /tax-setup.")


# ── Step 3: Virtual environment ───────────────────────────────────────────────

def create_venv(python_cmd: str, check_only: bool) -> Path:
    hdr("Step 3 — Virtual environment (.venv/)")

    if env_is_windows():
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    if VENV_DIR.exists() and venv_python.exists():
        ok(f"Virtual environment exists at .venv/")
        return venv_python

    if check_only:
        warn(".venv/ not found.")
        return venv_python

    info(f"Creating .venv/ with '{python_cmd} -m venv' ...")
    _run([python_cmd, "-m", "venv", str(VENV_DIR)])
    ok("Virtual environment created.")
    return venv_python


def env_is_windows() -> bool:
    return os.name == "nt"


# ── Step 4: Pip packages ──────────────────────────────────────────────────────

def install_pip_packages(venv_python: Path, check_only: bool) -> None:
    hdr("Step 4 — Python packages (requirements.txt)")

    r = subprocess.run(
        [str(venv_python), "-c", "import pdfplumber, playwright, rich, pandas, jsonschema; print('ok')"],
        capture_output=True, text=True
    )

    if r.returncode == 0 and r.stdout.strip() == "ok":
        ok("All pip packages already installed.")
        return

    if check_only:
        warn("Some packages missing. Run /tax-setup to install.")
        return

    venv_pip = venv_python.parent / ("pip.exe" if env_is_windows() else "pip")

    info("Upgrading pip ...")
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])

    info(f"Installing packages from requirements.txt ...")
    _run([str(venv_pip), "install", "-r", str(REQUIREMENTS), "--quiet"])
    ok("All pip packages installed.")


# ── Step 5: Playwright browser ────────────────────────────────────────────────

def install_playwright_browser(venv_python: Path, check_only: bool) -> None:
    hdr("Step 5 — Playwright Chromium browser")

    check = subprocess.run(
        [str(venv_python), "-c",
         "from playwright.sync_api import sync_playwright; "
         "pw=sync_playwright().start(); b=pw.chromium.launch(); b.close(); pw.stop(); print('ok')"],
        capture_output=True, text=True, timeout=30
    )

    if check.returncode == 0 and check.stdout.strip() == "ok":
        ok("Playwright Chromium already installed.")
        return

    if check_only:
        warn("Playwright Chromium not installed.")
        return

    info("Installing Playwright Chromium browser (this may take 1-2 minutes)...")

    # Some distros need system deps first
    deps_cmd = [str(venv_python), "-m", "playwright", "install-deps", "chromium"]
    r = subprocess.run(deps_cmd, capture_output=True, text=True)
    if r.returncode != 0 and "sudo" in r.stderr:
        info("Installing system dependencies for Chromium (requires sudo)...")
        _sudo(["bash", "-c",
               f"{venv_python} -m playwright install-deps chromium"])

    _run([str(venv_python), "-m", "playwright", "install", "chromium"])
    ok("Playwright Chromium installed.")


# ── Step 6: Tesseract OCR ─────────────────────────────────────────────────────

def ensure_tesseract(env, check_only: bool) -> None:
    hdr("Step 6 — Tesseract OCR (optional, for scanned PDFs)")

    if env.has_tesseract:
        ok("Tesseract already installed.")
        return

    warn("Tesseract not found. It's optional — needed only for scanned/image-based PDFs.")
    info("Most Form 16 and 26AS downloads from the portal are text PDFs, so this may not be needed.")

    if check_only:
        return

    install_cmds = {
        "apt":    ["apt-get", "install", "-y", "tesseract-ocr", "tesseract-ocr-eng"],
        "dnf":    ["dnf", "install", "-y", "tesseract"],
        "pacman": ["pacman", "-S", "--noconfirm", "tesseract", "tesseract-data-eng"],
        "brew":   ["brew", "install", "tesseract"],
    }

    cmd = install_cmds.get(env.pkg_manager)
    if not cmd:
        _tesseract_manual_instructions(env)
        return

    answer = input("    Install Tesseract now? (y/N): ").strip().lower()
    if answer == "y":
        _sudo(cmd)
        ok("Tesseract installed.")
    else:
        info("Skipped. You can install later if you encounter scanned PDFs.")


def _tesseract_manual_instructions(env) -> None:
    if env.system == "windows":
        info("Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        info("Add the install folder to your system PATH.")
    elif env.system == "macos":
        info("Run: brew install tesseract")
    else:
        info("Install tesseract-ocr using your distro's package manager.")


# ── Step 7: Write .claude/settings.json ──────────────────────────────────────

def write_claude_settings(venv_python: Path) -> None:
    hdr("Step 7 — Claude Code settings (inject venv into PATH)")

    venv_bin = str(venv_python.parent)
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if CLAUDE_SETTINGS.exists():
        try:
            existing = json.loads(CLAUDE_SETTINGS.read_text())
        except json.JSONDecodeError:
            pass

    existing.setdefault("env", {})

    # Prepend venv bin to PATH so 'python' and 'pip' resolve to venv versions
    current_path = existing["env"].get("PATH", "")
    if venv_bin not in current_path:
        if current_path:
            existing["env"]["PATH"] = f"{venv_bin}:{current_path}"
        else:
            # Use os.environ PATH as base so system tools still work
            system_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
            existing["env"]["PATH"] = f"{venv_bin}:{system_path}"

    CLAUDE_SETTINGS.write_text(json.dumps(existing, indent=2))
    ok(f"Wrote .claude/settings.json — venv PATH injected.")
    info(f"All skill file 'python' calls will now use: {venv_python}")


# ── Step 8: Verify everything ─────────────────────────────────────────────────

def verify_all(venv_python: Path) -> bool:
    hdr("Step 8 — Final verification")

    checks = {
        "pdfplumber":   "import pdfplumber",
        "pytesseract":  "import pytesseract",
        "Pillow":       "from PIL import Image",
        "openpyxl":     "import openpyxl",
        "pandas":       "import pandas",
        "playwright":   "import playwright",
        "python-dateutil": "import dateutil",
        "jsonschema":   "import jsonschema",
        "rich":         "import rich",
    }

    all_ok = True
    for name, stmt in checks.items():
        r = subprocess.run([str(venv_python), "-c", stmt], capture_output=True, text=True)
        if r.returncode == 0:
            ok(f"{name}")
        else:
            err(f"{name} — FAILED: {r.stderr.strip()[:80]}")
            all_ok = False

    # State manager smoke test
    r = subprocess.run(
        [str(venv_python), "-c", "from scripts.utils.state_manager import _empty_state; print('ok')"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    if r.returncode == 0:
        ok("scripts.utils.state_manager importable")
    else:
        warn(f"scripts.utils.state_manager: {r.stderr.strip()[:120]}")

    return all_ok


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(venv_python: Path, all_ok: bool) -> None:
    hdr("Setup Complete")

    if all_ok:
        print(_c("32", """
  ✓ Everything installed and verified.

  IMPORTANT — how to use this project:

  Option A (recommended): Claude Code handles PATH automatically
    → .claude/settings.json already adds the venv to PATH.
    → Just open Claude Code in this project directory and run /tax-help.

  Option B: Activate venv manually before running claude
    Linux/macOS:  source .venv/bin/activate
    Windows:      .venv\\Scripts\\activate
    Then:         claude

  To verify setup at any time:
    python scripts/setup/verify.py

  Start filing:
    /tax-help
"""))
    else:
        warn("Setup completed with some errors. Check the output above.")
        info("Try re-running /tax-setup to fix missing items.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Taxman setup")
    parser.add_argument("--check", action="store_true", help="Check only, do not install")
    parser.add_argument("--skip-tesseract", action="store_true", help="Skip Tesseract OCR install")
    parser.add_argument("--skip-browser", action="store_true", help="Skip Playwright browser download")
    args = parser.parse_args()

    check_only = args.check

    print(_c("1;36", "\nTAXMAN — Setup"))
    print(_c("36", f"  Project root : {PROJECT_ROOT}"))
    print(_c("36", f"  Mode         : {'CHECK ONLY' if check_only else 'INSTALL'}"))

    # Step 1 — Detect
    hdr("Step 1 — Detecting environment")
    env = detect_os()
    info(f"OS        : {env.system} / {env.distro}")
    info(f"Pkg mgr   : {env.pkg_manager}")
    info(f"Python    : {env.python_version or 'not found'} ({env.python_cmd or '-'})")
    info(f"venv      : {'✓' if env.has_venv else '✗'}")
    info(f"Tesseract : {'✓' if env.has_tesseract else '✗'}")
    if env.missing:
        warn(f"Missing   : {', '.join(env.missing)}")
    else:
        ok("All tools detected — nothing to install.")
        if not check_only:
            write_claude_settings(Path(env.venv_python))
        print_summary(Path(env.venv_python), True)
        return

    if check_only:
        print("\nRe-run without --check to install missing items.")
        sys.exit(1 if env.missing else 0)

    # Steps 2–7
    python_cmd = ensure_python(env, check_only)
    if not python_cmd:
        sys.exit(1)

    venv_python = create_venv(python_cmd, check_only)
    install_pip_packages(venv_python, check_only)

    if not args.skip_browser:
        try:
            install_playwright_browser(venv_python, check_only)
        except subprocess.TimeoutExpired:
            warn("Playwright browser install timed out. Re-run /tax-setup or run manually:")
            info(f"  {venv_python} -m playwright install chromium")

    if not args.skip_tesseract:
        ensure_tesseract(env, check_only)

    write_claude_settings(venv_python)

    all_ok = verify_all(venv_python)
    print_summary(venv_python, all_ok)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
