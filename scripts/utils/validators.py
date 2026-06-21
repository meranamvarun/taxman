"""Input validation for Indian tax filing fields."""

from __future__ import annotations

import re
from datetime import date, datetime


def validate_pan(pan: str) -> tuple[bool, str]:
    """PAN format: AAAAA9999A (5 alpha + 4 digits + 1 alpha, uppercase)."""
    pan = pan.strip().upper()
    if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
        return True, pan
    return False, f"Invalid PAN format: {pan!r}. Expected AAAAA9999A."


def validate_ifsc(ifsc: str) -> tuple[bool, str]:
    """IFSC format: 4 alpha (bank code) + 0 + 6 alphanumeric (branch)."""
    ifsc = ifsc.strip().upper()
    if re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc):
        return True, ifsc
    return False, f"Invalid IFSC format: {ifsc!r}. Expected AAAA0XXXXXX."


def validate_ay(ay: str) -> tuple[bool, str]:
    """AY format: YYYY-YY where end year = start year + 1."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", ay.strip())
    if not m:
        return False, f"Invalid AY format: {ay!r}. Expected YYYY-YY (e.g. 2026-27)."
    start, end = int(m.group(1)), int(m.group(2))
    expected_end = (start + 1) % 100
    if end != expected_end:
        return False, f"AY end year mismatch: {ay!r}. End should be {expected_end:02d}."
    return True, ay.strip()


def validate_dob(dob_str: str) -> tuple[bool, date | None, str]:
    """Accept DD/MM/YYYY or YYYY-MM-DD. Returns (ok, date_obj, message)."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            d = datetime.strptime(dob_str.strip(), fmt).date()
            if d >= date.today():
                return False, None, "Date of birth cannot be in the future."
            if d.year < 1900:
                return False, None, "Date of birth seems too old."
            return True, d, d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return False, None, f"Cannot parse date: {dob_str!r}. Use DD/MM/YYYY."


def validate_mobile(mobile: str) -> tuple[bool, str]:
    digits = re.sub(r"[\s\-\+]", "", mobile)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if re.fullmatch(r"[6-9]\d{9}", digits):
        return True, digits
    return False, f"Invalid mobile number: {mobile!r}. Must be 10-digit Indian number."


def validate_amount(value) -> tuple[bool, float, str]:
    """Ensure value is a non-negative number."""
    try:
        v = float(str(value).replace(",", ""))
        if v < 0:
            return False, 0.0, f"Amount cannot be negative: {value}"
        return True, round(v, 2), ""
    except (ValueError, TypeError):
        return False, 0.0, f"Cannot parse amount: {value!r}"


def taxpayer_category(dob: date, ay: str) -> str:
    """Return 'general', 'senior', or 'super_senior' based on age at year-end."""
    fy_end_year = int(ay[:4])
    fy_end = date(fy_end_year, 3, 31)
    age = (fy_end - dob).days // 365
    if age >= 80:
        return "super_senior"
    if age >= 60:
        return "senior"
    return "general"
