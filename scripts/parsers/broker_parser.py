"""
Broker P&L parser — capital gains from equity / MF trading.

Hard-coded support:
  - Zerodha Console P&L CSV  (console.zerodha.com → P&L → Download)
  - Groww P&L CSV            (groww.in → Reports → P&L → Download)
  - Generic CSV              (user maps columns manually via --map flag)

Output categories:
  equity_stcg, equity_ltcg,
  debt_stcg, debt_ltcg,
  gold_stcg, gold_ltcg,
  other_stcg, other_ltcg

CLI:
  python -m scripts.parsers.broker_parser path/to/pnl.csv [--broker zerodha|groww|auto]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from scripts.parsers.base_parser import BaseParser, ParseResult


def _parse_amount(s: str) -> float:
    s = re.sub(r"[₹,\s\(\)]", "", str(s))
    if not s:
        return 0.0
    try:
        v = float(s)
        return v
    except ValueError:
        return 0.0


def _empty_gains() -> dict:
    return {
        "equity_stcg": 0.0, "equity_ltcg": 0.0,
        "debt_stcg": 0.0, "debt_ltcg": 0.0,
        "gold_stcg": 0.0, "gold_ltcg": 0.0,
        "other_stcg": 0.0, "other_ltcg": 0.0,
    }


# ---------------------------------------------------------------------------
# Zerodha Console P&L CSV format
# ---------------------------------------------------------------------------

ZERODHA_EQUITY_INSTRUMENTS = {"EQ", "BE", "BL"}
ZERODHA_EQUITY_MF_KEYWORDS = ["equity", "elss", "large cap", "mid cap", "small cap", "flexi", "multi cap", "nifty", "sensex", "index"]
ZERODHA_DEBT_MF_KEYWORDS = ["debt", "liquid", "overnight", "ultra short", "money market", "gilt", "banking psu", "bond"]
ZERODHA_GOLD_KEYWORDS = ["gold", "sgb", "sovereign gold"]


def _zerodha_classify(row: dict) -> str:
    segment = row.get("Segment", row.get("segment", "")).strip().upper()
    scrip = row.get("Script", row.get("scrip", row.get("Symbol", row.get("symbol", "")))).strip().lower()

    if segment in ZERODHA_EQUITY_INSTRUMENTS or segment == "EQ":
        return "equity"
    if "MF" in segment or "MUTUAL" in segment:
        if any(k in scrip for k in ZERODHA_DEBT_MF_KEYWORDS):
            return "debt_mf"
        if any(k in scrip for k in ZERODHA_GOLD_KEYWORDS):
            return "gold"
        return "equity_mf"
    if any(k in scrip for k in ZERODHA_GOLD_KEYWORDS):
        return "gold"
    return "other"


def _parse_zerodha(rows: list[dict]) -> tuple[dict, list[str]]:
    gains = _empty_gains()
    warnings = []

    for row in rows:
        # Zerodha P&L CSV has: Symbol, ISIN, Qty, Buy Avg, Buy Value, Sell Avg, Sell Value,
        #                       Realised P&L, Holding Period (days or 'Long Term')
        pnl_raw = row.get("Realised P&L", row.get("P&L", row.get("Profit/Loss", "")))
        pnl = _parse_amount(pnl_raw)

        holding = str(row.get("Holding Period", row.get("holding_period", ""))).strip().lower()
        is_long = "long" in holding or "ltcg" in holding

        category = _zerodha_classify(row)

        if category in ("equity", "equity_mf"):
            if is_long:
                gains["equity_ltcg"] += pnl
            else:
                gains["equity_stcg"] += pnl
        elif category == "debt_mf":
            if is_long:
                gains["debt_ltcg"] += pnl
            else:
                gains["debt_stcg"] += pnl
        elif category == "gold":
            if is_long:
                gains["gold_ltcg"] += pnl
            else:
                gains["gold_stcg"] += pnl
        else:
            if is_long:
                gains["other_ltcg"] += pnl
            else:
                gains["other_stcg"] += pnl

    return gains, warnings


# ---------------------------------------------------------------------------
# Groww P&L CSV format
# ---------------------------------------------------------------------------

GROWW_TYPE_MAP = {
    "STOCKS": "equity",
    "EQUITY": "equity",
    "EQUITY MUTUAL FUNDS": "equity_mf",
    "DEBT MUTUAL FUNDS": "debt_mf",
    "GOLD MUTUAL FUNDS": "gold",
    "INTERNATIONAL": "other",
    "DIGITAL GOLD": "gold",
}


def _parse_groww(rows: list[dict]) -> tuple[dict, list[str]]:
    gains = _empty_gains()
    warnings = []

    for row in rows:
        pnl = _parse_amount(row.get("Realised P&L", row.get("Gain/Loss", "")))
        gain_type = str(row.get("Gain Type", row.get("Term", ""))).strip().upper()
        asset_type = str(row.get("Asset Type", row.get("Instrument Type", ""))).strip().upper()

        is_long = "LONG" in gain_type or "LTCG" in gain_type
        category = GROWW_TYPE_MAP.get(asset_type, "other")

        if category in ("equity", "equity_mf"):
            if is_long:
                gains["equity_ltcg"] += pnl
            else:
                gains["equity_stcg"] += pnl
        elif category == "debt_mf":
            if is_long:
                gains["debt_ltcg"] += pnl
            else:
                gains["debt_stcg"] += pnl
        elif category == "gold":
            if is_long:
                gains["gold_ltcg"] += pnl
            else:
                gains["gold_stcg"] += pnl
        else:
            if is_long:
                gains["other_ltcg"] += pnl
            else:
                gains["other_stcg"] += pnl

    return gains, warnings


# ---------------------------------------------------------------------------
# Auto-detect broker from CSV header
# ---------------------------------------------------------------------------

def _detect_broker(header: list[str]) -> str:
    h = {c.strip().lower() for c in header}
    if "holding period" in h and "realised p&l" in h and "segment" in h:
        return "zerodha"
    if "gain type" in h and "asset type" in h:
        return "groww"
    return "generic"


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------

class BrokerParser(BaseParser):
    def __init__(self, file_path, broker: str = "auto"):
        super().__init__(file_path)
        self.broker = broker.lower()

    @classmethod
    def doc_type(cls) -> str:
        return "broker"

    def parse(self) -> ParseResult:
        warnings = []
        try:
            rows, header = self._read_csv()
        except Exception as e:
            return ParseResult({}, "low", [f"Could not read CSV: {e}"])

        if not rows:
            return ParseResult(_empty_gains(), "low", ["CSV has no data rows."])

        broker = self.broker if self.broker != "auto" else _detect_broker(header)

        if broker == "zerodha":
            gains, w = _parse_zerodha(rows)
        elif broker == "groww":
            gains, w = _parse_groww(rows)
        else:
            warnings.append(
                f"Unknown broker format. Falling back to generic parser. "
                "Map columns: 'pnl', 'is_long_term', 'asset_type' expected in CSV headers."
            )
            gains, w = self._parse_generic(rows)

        warnings.extend(w)
        gains = {k: round(v, 2) for k, v in gains.items()}
        has_data = any(v != 0 for v in gains.values())

        data = {
            "broker_detected": broker,
            "gains": gains,
            "total_stcg": round(sum(v for k, v in gains.items() if "stcg" in k), 2),
            "total_ltcg": round(sum(v for k, v in gains.items() if "ltcg" in k), 2),
        }

        confidence = "high" if (has_data and broker in ("zerodha", "groww")) else "medium" if has_data else "low"
        return ParseResult(data, confidence, warnings)

    def _read_csv(self) -> tuple[list[dict], list[str]]:
        try:
            with self.file_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])
        except UnicodeDecodeError:
            with self.file_path.open(newline="", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])

    def _parse_generic(self, rows: list[dict]) -> tuple[dict, list[str]]:
        gains = _empty_gains()
        warnings = ["Generic parser: assuming columns named 'pnl', 'is_long', 'asset_type'."]
        for row in rows:
            pnl = _parse_amount(row.get("pnl", row.get("P&L", 0)))
            is_long = str(row.get("is_long", "")).lower() in ("true", "yes", "1", "long")
            asset = str(row.get("asset_type", "equity")).lower()
            key = f"{asset}_{'ltcg' if is_long else 'stcg'}"
            if key in gains:
                gains[key] += pnl
            else:
                gains["other_ltcg" if is_long else "other_stcg"] += pnl
        return gains, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--broker", default="auto", choices=["zerodha", "groww", "auto", "generic"])
    args = parser.parse_args()
    result = BrokerParser(args.file, args.broker).parse()
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
