"""Tests for document type detection router."""

from __future__ import annotations

import pytest

from scripts.parsers.router import detect_type


class TestDetectType:
    @pytest.mark.parametrize("filename,expected", [
        ("Form16_2024.pdf", "form16"),
        ("form-16-partb.pdf", "form16"),
        ("TDS_Certificate_Form_16.pdf", "form16"),
        ("26AS_2024-25.pdf", "form26as"),
        ("form26AS_annual.pdf", "form26as"),
        ("AIS_report.pdf", "ais"),
        ("TIS_2024.pdf", "tis"),
        ("SBI_bank_2024.pdf", "bank"),
        ("bank_passbook.pdf", "bank"),
        ("zerodha_pnl_2024.pdf", "broker"),
        ("Groww_Capital_Gain_Report.pdf", "broker"),
        ("PPF_receipt.pdf", "investment"),
        ("80C_proofs.pdf", "investment"),
        ("random_document.pdf", "unknown"),
    ])
    def test_filename_detection(self, filename, expected):
        assert detect_type(filename) == expected

    def test_hint_overrides_filename(self):
        assert detect_type("random.pdf", hint="form16") == "form16"

    def test_hint_auto_falls_through(self):
        assert detect_type("26AS_report.pdf", hint="auto") == "form26as"

    def test_case_insensitive(self):
        assert detect_type("FORM16_SALARY.PDF") == "form16"
