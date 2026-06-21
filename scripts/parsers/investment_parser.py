"""
Investment proof parser — extracts deduction-eligible amounts from common documents.

Supported:
  - PPF statement (PDF)
  - ELSS / MF account statement (CAMS/KFintech/broker)
  - LIC premium receipt (PDF)
  - Home loan certificate (PDF) — 80C principal + 24b interest
  - NPS statement (PDF) — 80CCD1, 80CCD1B, 80CCD2
  - Health insurance premium (80D)
  - Education loan interest certificate (80E)
  - Donation receipt (80G)
  - NSC / SCSS / Sukanya Samriddhi statement (PDF)

Each document returns: {category, amount, subcategory?, description}

CLI:
  python -m scripts.parsers.investment_parser path/to/doc.pdf [--type ppf|elss|lic|homeloan|nps|health|eduload|donation|nsc]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.parsers.base_parser import BaseParser, ParseResult
from scripts.utils.pdf_utils import extract_text


def _parse_amount(s: str) -> float:
    s = re.sub(r"[₹,\s]", "", str(s))
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_amount(text: str, *labels: str) -> float:
    for label in labels:
        pattern = re.escape(label) + r"[^\n]*?([₹,\d]+(?:\.\d{2})?)"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return _parse_amount(m.group(1))
    return 0.0


class InvestmentParser(BaseParser):
    def __init__(self, file_path, doc_type_hint: str = "auto"):
        super().__init__(file_path)
        self.doc_type_hint = doc_type_hint.lower()

    @classmethod
    def doc_type(cls) -> str:
        return "investment"

    def parse(self) -> ParseResult:
        warnings = []
        try:
            text, ocr_used = extract_text(self.file_path)
        except Exception as e:
            return ParseResult({}, "low", [f"Could not extract: {e}"])

        if ocr_used:
            warnings.append("Scanned document — OCR used. Verify amounts.")

        dtype = self.doc_type_hint if self.doc_type_hint != "auto" else self._detect_type(text)

        parsers = {
            "ppf": self._parse_ppf,
            "elss": self._parse_elss,
            "lic": self._parse_lic,
            "homeloan": self._parse_homeloan,
            "nps": self._parse_nps,
            "health": self._parse_health,
            "eduloan": self._parse_eduloan,
            "donation": self._parse_donation,
            "nsc": self._parse_generic_80c,
        }

        fn = parsers.get(dtype, self._parse_generic_80c)
        data, w = fn(text)
        warnings.extend(w)
        data["document_type_detected"] = dtype

        confidence = "medium" if data.get("amount", 0) > 0 else "low"
        return ParseResult(data, confidence, warnings)

    def _detect_type(self, text: str) -> str:
        tl = text.lower()
        if "public provident fund" in tl or "ppf" in tl:
            return "ppf"
        if "life insurance" in tl or "lic" in tl:
            return "lic"
        if "national pension" in tl or "nps" in tl or "pran" in tl:
            return "nps"
        if "home loan" in tl or "housing loan" in tl:
            return "homeloan"
        if "health insurance" in tl or "mediclaim" in tl or "health premium" in tl:
            return "health"
        if "education loan" in tl or "student loan" in tl:
            return "eduloan"
        if "donation" in tl or "80g" in tl:
            return "donation"
        if "elss" in tl or "equity linked" in tl:
            return "elss"
        if "national savings" in tl or "nsc" in tl or "sukanya" in tl or "scss" in tl:
            return "nsc"
        return "generic"

    def _parse_ppf(self, text: str):
        amount = _find_amount(text, "Total Deposit", "Deposit Amount", "Amount Deposited", "Total Credited")
        return {"category": "80C", "subcategory": "PPF", "amount": amount}, []

    def _parse_elss(self, text: str):
        amount = _find_amount(text, "Total Investment", "Amount Invested", "Purchase Amount", "Total Amount")
        return {"category": "80C", "subcategory": "ELSS", "amount": amount}, []

    def _parse_lic(self, text: str):
        amount = _find_amount(text, "Premium Paid", "Premium Amount", "Total Premium", "Amount Paid")
        return {"category": "80C", "subcategory": "LIC", "amount": amount}, []

    def _parse_homeloan(self, text: str):
        principal = _find_amount(text, "Principal Repaid", "Principal", "Principal Amount")
        interest = _find_amount(text, "Interest Paid", "Interest Amount", "Total Interest")
        warnings = []
        if principal == 0:
            warnings.append("Could not extract principal repayment — enter manually.")
        if interest == 0:
            warnings.append("Could not extract interest paid — enter manually.")
        return {
            "category": "multiple",
            "80C_principal": principal,
            "24b_interest": interest,
            "amount": principal,
        }, warnings

    def _parse_nps(self, text: str):
        tier1 = _find_amount(text, "Tier I", "Tier-I", "Employee Contribution")
        tier1b = _find_amount(text, "Voluntary", "Additional Contribution", "80CCD(1B)")
        employer = _find_amount(text, "Employer Contribution", "Employer", "80CCD(2)")
        return {
            "category": "nps",
            "80CCD1": tier1,
            "80CCD1B": tier1b,
            "80CCD2": employer,
            "amount": tier1 + tier1b + employer,
        }, []

    def _parse_health(self, text: str):
        self_amount = _find_amount(text, "Self Premium", "Self", "Premium for Self")
        parent_amount = _find_amount(text, "Parent Premium", "Parents", "Premium for Parents")
        if self_amount == 0:
            self_amount = _find_amount(text, "Total Premium", "Premium Amount", "Amount")
        return {
            "category": "80D",
            "80D_self": self_amount,
            "80D_parents": parent_amount,
            "amount": self_amount + parent_amount,
        }, []

    def _parse_eduloan(self, text: str):
        interest = _find_amount(text, "Interest Paid", "Interest Amount", "Total Interest")
        return {"category": "80E", "amount": interest}, []

    def _parse_donation(self, text: str):
        amount = _find_amount(text, "Donation Amount", "Amount Donated", "Amount", "Total")
        entity_m = re.search(r"(?:Name of|Donated to|Donee)[:\s]+([A-Z][^\n]{5,60})", text, re.IGNORECASE)
        entity = entity_m.group(1).strip() if entity_m else "Unknown"
        pct_m = re.search(r"(\d+)\s*%\s*deduction", text, re.IGNORECASE)
        pct = int(pct_m.group(1)) if pct_m else 50
        return {
            "category": "80G",
            "entity": entity,
            "amount": amount,
            "deductible_percent": pct,
        }, []

    def _parse_generic_80c(self, text: str):
        amount = _find_amount(text, "Amount", "Total", "Deposit", "Investment")
        return {"category": "80C", "subcategory": "other", "amount": amount}, [
            "Generic 80C parser used — verify category and amount."
        ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--type", default="auto", dest="doc_type",
                        choices=["ppf", "elss", "lic", "homeloan", "nps", "health", "eduloan", "donation", "nsc", "auto"])
    args = parser.parse_args()
    result = InvestmentParser(args.file, args.doc_type).parse()
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
