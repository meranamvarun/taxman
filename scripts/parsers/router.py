"""
Document type detector and parse router.

Detects document type from filename pattern and/or content keywords,
runs the appropriate parser, and returns a ParseResult.

CLI:
  python -m scripts.parsers.router path/to/document.pdf
  python -m scripts.parsers.router path/to/doc.pdf --type form16
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.parsers.base_parser import ParseResult
from scripts.parsers.form16_parser import Form16Parser
from scripts.parsers.form26as_parser import Form26ASParser
from scripts.parsers.ais_parser import AISParser
from scripts.parsers.bank_statement_parser import BankStatementParser
from scripts.parsers.broker_parser import BrokerParser
from scripts.parsers.investment_parser import InvestmentParser


FILENAME_PATTERNS = {
    "form16": ["form16", "form-16", "form_16", "16a", "16b", "tds certificate", "salary certificate"],
    "form26as": ["26as", "form26", "tds statement", "annual tax statement"],
    "ais": ["ais", "annual information", "ais_", "_ais"],
    "tis": ["tis", "taxpayer information"],
    "bank": ["statement", "bank", "passbook", "account"],
    "broker": ["pnl", "p&l", "profit", "zerodha", "groww", "upstox", "capital gain", "tradebook"],
    "investment": ["ppf", "lic", "elss", "nps", "health", "80c", "80d", "donation", "home loan", "homeloan", "nsc", "scss", "sukanya", "eduloan"],
}


def detect_type(file_path: str | Path, hint: str | None = None) -> str:
    if hint and hint != "auto":
        return hint.lower()

    name = Path(file_path).stem.lower()
    for doc_type, patterns in FILENAME_PATTERNS.items():
        if any(p in name for p in patterns):
            return doc_type

    return "unknown"


def route(file_path: str | Path, doc_type: str | None = None, **kwargs) -> ParseResult:
    """Detect document type and run the appropriate parser."""
    path = Path(file_path)
    dtype = detect_type(path, doc_type)

    parsers = {
        "form16": lambda: Form16Parser(path).parse(),
        "form26as": lambda: Form26ASParser(path).parse(),
        "ais": lambda: AISParser(path).parse(),
        "tis": lambda: AISParser(path).parse(),
        "bank": lambda: BankStatementParser(path, kwargs.get("bank", "auto")).parse(),
        "broker": lambda: BrokerParser(path, kwargs.get("broker", "auto")).parse(),
        "investment": lambda: InvestmentParser(path, kwargs.get("investment_type", "auto")).parse(),
    }

    if dtype not in parsers:
        return ParseResult(
            {},
            "low",
            [
                f"Could not detect document type from filename '{path.name}'. "
                "Use --type flag: form16 | form26as | ais | bank | broker | investment"
            ],
        )

    return parsers[dtype]()


def main():
    parser = argparse.ArgumentParser(description="Route a document to the correct parser")
    parser.add_argument("file")
    parser.add_argument("--type", default=None, help="Force document type")
    parser.add_argument("--bank", default="auto")
    parser.add_argument("--broker", default="auto")
    parser.add_argument("--investment-type", default="auto")
    args = parser.parse_args()

    dtype = detect_type(args.file, args.type)
    print(f"Detected type: {dtype}", file=sys.stderr)

    result = route(args.file, dtype, bank=args.bank, broker=args.broker, investment_type=args.investment_type)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
