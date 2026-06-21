"""
Portal navigation helpers — moves through the ITR filing wizard.

Selects AY, filing mode, and ITR form type on the portal's multi-step wizard.
"""

from __future__ import annotations

import sys
import time

from scripts.portal import session as sess


def navigate_to_file_itr(page) -> None:
    """From dashboard: e-File → Income Tax Returns → File Income Tax Return."""
    try:
        page.wait_for_selector("text=e-File", timeout=15000)
        page.hover("text=e-File")
        time.sleep(0.5)
        page.click("text=Income Tax Returns")
        time.sleep(0.5)
        page.click("text=File Income Tax Return")
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception as e:
        print(f"  [Warning] Navigation error: {e}", file=sys.stderr)
        sess.human_pause(
            page,
            "Could not automatically navigate to File Income Tax Return.\n"
            "Please navigate manually: e-File → Income Tax Returns → File Income Tax Return.\n"
            "Press Enter once you are on the filing start page.",
            step_name="manual_nav",
        )


def select_ay_and_mode(page, ay: str) -> None:
    """Select Assessment Year and Online filing mode."""
    try:
        # Select AY from dropdown
        ay_selector = "select[name*='assessmentYear'], select[id*='assessmentYear'], select[aria-label*='Assessment Year']"
        page.wait_for_selector(ay_selector, timeout=15000)
        page.select_option(ay_selector, label=ay)
        time.sleep(0.5)

        # Click Continue
        page.click("button:has-text('Continue'), input[value='Continue']")
        time.sleep(1)

        # Select Online mode
        online_selector = "input[value='Online'], label:has-text('Online')"
        try:
            page.click(online_selector, timeout=5000)
        except Exception:
            pass
        time.sleep(0.5)

        # Click Continue again
        page.click("button:has-text('Continue'), input[value='Continue']")
        page.wait_for_load_state("networkidle", timeout=15000)

    except Exception as e:
        print(f"  [Warning] Could not auto-select AY/mode: {e}", file=sys.stderr)
        sess.human_pause(
            page,
            f"Please select Assessment Year {ay}, choose 'Online' filing mode, and click Continue.\n"
            "Press Enter once done.",
            step_name="ay_mode_select",
        )


def select_itr_form(page, itr_form: str) -> None:
    """Select the correct ITR form on the portal."""
    try:
        form_selector = f"input[value='{itr_form}'], label:has-text('{itr_form}')"
        page.click(form_selector, timeout=10000)
        time.sleep(0.5)
        page.click("button:has-text('Proceed'), button:has-text('Let\\'s Get Started')")
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception as e:
        print(f"  [Warning] Could not auto-select {itr_form}: {e}", file=sys.stderr)
        sess.human_pause(
            page,
            f"Please select {itr_form} and click Proceed / Let's Get Started.\n"
            "Press Enter once done.",
            step_name="form_select",
        )


def navigate_to_section(page, section_name: str) -> None:
    """Click on a named section in the ITR wizard sidebar."""
    try:
        page.click(f"text={section_name}", timeout=8000)
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(0.5)
    except Exception as e:
        print(f"  [Warning] Could not navigate to section '{section_name}': {e}", file=sys.stderr)
