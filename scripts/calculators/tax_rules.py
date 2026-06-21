"""Load and validate tax rules for a given Assessment Year."""

from __future__ import annotations

import json
from pathlib import Path

RULES_DIR = Path(__file__).parent / "rules"


def load(ay: str) -> dict:
    """Load rules for the given AY. Raises FileNotFoundError if no rules file exists."""
    key = ay.replace("-", "")
    candidates = [
        RULES_DIR / f"ay{key}.json",
        RULES_DIR / f"ay{key.lower()}.json",
    ]
    for path in candidates:
        if path.exists():
            with path.open() as f:
                rules = json.load(f)
            _validate(rules, ay)
            return rules
    available = list_available()
    raise FileNotFoundError(
        f"No tax rules file for AY {ay}. "
        f"Available: {available}. "
        f"Run /tax-update-rules {ay} to create one."
    )


def list_available() -> list[str]:
    """Return sorted list of AYs that have rules files."""
    result = []
    for path in sorted(RULES_DIR.glob("ay*.json")):
        try:
            with path.open() as f:
                data = json.load(f)
            result.append(data.get("ay", path.stem))
        except Exception:
            pass
    return result


def latest_ay() -> str:
    """Return the most recent AY with a rules file."""
    avail = list_available()
    if not avail:
        raise RuntimeError("No tax rules files found.")
    return sorted(avail)[-1]


def _validate(rules: dict, ay: str) -> None:
    required = ["ay", "old_regime", "new_regime", "capital_gains", "deduction_limits", "cess_rate"]
    missing = [k for k in required if k not in rules]
    if missing:
        raise ValueError(f"Rules file for {ay} is missing keys: {missing}")
