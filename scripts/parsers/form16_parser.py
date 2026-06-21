"""
Form 16 parser — Part A (TDS certificate) + Part B (salary breakup).

Supports:
- Standard Form 16 PDF issued by TRACES
- Common custom formats (detected by keyword heuristics)
- Multiple Form 16s (one per employer)

Output schema:
  employer_name, employer_tan, employer_pan
  employee_pan, employee_name
  period: {from, to}
  part_a: {tds_quarterly: [...], total_tds_deducted}
  part_b: {
    gross_salary, basic, hra_received, special_allowance,
    perquisites, professional_tax, standard_deduction,
    net_salary, deductions: {80C, 80D, ...}, taxable_salary
  }

CLI:
  python -m scripts.parsers.form16_parser path/to/form16.pdf
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scripts.parsers.base_parser import BaseParser, ParseResult
from scripts.utils.pdf_utils import extract_text


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_amount(s: str) -> float:
    s = re.sub(r"[₹,\s]", "", str(s))
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_amount_after(text: str, label: str) -> float:
    pattern = re.escape(label) + r"[\s:]*([₹,\d]+(?:\.\d{2})?)"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return _parse_amount(m.group(1))
    return 0.0


def _find_pan(text: str) -> str | None:
    m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    return m.group(1) if m else None


def _find_tan(text: str) -> str | None:
    m = re.search(r"\b([A-Z]{4}[0-9]{5}[A-Z])\b", text)
    return m.group(1) if m else None


class Form16Parser(BaseParser):
    @classmethod
    def doc_type(cls) -> str:
        return "form16"

    def parse(self) -> ParseResult:
        warnings = []
        try:
            text, ocr_used = extract_text(self.file_path)
        except Exception as e:
            return ParseResult({}, "low", [f"Could not extract text: {e}"])

        if ocr_used:
            warnings.append("Scanned PDF detected — OCR used. Please verify all amounts carefully.")

        data = {}
        confidence = "high"

        # --- Employer ---
        emp_name_m = re.search(r"Name\s+(?:of\s+Employer|and\s+address)[:\s]+([A-Z][^\n]{3,60})", text, re.IGNORECASE)
        data["employer_name"] = _clean(emp_name_m.group(1)) if emp_name_m else None

        # TAN of deductor
        data["employer_tan"] = _find_tan(text)
        if not data["employer_tan"]:
            warnings.append("Employer TAN not found.")
            confidence = "medium"

        # --- Employee ---
        emp_pan_m = re.search(r"PAN\s+of\s+(?:the\s+)?Employee[:\s]+([A-Z]{5}[0-9]{4}[A-Z])", text, re.IGNORECASE)
        data["employee_pan"] = emp_pan_m.group(1) if emp_pan_m else _find_pan(text)

        emp_name2_m = re.search(r"Name\s+of\s+(?:the\s+)?Employee[:\s]+([A-Za-z][^\n]{2,60})", text, re.IGNORECASE)
        data["employee_name"] = _clean(emp_name2_m.group(1)) if emp_name2_m else None

        # --- Period ---
        period_m = re.search(r"(?:period|from)[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})\s+(?:to)[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})", text, re.IGNORECASE)
        if period_m:
            data["period"] = {"from": period_m.group(1), "to": period_m.group(2)}
        else:
            ay_m = re.search(r"(?:Assessment\s+Year|A\.Y\.)[:\s]+(\d{4}[-–]\d{2})", text, re.IGNORECASE)
            data["period"] = {"assessment_year": ay_m.group(1) if ay_m else None}

        # --- Part A: TDS ---
        tds_total_m = re.search(
            r"(?:Total\s+(?:amount\s+of\s+)?tax\s+deducted|Total\s+TDS)[:\s]*([₹,\d]+(?:\.\d{2})?)",
            text, re.IGNORECASE
        )
        total_tds = _parse_amount(tds_total_m.group(1)) if tds_total_m else 0.0

        # Quarterly breakdown (q1–q4)
        quarters = []
        for q, pattern in enumerate([
            r"Apr.*?Jun", r"Jul.*?Sep", r"Oct.*?Dec", r"Jan.*?Mar"
        ], 1):
            qm = re.search(
                rf"({pattern})[^\n]*\n[^\n]*?([₹,\d]+(?:\.\d{{2}})?)\s+([₹,\d]+(?:\.\d{{2}})?)",
                text, re.IGNORECASE | re.DOTALL
            )
            if qm:
                quarters.append({
                    "quarter": f"Q{q}",
                    "amount_paid": _parse_amount(qm.group(2)),
                    "tds_deducted": _parse_amount(qm.group(3)),
                })

        data["part_a"] = {
            "tds_quarterly": quarters,
            "total_tds_deducted": total_tds,
        }

        # --- Part B: Salary breakdown ---
        gross = _find_amount_after(text, "Gross Salary")
        if gross == 0:
            gross = _find_amount_after(text, "Total Salary")

        hra = _find_amount_after(text, "House Rent Allowance")
        basic = _find_amount_after(text, "Basic")
        special_allowance = _find_amount_after(text, "Special Allowance")
        lta = _find_amount_after(text, "Leave Travel")
        perquisites = _find_amount_after(text, "Perquisites")
        prof_tax = _find_amount_after(text, "Professional Tax")
        std_ded = _find_amount_after(text, "Standard Deduction")

        # Deductions under Chapter VI-A (as reported by employer)
        c80c = _find_amount_after(text, "80C")
        c80d = _find_amount_after(text, "80D")
        c80ccd = _find_amount_after(text, "80CCD")

        taxable_m = re.search(
            r"(?:Taxable\s+Salary|Net\s+Taxable\s+Income)[:\s]*([₹,\d]+(?:\.\d{2})?)",
            text, re.IGNORECASE
        )
        taxable_salary = _parse_amount(taxable_m.group(1)) if taxable_m else 0.0

        data["part_b"] = {
            "gross_salary": gross,
            "basic": basic,
            "hra_received": hra,
            "special_allowance": special_allowance,
            "lta": lta,
            "perquisites": perquisites,
            "professional_tax": prof_tax,
            "standard_deduction": std_ded if std_ded > 0 else 50000,
            "deductions_by_employer": {"80C": c80c, "80D": c80d, "80CCD": c80ccd},
            "taxable_salary": taxable_salary,
        }

        if gross == 0:
            warnings.append("Gross salary is 0 — could not parse Part B reliably.")
            confidence = "low"
        elif taxable_salary == 0:
            warnings.append("Taxable salary is 0 — check Part B extraction.")
            confidence = "medium"

        return ParseResult(data, confidence, warnings)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.parsers.form16_parser <pdf_path>")
        sys.exit(1)
    parser = Form16Parser(sys.argv[1])
    result = parser.parse()
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
