"""
State manager — atomic read/write of state/session.json.

CLI usage:
  python -m scripts.utils.state_manager init --ay 2026-27 --pan ABCDE1234F ...
  python -m scripts.utils.state_manager status
  python -m scripts.utils.state_manager checkpoint --name form16_parsed
  python -m scripts.utils.state_manager get income.salary.gross
  python -m scripts.utils.state_manager set income.salary.gross 1200000
  python -m scripts.utils.state_manager backup
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_PATH = Path("state/session.json")
BACKUP_DIR = Path("state")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_state(ay: str, pan: str, name: str) -> dict:
    fy_start = int(ay[:4])
    fy = f"{fy_start}-{str(fy_start + 1)[-2:]}"
    return {
        "version": 1,
        "session": {
            "id": str(uuid.uuid4()),
            "created": _now(),
            "last_updated": _now(),
            "ay": ay,
            "fy": fy,
        },
        "taxpayer": {
            "pan": pan.upper(),
            "name": name,
            "dob": None,
            "mobile": None,
            "email": None,
            "residential_status": "resident",
            "is_senior_citizen": False,
            "is_super_senior_citizen": False,
            "bank": {"account_number": None, "ifsc": None, "bank_name": None},
            "aadhaar_last4": None,
            "address": {},
        },
        "itr_form": None,
        "regime_elected": None,
        "documents_processed": [],
        "income": {
            "salary": {
                "employers": [],
                "gross": 0,
                "standard_deduction": 0,
                "professional_tax": 0,
                "net": 0,
                "total_tds": 0,
            },
            "house_property": {"properties": [], "net": 0},
            "capital_gains": {
                "equity_stcg": 0,
                "equity_ltcg": 0,
                "debt_stcg": 0,
                "debt_ltcg": 0,
                "property_stcg": 0,
                "property_ltcg": 0,
                "gold_stcg": 0,
                "gold_ltcg": 0,
                "vda": 0,
                "other_stcg": 0,
                "other_ltcg": 0,
            },
            "other_sources": {
                "savings_interest": 0,
                "fd_interest": 0,
                "dividend": 0,
                "other": 0,
            },
            "foreign_source": {
                "salary": 0,
                "business": 0,
                "capital_gains": 0,
                "other": 0,
            },
        },
        "deductions": {
            "80C": 0,
            "80CCC": 0,
            "80CCD1": 0,
            "80CCD1B": 0,
            "80CCD2": 0,
            "80D_self": 0,
            "80D_parents": 0,
            "80E": 0,
            "80G": [],
            "80TTA": 0,
            "80TTB": 0,
            "80EEA": 0,
            "HRA_exempt": 0,
            "LTA_exempt": 0,
        },
        "tds_credits": [],
        "advance_tax_paid": [],
        "self_assessment_tax_paid": [],
        "discrepancies": [],
        "foreign_assets": {
            "bank_accounts": [],
            "custodial_accounts": [],
            "equity_debt": [],
            "immovable_property": [],
            "other_assets": [],
            "trusts": [],
            "dtaa_relief": [],
        },
        "prior_year_losses": {
            "equity_stcl": 0,
            "other_stcl": 0,
            "other_ltcl": 0,
            "house_property_loss": 0,
        },
        "tax_computation": {
            "old": {
                "taxable_income": 0,
                "slab_tax": 0,
                "special_rate_tax": 0,
                "rebate_87a": 0,
                "surcharge": 0,
                "cess": 0,
                "total_tax": 0,
                "tds_paid": 0,
                "advance_tax_paid": 0,
                "balance": 0,
            },
            "new": {
                "taxable_income": 0,
                "slab_tax": 0,
                "special_rate_tax": 0,
                "rebate_87a": 0,
                "surcharge": 0,
                "cess": 0,
                "total_tax": 0,
                "tds_paid": 0,
                "advance_tax_paid": 0,
                "balance": 0,
            },
            "recommended_regime": None,
        },
        "filing": {
            "status": "not_started",
            "is_revised": False,
            "original_ack": None,
            "is_belated": False,
            "portal_paused_at": None,
            "ack_number": None,
            "submitted_at": None,
        },
        "checkpoints": [],
        "manually_overridden": [],
    }


def load() -> dict:
    if not STATE_PATH.exists():
        print("No session found. Run /tax-init to start.", file=sys.stderr)
        sys.exit(1)
    with STATE_PATH.open() as f:
        return json.load(f)


def save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["session"]["last_updated"] = _now()
    tmp = STATE_PATH.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp.replace(STATE_PATH)


def init(ay: str, pan: str, name: str, **kwargs) -> dict:
    state = _empty_state(ay, pan, name)
    for key, val in kwargs.items():
        if val is not None:
            _set_path(state, key.replace("-", "_").replace("__", "."), val)
    save(state)
    return state


def backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"session_backup_{ts}.json"
    shutil.copy2(STATE_PATH, dest)
    return dest


def add_checkpoint(state: dict, name: str, description: str = "") -> None:
    state["checkpoints"].append(
        {"name": name, "description": description, "timestamp": _now()}
    )


def add_document(state: dict, doc_type: str, file_path: str, confidence: str, summary: dict) -> None:
    state["documents_processed"].append(
        {
            "type": doc_type,
            "file": file_path,
            "confidence": confidence,
            "summary": summary,
            "parsed_at": _now(),
        }
    )


def add_discrepancy(state: dict, field: str, source_a: str, value_a, source_b: str, value_b, resolved: bool = False, resolution: str = "") -> None:
    state["discrepancies"].append(
        {
            "field": field,
            "source_a": source_a,
            "value_a": value_a,
            "source_b": source_b,
            "value_b": value_b,
            "resolved": resolved,
            "resolution": resolution,
            "detected_at": _now(),
        }
    )


def _get_path(obj: dict, path: str) -> Any:
    parts = path.split(".")
    cur = obj
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def _set_path(obj: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def progress_summary(state: dict) -> dict:
    docs = {d["type"] for d in state["documents_processed"]}
    return {
        "ay": state["session"]["ay"],
        "taxpayer": state["taxpayer"]["name"],
        "pan": state["taxpayer"]["pan"],
        "itr_form": state["itr_form"],
        "regime_elected": state["regime_elected"],
        "documents_parsed": sorted(docs),
        "filing_status": state["filing"]["status"],
        "checkpoints_done": [c["name"] for c in state["checkpoints"]],
        "discrepancies_unresolved": sum(
            1 for d in state["discrepancies"] if not d["resolved"]
        ),
        "last_updated": state["session"]["last_updated"],
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Taxman state manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--ay", required=True)
    p_init.add_argument("--pan", required=True)
    p_init.add_argument("--name", required=True)
    p_init.add_argument("--dob")
    p_init.add_argument("--mobile")
    p_init.add_argument("--email")
    p_init.add_argument("--residential-status", default="resident")
    p_init.add_argument("--itr-form")

    sub.add_parser("status")
    sub.add_parser("backup")

    p_cp = sub.add_parser("checkpoint")
    p_cp.add_argument("--name", required=True)
    p_cp.add_argument("--description", default="")

    p_get = sub.add_parser("get")
    p_get.add_argument("path")

    p_set = sub.add_parser("set")
    p_set.add_argument("path")
    p_set.add_argument("value")

    args = parser.parse_args()

    if args.cmd == "init":
        kwargs = {k: v for k, v in vars(args).items() if k not in ("cmd", "ay", "pan", "name") and v is not None}
        state = init(args.ay, args.pan, args.name, **kwargs)
        print(json.dumps(progress_summary(state), indent=2))

    elif args.cmd == "status":
        state = load()
        print(json.dumps(progress_summary(state), indent=2))

    elif args.cmd == "backup":
        dest = backup()
        print(f"Backed up to {dest}")

    elif args.cmd == "checkpoint":
        state = load()
        add_checkpoint(state, args.name, args.description)
        save(state)
        print(f"Checkpoint '{args.name}' saved.")

    elif args.cmd == "get":
        state = load()
        val = _get_path(state, args.path)
        print(json.dumps(val, indent=2))

    elif args.cmd == "set":
        state = load()
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        _set_path(state, args.path, value)
        state["manually_overridden"].append(
            {"path": args.path, "value": value, "at": _now()}
        )
        save(state)
        print(f"Set {args.path} = {value}")


if __name__ == "__main__":
    _cli()
