"""
Quick dependency checker — no installs, just reports what's working.

Exit code 0 = everything required is present.
Exit code 1 = something required is missing.
Exit code 2 = only optional items (Tesseract) missing.

CLI:
  python scripts/setup/verify.py
  python scripts/setup/verify.py --json    # machine-readable output
  python scripts/setup/verify.py --quiet   # only print failures
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _c(code: str, text: str) -> str:
    if os.name == "nt" or not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _venv_python() -> Path | None:
    candidates = [
        PROJECT_ROOT / ".venv" / "bin" / "python",
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _run_in_venv(venv_py: Path, code: str) -> bool:
    r = subprocess.run([str(venv_py), "-c", code], capture_output=True, text=True)
    return r.returncode == 0


def check_all(quiet: bool = False) -> dict:
    venv_py = _venv_python()

    results = {
        "venv_exists": venv_py is not None,
        "packages": {},
        "playwright_browser": False,
        "tesseract": False,
        "state_manager": False,
        "tax_rules": False,
    }

    def _ok(label: str) -> None:
        if not quiet:
            print(_c("32", f"  ✓ {label}"))

    def _fail(label: str, detail: str = "") -> None:
        msg = f"  ✗ {label}"
        if detail:
            msg += f" — {detail}"
        print(_c("31", msg))

    def _warn(label: str, detail: str = "") -> None:
        msg = f"  ⚠ {label}"
        if detail:
            msg += f" — {detail}"
        print(_c("33", msg))

    # ── venv ──────────────────────────────────────────────────────────────
    if venv_py:
        _ok(f"Virtual environment (.venv/) — Python at {venv_py}")
    else:
        _fail(".venv/ not found", "Run /tax-setup to create it")
        results["venv_exists"] = False
        return results

    # ── pip packages ──────────────────────────────────────────────────────
    required = {
        "pdfplumber":    "import pdfplumber",
        "pytesseract":   "import pytesseract",
        "Pillow":        "from PIL import Image",
        "openpyxl":      "import openpyxl",
        "pandas":        "import pandas",
        "playwright":    "import playwright",
        "python-dateutil": "import dateutil",
        "jsonschema":    "import jsonschema",
        "rich":          "import rich",
    }

    for name, stmt in required.items():
        ok_flag = _run_in_venv(venv_py, stmt)
        results["packages"][name] = ok_flag
        if ok_flag:
            _ok(f"{name}")
        else:
            _fail(f"{name}", "missing — run /tax-setup")

    # ── Playwright browser ─────────────────────────────────────────────────
    r = subprocess.run(
        [str(venv_py), "-c",
         "from playwright.sync_api import sync_playwright; "
         "pw=sync_playwright().start(); b=pw.chromium.launch(); b.close(); pw.stop(); print('ok')"],
        capture_output=True, text=True, timeout=20
    )
    results["playwright_browser"] = r.returncode == 0 and "ok" in r.stdout
    if results["playwright_browser"]:
        _ok("Playwright Chromium browser")
    else:
        _fail("Playwright Chromium browser", "run /tax-setup or: python -m playwright install chromium")

    # ── Tesseract (optional) ───────────────────────────────────────────────
    import shutil
    tess = shutil.which("tesseract")
    if tess:
        results["tesseract"] = True
        _ok(f"Tesseract OCR ({tess})")
    else:
        _warn("Tesseract OCR — not installed (optional; needed only for scanned PDFs)")

    # ── Project modules ────────────────────────────────────────────────────
    r2 = subprocess.run(
        [str(venv_py), "-c", "from scripts.utils.state_manager import load; print('ok')"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    results["state_manager"] = r2.returncode == 0
    if results["state_manager"]:
        _ok("scripts.utils.state_manager")
    else:
        _fail("scripts.utils.state_manager", r2.stderr.strip()[:100])

    r3 = subprocess.run(
        [str(venv_py), "-c", "from scripts.calculators import tax_rules; print(tax_rules.list_available())"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    results["tax_rules"] = r3.returncode == 0
    if results["tax_rules"]:
        _ok(f"Tax rules available: {r3.stdout.strip()}")
    else:
        _fail("Tax rules", r3.stderr.strip()[:100])

    # ── Claude settings ────────────────────────────────────────────────────
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
            venv_in_path = str(venv_py.parent) in settings.get("env", {}).get("PATH", "")
            if venv_in_path:
                _ok(".claude/settings.json — venv PATH configured")
            else:
                _warn(".claude/settings.json exists but venv PATH not configured — run /tax-setup")
        except Exception:
            _warn(".claude/settings.json parse error — run /tax-setup")
    else:
        _warn(".claude/settings.json missing — run /tax-setup")

    return results


def _exit_code(results: dict) -> int:
    required_ok = (
        results.get("venv_exists") and
        all(results.get("packages", {}).values()) and
        results.get("playwright_browser") and
        results.get("state_manager") and
        results.get("tax_rules")
    )
    if not required_ok:
        return 1
    if not results.get("tesseract"):
        return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify taxman dependencies")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.quiet and not args.as_json:
        print(_c("1;36", "\nTAXMAN — Dependency Check"))
        print(_c("36",   f"  Project: {PROJECT_ROOT}\n"))

    results = check_all(quiet=args.quiet)
    code = _exit_code(results)

    if args.as_json:
        print(json.dumps(results, indent=2))
    elif not args.quiet:
        print()
        if code == 0:
            print(_c("32", "  All dependencies satisfied. Ready to file taxes.\n"))
        elif code == 2:
            print(_c("33", "  Required tools OK. Tesseract missing (optional for scanned PDFs).\n"))
        else:
            print(_c("31", "  Some required tools missing. Run /tax-setup to install.\n"))

    sys.exit(code)


if __name__ == "__main__":
    main()
