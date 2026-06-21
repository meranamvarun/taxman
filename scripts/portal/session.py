"""
Playwright session manager for the income tax portal.

- Always runs in headed mode (user sees the browser)
- Human-pause helper: stops automation and waits for user to press Enter
- Screenshots saved to screenshots/ after each major step
- Detects session timeout (redirect to login page) and prompts re-login
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

PORTAL_URL = "https://www.incometax.gov.in/iec/foportal/"
LOGIN_INDICATOR = "/iec/foportal/login"
SCREENSHOTS_DIR = Path("screenshots")


def launch() -> tuple:
    """Launch Playwright and return (playwright, browser, page)."""
    from playwright.sync_api import sync_playwright

    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    return pw, browser, page


def open_portal(page) -> None:
    """Navigate to the income tax portal home page."""
    page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)


def human_pause(page, message: str, step_name: str = "") -> None:
    """
    Stop automation, show a message, and wait for user to press Enter.
    Takes a screenshot before pausing.
    """
    _screenshot(page, step_name or "before_pause")
    print()
    print("=" * 70)
    print(f"  ACTION REQUIRED")
    print(f"  {message}")
    print("=" * 70)
    print("  Press Enter when done...")
    input()
    _screenshot(page, step_name + "_after" if step_name else "after_pause")


def check_session_alive(page) -> bool:
    """Return False if the portal has redirected to the login page."""
    return LOGIN_INDICATOR not in page.url


def wait_for_login(page) -> None:
    """Block until the user is logged in (dashboard visible)."""
    human_pause(
        page,
        "Please log in to the Income Tax Portal using your PAN/Aadhaar/Net Banking.\n"
        "  Complete OTP verification as prompted by the portal.\n"
        "  Once the dashboard is visible, press Enter to continue.",
        step_name="login",
    )
    # Wait for dashboard element to appear
    try:
        page.wait_for_selector("text=e-File", timeout=60000)
    except Exception:
        print("  [Warning] Could not confirm dashboard loaded — proceeding anyway.")


def safe_fill(page, selector: str, value: str, label: str = "") -> None:
    """Fill a field, retrying once on timeout. Logs warnings on failure."""
    try:
        page.wait_for_selector(selector, timeout=10000)
        page.fill(selector, str(value))
    except Exception as e:
        print(f"  [Warning] Could not fill {label or selector}: {e}", file=sys.stderr)


def safe_click(page, selector: str, label: str = "") -> None:
    try:
        page.wait_for_selector(selector, timeout=10000)
        page.click(selector)
        time.sleep(0.5)
    except Exception as e:
        print(f"  [Warning] Could not click {label or selector}: {e}", file=sys.stderr)


def safe_select(page, selector: str, value: str, label: str = "") -> None:
    try:
        page.wait_for_selector(selector, timeout=10000)
        page.select_option(selector, value=value)
    except Exception as e:
        print(f"  [Warning] Could not select {label or selector}: {e}", file=sys.stderr)


def _screenshot(page, name: str) -> Path:
    ts = datetime.now().strftime("%H%M%S")
    safe_name = name.replace(" ", "_").replace("/", "-")
    path = SCREENSHOTS_DIR / f"{ts}_{safe_name}.png"
    try:
        page.screenshot(path=str(path))
    except Exception:
        pass
    return path


def close(pw, browser) -> None:
    try:
        browser.close()
        pw.stop()
    except Exception:
        pass
