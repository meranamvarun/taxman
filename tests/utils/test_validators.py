"""Tests for input validators."""

from __future__ import annotations

from datetime import date

import pytest

from scripts.utils.validators import (
    validate_pan,
    validate_ifsc,
    validate_ay,
    validate_dob,
    validate_mobile,
    validate_amount,
    taxpayer_category,
)


class TestValidatePAN:
    @pytest.mark.parametrize("pan", ["ABCDE1234F", "abcde1234f", " ABCDE1234F "])
    def test_valid(self, pan):
        ok, result = validate_pan(pan)
        assert ok is True
        assert result == "ABCDE1234F"

    @pytest.mark.parametrize("pan", ["ABCDE123F", "12345ABCDE", "", "ABCDE12345"])
    def test_invalid(self, pan):
        ok, _ = validate_pan(pan)
        assert ok is False


class TestValidateIFSC:
    def test_valid(self):
        ok, result = validate_ifsc("SBIN0001234")
        assert ok is True
        assert result == "SBIN0001234"

    @pytest.mark.parametrize("ifsc", ["SBIN1001234", "SBI00001234", ""])
    def test_invalid(self, ifsc):
        ok, _ = validate_ifsc(ifsc)
        assert ok is False


class TestValidateAY:
    @pytest.mark.parametrize("ay", ["2025-26", "2026-27", "2030-31"])
    def test_valid(self, ay):
        ok, _ = validate_ay(ay)
        assert ok is True

    def test_mismatched_end_year(self):
        ok, msg = validate_ay("2025-28")
        assert ok is False
        assert "mismatch" in msg.lower()

    def test_bad_format(self):
        ok, _ = validate_ay("2025")
        assert ok is False


class TestValidateDOB:
    def test_iso_format(self):
        ok, d, _ = validate_dob("1990-05-15")
        assert ok is True
        assert d == date(1990, 5, 15)

    def test_indian_format(self):
        ok, d, _ = validate_dob("15/05/1990")
        assert ok is True
        assert d == date(1990, 5, 15)

    def test_future_date_rejected(self):
        ok, _, msg = validate_dob("2099-01-01")
        assert ok is False
        assert "future" in msg.lower()

    def test_unparseable(self):
        ok, _, _ = validate_dob("not-a-date")
        assert ok is False


class TestValidateMobile:
    @pytest.mark.parametrize("mobile", ["9876543210", "+919876543210", "91 9876543210"])
    def test_valid(self, mobile):
        ok, digits = validate_mobile(mobile)
        assert ok is True
        assert len(digits) == 10

    @pytest.mark.parametrize("mobile", ["1234567890", "12345", ""])
    def test_invalid(self, mobile):
        ok, _ = validate_mobile(mobile)
        assert ok is False


class TestValidateAmount:
    def test_integer(self):
        ok, v, _ = validate_amount(1000)
        assert ok is True and v == 1000.0

    def test_string_with_commas(self):
        ok, v, _ = validate_amount("1,50,000")
        assert ok is True and v == 150_000.0

    def test_negative_rejected(self):
        ok, _, msg = validate_amount(-500)
        assert ok is False

    def test_non_numeric(self):
        ok, _, _ = validate_amount("abc")
        assert ok is False


class TestTaxpayerCategory:
    def test_general(self):
        assert taxpayer_category(date(1990, 1, 1), "2025-26") == "general"

    def test_senior(self):
        assert taxpayer_category(date(1963, 1, 1), "2025-26") == "senior"

    def test_super_senior(self):
        assert taxpayer_category(date(1940, 1, 1), "2025-26") == "super_senior"
