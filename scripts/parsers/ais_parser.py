"""
Annual Information Statement (AIS) + Taxpayer Information Summary (TIS) parser.

Extracts income categories pre-populated by the IT department:
  - Salary
  - Rent received
  - Dividends
  - Interest from savings / FD / bonds
  - Capital gains (equity, MF, property)
  - Foreign remittances

Each category has: reported_value (from third party) and taxpayer_value (after corrections).
We use taxpayer_value where available, else reported_value.

CLI:
  python -m scripts.parsers.ais_parser path/to/ais.pdf
"""

from __future__ import annotations

import json
import re
import sys

from scripts.parsers.base_parser import BaseParser, ParseResult
from scripts.utils.pdf_utils import extract_text, extract_tables


def _parse_amount(s: str) -> float:
    s = re.sub(r"[₹,\s]", "", str(s))
    try:
        return float(s)
    except ValueError:
        return 0.0


_SECTION_KEYWORDS = {
    "salary": ["salary", "wage", "tds on salary"],
    "interest_savings": ["saving", "savings bank interest"],
    "interest_fd": ["term deposit", "fixed deposit", "recurring deposit", "interest on"],
    "dividend": ["dividend"],
    "capital_gains_equity": ["securities", "listed equity", "equity mutual fund"],
    "capital_gains_property": ["immovable property"],
    "rent": ["rent", "rental"],
    "foreign_remittance": ["foreign remittance", "overseas"],
}


def _classify_line(text: str) -> str | None:
    tl = text.lower()
    for category, keywords in _SECTION_KEYWORDS.items():
        if any(k in tl for k in keywords):
            return category
    return None


class AISParser(BaseParser):
    @classmethod
    def doc_type(cls) -> str:
        return "ais"

    def parse(self) -> ParseResult:
        warnings = []
        try:
            text, ocr_used = extract_text(self.file_path)
            tables = extract_tables(self.file_path)
        except Exception as e:
            return ParseResult({}, "low", [f"Could not extract: {e}"])

        if ocr_used:
            warnings.append("Scanned PDF — OCR used. Verify AIS figures.")

        pan_m = re.search(r"PAN[:\s]+([A-Z]{5}[0-9]{4}[A-Z])", text, re.IGNORECASE)
        name_m = re.search(r"(?:Name|Taxpayer Name)[:\s]+([A-Z][A-Za-z\s]{3,60})\n", text)

        extracted: dict[str, float] = {
            "salary": 0.0,
            "interest_savings": 0.0,
            "interest_fd": 0.0,
            "dividend": 0.0,
            "capital_gains_equity": 0.0,
            "capital_gains_property": 0.0,
            "rent": 0.0,
            "foreign_remittance": 0.0,
            "other": 0.0,
        }

        # Try to parse from tables
        for table in tables:
            for row in table:
                cells = [str(c or "").strip() for c in row]
                row_str = " ".join(cells)
                cat = _classify_line(row_str)
                # Last non-empty numeric cell is usually the value
                amounts = [_parse_amount(c) for c in cells if re.match(r"^[\d,₹]+$", c.replace(" ", ""))]
                if cat and amounts:
                    # Prefer last column (taxpayer value) over second-to-last (reported value)
                    extracted[cat] += amounts[-1]

        # Fallback: extract named amounts from raw text
        if all(v == 0 for v in extracted.values()):
            patterns = {
                "salary": r"Salary[^\n]*?([₹,\d]+(?:\.\d{2})?)",
                "interest_savings": r"Savings\s+Bank\s+Interest[^\n]*?([₹,\d]+(?:\.\d{2})?)",
                "interest_fd": r"(?:Fixed|Term)\s+Deposit[^\n]*?([₹,\d]+(?:\.\d{2})?)",
                "dividend": r"Dividend[^\n]*?([₹,\d]+(?:\.\d{2})?)",
            }
            for cat, pattern in patterns.items():
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    extracted[cat] = _parse_amount(m.group(1))
            if any(v > 0 for v in extracted.values()):
                warnings.append("AIS parsed via fallback — table extraction failed. Verify figures.")

        has_data = any(v > 0 for v in extracted.values())
        confidence = "medium" if has_data else "low"

        if not has_data:
            warnings.append(
                "No income figures found in AIS. The AIS PDF from the portal sometimes uses "
                "JavaScript rendering and may not be extractable. Try downloading as a non-password-protected PDF."
            )

        data = {
            "pan": pan_m.group(1) if pan_m else None,
            "name": name_m.group(1).strip() if name_m else None,
            "income": extracted,
            "note": "Values represent taxpayer-corrected figures where available, else reported values.",
        }

        return ParseResult(data, confidence, warnings)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.parsers.ais_parser <pdf_path>")
        sys.exit(1)
    result = AISParser(sys.argv[1]).parse()
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
