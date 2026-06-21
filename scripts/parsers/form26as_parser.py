"""
Form 26AS parser — TDS/TCS statement downloaded from income tax portal.

Extracts:
- Part A: TDS on salary / non-salary (deductor-wise)
- Part B: TDS on sale of immovable property
- Part C: Advance tax / self-assessment tax paid
- Part F: TDS on rent (26QC)
- Part G: TCS entries

CLI:
  python -m scripts.parsers.form26as_parser path/to/26as.pdf
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scripts.parsers.base_parser import BaseParser, ParseResult
from scripts.utils.pdf_utils import extract_text, extract_tables


def _parse_amount(s: str) -> float:
    s = re.sub(r"[₹,\s]", "", str(s))
    try:
        return float(s)
    except ValueError:
        return 0.0


class Form26ASParser(BaseParser):
    @classmethod
    def doc_type(cls) -> str:
        return "form26as"

    def parse(self) -> ParseResult:
        warnings = []
        try:
            text, ocr_used = extract_text(self.file_path)
            tables = extract_tables(self.file_path)
        except Exception as e:
            return ParseResult({}, "low", [f"Could not extract: {e}"])

        if ocr_used:
            warnings.append("Scanned/image PDF — OCR used. Verify amounts carefully.")

        pan_m = re.search(r"PAN[:\s]+([A-Z]{5}[0-9]{4}[A-Z])", text, re.IGNORECASE)
        name_m = re.search(r"Name[:\s]+([A-Z][A-Z\s]{3,50})\n", text, re.IGNORECASE)

        data: dict = {
            "pan": pan_m.group(1) if pan_m else None,
            "name": name_m.group(1).strip() if name_m else None,
            "part_a_tds": [],
            "part_c_self_tax": [],
            "part_f_tds_rent": [],
            "part_g_tcs": [],
            "totals": {
                "total_tds": 0.0,
                "total_advance_tax": 0.0,
                "total_self_assessment_tax": 0.0,
            },
        }

        # --- Parse TDS entries from tables ---
        current_section = None
        for table in tables:
            for row in table:
                row_text = " ".join(str(c or "") for c in row).strip()

                if "Part A" in row_text and "TDS" in row_text:
                    current_section = "part_a"
                    continue
                if "Part C" in row_text and ("Advance" in row_text or "Self" in row_text):
                    current_section = "part_c"
                    continue
                if "Part F" in row_text:
                    current_section = "part_f"
                    continue
                if "Part G" in row_text and "TCS" in row_text:
                    current_section = "part_g"
                    continue

                cells = [str(c or "").strip() for c in row]

                if current_section == "part_a" and len(cells) >= 6:
                    tds_amt = _parse_amount(cells[-2]) if len(cells) > 5 else 0
                    if tds_amt > 0:
                        data["part_a_tds"].append({
                            "deductor_name": cells[1] if len(cells) > 1 else "",
                            "deductor_tan": cells[2] if len(cells) > 2 else "",
                            "amount_paid": _parse_amount(cells[3]) if len(cells) > 3 else 0,
                            "tds_deducted": tds_amt,
                            "tds_deposited": _parse_amount(cells[-1]),
                        })

                elif current_section == "part_c" and len(cells) >= 4:
                    amt = _parse_amount(cells[-2]) if len(cells) > 3 else 0
                    if amt > 0:
                        tax_type = "advance" if "advance" in row_text.lower() else "self_assessment"
                        data["part_c_self_tax"].append({
                            "type": tax_type,
                            "bsr_code": cells[0] if cells else "",
                            "date": cells[1] if len(cells) > 1 else "",
                            "challan": cells[2] if len(cells) > 2 else "",
                            "amount": amt,
                        })

        # Fallback: try regex if tables didn't yield data
        if not data["part_a_tds"]:
            entries = re.findall(
                r"([A-Z]{4}[0-9]{5}[A-Z])\s+([\d,]+)\s+([\d,]+)",
                text
            )
            for tan, paid, tds in entries:
                data["part_a_tds"].append({
                    "deductor_tan": tan,
                    "amount_paid": _parse_amount(paid),
                    "tds_deducted": _parse_amount(tds),
                })
            if entries:
                warnings.append("TDS entries parsed via fallback regex — verify each entry.")

        # Totals
        data["totals"]["total_tds"] = sum(e["tds_deducted"] for e in data["part_a_tds"])
        data["totals"]["total_advance_tax"] = sum(
            e["amount"] for e in data["part_c_self_tax"] if e["type"] == "advance"
        )
        data["totals"]["total_self_assessment_tax"] = sum(
            e["amount"] for e in data["part_c_self_tax"] if e["type"] == "self_assessment"
        )

        confidence = "high" if data["part_a_tds"] else "low"
        if not data["pan"]:
            warnings.append("PAN not found in 26AS.")
            confidence = "medium"

        return ParseResult(data, confidence, warnings)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.parsers.form26as_parser <pdf_path>")
        sys.exit(1)
    result = Form26ASParser(sys.argv[1]).parse()
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
