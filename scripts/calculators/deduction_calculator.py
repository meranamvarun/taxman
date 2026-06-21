"""
HRA and deduction helpers.

HRA Exemption (u/s 10(13A)) — least of:
  1. Actual HRA received
  2. 50% of basic (metro) or 40% of basic (non-metro)
  3. Rent paid - 10% of basic salary
"""

from __future__ import annotations


def compute_hra_exemption(
    hra_received: float,
    basic_salary: float,
    rent_paid: float,
    city: str,
    metro_cities: list[str],
) -> dict:
    is_metro = any(city.lower() == m.lower() for m in metro_cities)
    pct = 50 if is_metro else 40

    limit1 = hra_received
    limit2 = basic_salary * pct / 100
    limit3 = max(0.0, rent_paid - basic_salary * 0.10)
    exempt = min(limit1, limit2, limit3)

    return {
        "hra_received": hra_received,
        "limit_actual_hra": limit1,
        "limit_pct_basic": limit2,
        "limit_rent_minus_10pct": limit3,
        "exempt_amount": round(exempt, 2),
        "taxable_hra": round(hra_received - exempt, 2),
        "is_metro": is_metro,
    }


def compute_80g_deduction(donations: list[dict]) -> float:
    """Compute total 80G deduction from list of {entity, amount, deductible_percent, with_limit}."""
    total = 0.0
    for d in donations:
        pct = d.get("deductible_percent", 50)
        total += d.get("amount", 0) * pct / 100
    return round(total, 2)
