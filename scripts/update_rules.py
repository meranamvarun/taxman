"""
Annual tax rules updater.

Creates a new AY rules file from the previous year with guided prompts for
each changed value. Run this every year after the Finance Budget is passed.

Usage:
  python -m scripts.update_rules 2027-28
  python -m scripts.update_rules 2027-28 --from 2026-27
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from scripts.calculators import tax_rules

RULES_DIR = Path("scripts/calculators/rules")


def _ask(prompt: str, current_value, cast=None):
    display = json.dumps(current_value) if isinstance(current_value, (list, dict)) else str(current_value)
    user_input = input(f"  {prompt}\n  Current [{display}]: ").strip()
    if not user_input:
        return current_value
    if cast:
        try:
            return cast(user_input)
        except (ValueError, TypeError):
            print(f"  [Warning] Invalid input, keeping {display}")
            return current_value
    try:
        return json.loads(user_input)
    except json.JSONDecodeError:
        return user_input


def update_rules(new_ay: str, from_ay: str | None = None) -> None:
    # Load source rules
    source_ay = from_ay or tax_rules.latest_ay()
    try:
        source = tax_rules.load(source_ay)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    new_rules = copy.deepcopy(source)
    new_rules["ay"] = new_ay
    fy_start = int(new_ay[:4])
    new_rules["fy"] = f"{fy_start}-{str(fy_start+1)[-2:]}"

    print()
    print(f"=== Creating rules for AY {new_ay} (FY {new_rules['fy']}) ===")
    print(f"    Copying from AY {source_ay}")
    print()
    print("  Answer each prompt. Press Enter to keep current value.")
    print("  Enter valid JSON for arrays/objects. Numbers as plain digits.")
    print()

    # --- Metadata ---
    budget_date = input(f"  Budget date (YYYY-MM-DD) [{source.get('metadata', {}).get('budget_date', '')}]: ").strip()
    if budget_date:
        new_rules.setdefault("metadata", {})["budget_date"] = budget_date

    notes = input("  Brief summary of changes from previous year: ").strip()
    if notes:
        new_rules.setdefault("metadata", {})["notes"] = notes

    # --- Old regime ---
    print()
    print("  --- Old Regime ---")
    new_rules["old_regime"]["standard_deduction_salary"] = _ask(
        "Standard deduction (salary) [old regime]:",
        source["old_regime"]["standard_deduction_salary"], int
    )
    print("  Slabs (general) — enter as JSON array [{from, to, rate}] or press Enter to keep:")
    new_rules["old_regime"]["slabs_general"] = _ask("General slabs:", source["old_regime"]["slabs_general"])
    new_rules["old_regime"]["slabs_senior"] = _ask("Senior citizen slabs:", source["old_regime"]["slabs_senior"])
    new_rules["old_regime"]["slabs_super_senior"] = _ask("Super senior slabs:", source["old_regime"]["slabs_super_senior"])

    old_87a = source["old_regime"]["rebate_87a"]
    new_rules["old_regime"]["rebate_87a"]["max_income"] = _ask("87A max income [old regime]:", old_87a["max_income"], int)
    new_rules["old_regime"]["rebate_87a"]["max_rebate"] = _ask("87A max rebate [old regime]:", old_87a["max_rebate"], int)

    # --- New regime ---
    print()
    print("  --- New Regime ---")
    new_rules["new_regime"]["standard_deduction_salary"] = _ask(
        "Standard deduction (salary) [new regime]:",
        source["new_regime"]["standard_deduction_salary"], int
    )
    print("  New regime slabs — enter as JSON array or press Enter to keep:")
    new_rules["new_regime"]["slabs"] = _ask("New regime slabs:", source["new_regime"]["slabs"])

    new_87a = source["new_regime"]["rebate_87a"]
    new_rules["new_regime"]["rebate_87a"]["max_income"] = _ask("87A max income [new regime]:", new_87a["max_income"], int)
    new_rules["new_regime"]["rebate_87a"]["max_rebate"] = _ask("87A max rebate [new regime]:", new_87a["max_rebate"], int)

    # --- Capital Gains ---
    print()
    print("  --- Capital Gains Rates ---")
    cg = source["capital_gains"]
    new_rules["capital_gains"]["equity_stcg_rate"] = _ask("Equity STCG rate (%):", cg["equity_stcg_rate"], float)
    new_rules["capital_gains"]["equity_ltcg_rate"] = _ask("Equity LTCG rate (%):", cg["equity_ltcg_rate"], float)
    new_rules["capital_gains"]["equity_ltcg_exemption"] = _ask("LTCG equity exemption (₹):", cg["equity_ltcg_exemption"], int)

    # --- Deduction limits ---
    print()
    print("  --- Deduction Limits ---")
    lim = source["deduction_limits"]
    new_rules["deduction_limits"]["80C_max"] = _ask("80C max (₹):", lim["80C_max"], int)
    new_rules["deduction_limits"]["80CCD1B_max"] = _ask("80CCD1B max (₹):", lim["80CCD1B_max"], int)
    new_rules["deduction_limits"]["80D_self_below_60"] = _ask("80D self (below 60) max (₹):", lim["80D_self_below_60"], int)
    new_rules["deduction_limits"]["80D_self_senior"] = _ask("80D self (senior) max (₹):", lim["80D_self_senior"], int)
    new_rules["deduction_limits"]["80TTA_max"] = _ask("80TTA max (₹):", lim["80TTA_max"], int)
    new_rules["deduction_limits"]["80TTB_max"] = _ask("80TTB max (₹):", lim["80TTB_max"], int)

    # --- Cess ---
    new_rules["cess_rate"] = _ask("Health & Education Cess rate (%):", source["cess_rate"], float)

    # Save
    key = new_ay.replace("-", "")
    out_path = RULES_DIR / f"ay{key}.json"
    if out_path.exists():
        overwrite = input(f"\n  {out_path} already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            print("  Aborted.")
            sys.exit(0)

    with out_path.open("w") as f:
        json.dump(new_rules, f, indent=2)

    print()
    print(f"  Saved: {out_path}")
    print(f"  Review the file and correct any JSON before using with /tax-init {new_ay}")


def main():
    parser = argparse.ArgumentParser(description="Create new AY tax rules from previous year")
    parser.add_argument("new_ay", help="New Assessment Year, e.g. 2027-28")
    parser.add_argument("--from", dest="from_ay", default=None, help="Source AY (default: latest)")
    args = parser.parse_args()

    from scripts.utils.validators import validate_ay
    ok, msg = validate_ay(args.new_ay)
    if not ok:
        print(f"Error: {msg}")
        sys.exit(1)

    update_rules(args.new_ay, args.from_ay)


if __name__ == "__main__":
    main()
