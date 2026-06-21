"""
Bank statement parser — extracts interest income only.

Supported formats:
  - SBI: PDF / CSV export
  - HDFC: PDF / CSV export
  - ICICI: PDF / CSV export
  - Axis: PDF / CSV export
  - Generic: CSV with column auto-detection

Interest credit rows are identified by keywords in the narration/description column.
Outputs: savings_interest total and fd_interest total.

CLI:
  python -m scripts.parsers.bank_statement_parser path/to/statement.pdf [--bank sbi|hdfc|icici|axis|auto]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from scripts.parsers.base_parser import BaseParser, ParseResult
from scripts.utils.pdf_utils import extract_text, extract_tables


SAVINGS_KEYWORDS = [
    "interest cr", "int cr", "int. cr", "savings interest", "sb int",
    "interest on savings", "int on savings", "quarterly interest",
    "half yearly interest", "savings account interest",
]

FD_KEYWORDS = [
    "fd interest", "tdr int", "term deposit int", "fixed deposit int",
    "rd interest", "recurring deposit int", "stdr int", "mmda int",
]

IGNORE_KEYWORDS = [
    "reversed", "reversal", "refund", "penalty", "charge",
]


def _parse_amount(s: str) -> float:
    s = re.sub(r"[₹,\s]", "", str(s))
    try:
        return float(s)
    except ValueError:
        return 0.0


def _is_savings_interest(narration: str) -> bool:
    nl = narration.lower()
    if any(kw in nl for kw in IGNORE_KEYWORDS):
        return False
    return any(kw in nl for kw in SAVINGS_KEYWORDS)


def _is_fd_interest(narration: str) -> bool:
    nl = narration.lower()
    if any(kw in nl for kw in IGNORE_KEYWORDS):
        return False
    return any(kw in nl for kw in FD_KEYWORDS)


def _find_credit_col(header: list[str]) -> int | None:
    """Find the index of the credit/deposit column."""
    for i, h in enumerate(header):
        hl = h.lower().strip()
        if hl in ("cr", "credit", "deposit", "credited", "cr amount", "deposit amount"):
            return i
    return None


def _find_narration_col(header: list[str]) -> int | None:
    for i, h in enumerate(header):
        hl = h.lower().strip()
        if hl in ("description", "narration", "particulars", "remarks", "transaction details", "txn details"):
            return i
    return None


class BankStatementParser(BaseParser):
    def __init__(self, file_path: str | Path, bank: str = "auto"):
        super().__init__(file_path)
        self.bank = bank.lower()

    @classmethod
    def doc_type(cls) -> str:
        return "bank_statement"

    def parse(self) -> ParseResult:
        suffix = self.file_path.suffix.lower()
        if suffix == ".csv":
            return self._parse_csv()
        return self._parse_pdf()

    def _parse_pdf(self) -> ParseResult:
        warnings = []
        try:
            text, ocr_used = extract_text(self.file_path)
            tables = extract_tables(self.file_path)
        except Exception as e:
            return ParseResult({}, "low", [f"Could not extract: {e}"])

        if ocr_used:
            warnings.append("Scanned bank statement — OCR used. Verify interest amounts.")

        entries = []
        for table in tables:
            if len(table) < 2:
                continue
            header = [str(c or "").strip() for c in table[0]]
            cr_col = _find_credit_col(header)
            narr_col = _find_narration_col(header)

            if cr_col is None or narr_col is None:
                continue

            for row in table[1:]:
                cells = [str(c or "").strip() for c in row]
                if len(cells) <= max(cr_col, narr_col):
                    continue
                narration = cells[narr_col]
                credit = _parse_amount(cells[cr_col])
                if credit <= 0:
                    continue
                if _is_savings_interest(narration):
                    entries.append({"type": "savings", "amount": credit, "narration": narration})
                elif _is_fd_interest(narration):
                    entries.append({"type": "fd", "amount": credit, "narration": narration})

        if not entries:
            # Fallback: search raw text for interest credit lines
            for line in text.split("\n"):
                if _is_savings_interest(line) or _is_fd_interest(line):
                    amt_m = re.search(r"([\d,]+\.?\d*)\s*(?:Cr|CR)?$", line)
                    if amt_m:
                        t = "savings" if _is_savings_interest(line) else "fd"
                        entries.append({"type": t, "amount": _parse_amount(amt_m.group(1)), "narration": line.strip()})
            if entries:
                warnings.append("Interest entries extracted via text fallback — verify amounts.")

        return self._summarise(entries, warnings)

    def _parse_csv(self) -> ParseResult:
        warnings = []
        entries = []
        try:
            with self.file_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except UnicodeDecodeError:
            with self.file_path.open(newline="", encoding="latin-1") as f:
                reader = csv.reader(f)
                rows = list(reader)

        if len(rows) < 2:
            return ParseResult({}, "low", ["CSV has fewer than 2 rows."])

        # Find header row (first row with multiple non-empty cells)
        header_idx = 0
        for i, row in enumerate(rows):
            if len([c for c in row if c.strip()]) >= 3:
                header_idx = i
                break

        header = [c.strip() for c in rows[header_idx]]
        cr_col = _find_credit_col(header)
        narr_col = _find_narration_col(header)

        if cr_col is None:
            # Fallback: assume last or second-to-last column is credit
            cr_col = len(header) - 1
            warnings.append("Could not identify credit column — using last column as fallback.")

        if narr_col is None:
            narr_col = 1 if len(header) > 1 else 0
            warnings.append("Could not identify narration column — using column 2 as fallback.")

        for row in rows[header_idx + 1:]:
            if len(row) <= max(cr_col, narr_col):
                continue
            narration = row[narr_col].strip()
            credit = _parse_amount(row[cr_col])
            if credit <= 0:
                continue
            if _is_savings_interest(narration):
                entries.append({"type": "savings", "amount": credit, "narration": narration})
            elif _is_fd_interest(narration):
                entries.append({"type": "fd", "amount": credit, "narration": narration})

        return self._summarise(entries, warnings)

    def _summarise(self, entries: list[dict], warnings: list[str]) -> ParseResult:
        savings = sum(e["amount"] for e in entries if e["type"] == "savings")
        fd = sum(e["amount"] for e in entries if e["type"] == "fd")
        confidence = "high" if entries else "low"

        if not entries:
            warnings.append(
                "No interest entries found. Check that the statement covers the full financial year "
                "and that interest credit rows are present."
            )

        data = {
            "savings_interest": round(savings, 2),
            "fd_interest": round(fd, 2),
            "total_interest": round(savings + fd, 2),
            "entries": entries,
            "bank_detected": self.bank,
        }
        return ParseResult(data, confidence, warnings)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--bank", default="auto")
    args = parser.parse_args()
    result = BankStatementParser(args.file, args.bank).parse()
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
