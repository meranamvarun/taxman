"""Shared fixtures for taxman tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.calculators import tax_rules


RULES_DIR = Path(__file__).parent.parent / "scripts" / "calculators" / "rules"


@pytest.fixture
def ay2526_rules() -> dict:
    return tax_rules.load("25-26")


@pytest.fixture
def minimal_income() -> dict:
    return {
        "salary": {"gross": 0, "professional_tax": 0, "total_tds": 0},
        "house_property": {"net": 0},
        "capital_gains": {
            "equity_stcg": 0, "equity_ltcg": 0,
            "debt_stcg": 0, "debt_ltcg": 0,
            "property_stcg": 0, "property_ltcg": 0,
            "gold_stcg": 0, "gold_ltcg": 0,
            "vda": 0, "other_stcg": 0, "other_ltcg": 0,
        },
        "other_sources": {"savings_interest": 0, "fd_interest": 0, "dividend": 0, "other": 0},
        "foreign_source": {},
        "advance_tax_entries": [],
    }


@pytest.fixture
def zero_deductions() -> dict:
    return {
        "80C": 0, "80CCC": 0, "80CCD1": 0, "80CCD1B": 0, "80CCD2": 0,
        "80D_self": 0, "80D_parents": 0, "80E": 0, "80G": [],
        "80TTA": 0, "80TTB": 0, "HRA_exempt": 0, "LTA_exempt": 0,
    }


@pytest.fixture
def sample_state() -> dict:
    return {
        "version": 1,
        "session": {
            "id": "test-session-id",
            "created": "2025-01-01T00:00:00+00:00",
            "last_updated": "2025-01-01T00:00:00+00:00",
            "ay": "2025-26",
            "fy": "2024-25",
        },
        "taxpayer": {
            "pan": "ABCDE1234F",
            "name": "Test User",
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
            "salary": {"employers": [], "gross": 0, "standard_deduction": 0,
                       "professional_tax": 0, "net": 0, "total_tds": 0},
            "house_property": {"properties": [], "net": 0},
            "capital_gains": {
                "equity_stcg": 0, "equity_ltcg": 0, "debt_stcg": 0, "debt_ltcg": 0,
                "property_stcg": 0, "property_ltcg": 0, "gold_stcg": 0, "gold_ltcg": 0,
                "vda": 0, "other_stcg": 0, "other_ltcg": 0,
            },
            "other_sources": {"savings_interest": 0, "fd_interest": 0, "dividend": 0, "other": 0},
            "foreign_source": {},
        },
        "deductions": {
            "80C": 0, "80CCC": 0, "80CCD1": 0, "80CCD1B": 0, "80CCD2": 0,
            "80D_self": 0, "80D_parents": 0, "80E": 0, "80G": [],
            "80TTA": 0, "80TTB": 0, "80EEA": 0, "HRA_exempt": 0, "LTA_exempt": 0,
        },
        "tds_credits": [],
        "advance_tax_paid": [],
        "self_assessment_tax_paid": [],
        "discrepancies": [],
        "foreign_assets": {
            "bank_accounts": [], "custodial_accounts": [], "equity_debt": [],
            "immovable_property": [], "other_assets": [], "trusts": [], "dtaa_relief": [],
        },
        "prior_year_losses": {
            "equity_stcl": 0, "other_stcl": 0, "other_ltcl": 0, "house_property_loss": 0,
        },
        "tax_computation": {
            "old": {"taxable_income": 0, "slab_tax": 0, "special_rate_tax": 0,
                    "rebate_87a": 0, "surcharge": 0, "cess": 0, "total_tax": 0,
                    "tds_paid": 0, "advance_tax_paid": 0, "balance": 0},
            "new": {"taxable_income": 0, "slab_tax": 0, "special_rate_tax": 0,
                    "rebate_87a": 0, "surcharge": 0, "cess": 0, "total_tax": 0,
                    "tds_paid": 0, "advance_tax_paid": 0, "balance": 0},
            "recommended_regime": None,
        },
        "filing": {
            "status": "not_started", "is_revised": False, "original_ack": None,
            "is_belated": False, "portal_paused_at": None,
            "ack_number": None, "submitted_at": None,
        },
        "checkpoints": [],
        "manually_overridden": [],
    }
