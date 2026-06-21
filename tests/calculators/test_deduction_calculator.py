"""Tests for HRA exemption and 80G deduction helpers."""

from __future__ import annotations

import pytest

from scripts.calculators.deduction_calculator import compute_hra_exemption, compute_80g_deduction


class TestHRAExemption:
    METRO = ["Mumbai", "Delhi", "Kolkata", "Chennai"]

    def test_metro_city_uses_50pct(self):
        result = compute_hra_exemption(
            hra_received=200_000,
            basic_salary=500_000,
            rent_paid=180_000,
            city="Mumbai",
            metro_cities=self.METRO,
        )
        assert result["is_metro"] is True
        assert result["limit_pct_basic"] == 250_000

    def test_non_metro_uses_40pct(self):
        result = compute_hra_exemption(
            hra_received=200_000,
            basic_salary=500_000,
            rent_paid=180_000,
            city="Pune",
            metro_cities=self.METRO,
        )
        assert result["is_metro"] is False
        assert result["limit_pct_basic"] == 200_000

    def test_exempt_is_minimum_of_three_limits(self):
        result = compute_hra_exemption(
            hra_received=100_000,
            basic_salary=600_000,
            rent_paid=150_000,
            city="Delhi",
            metro_cities=self.METRO,
        )
        # limit1=100k, limit2=300k, limit3=150k-60k=90k → min=90k
        assert result["exempt_amount"] == 90_000.0

    def test_zero_rent_gives_zero_exemption(self):
        result = compute_hra_exemption(
            hra_received=100_000,
            basic_salary=500_000,
            rent_paid=0,
            city="Delhi",
            metro_cities=self.METRO,
        )
        assert result["exempt_amount"] == 0.0
        assert result["taxable_hra"] == 100_000.0

    def test_rent_below_10pct_basic_gives_zero_limit3(self):
        result = compute_hra_exemption(
            hra_received=100_000,
            basic_salary=500_000,
            rent_paid=40_000,
            city="Chennai",
            metro_cities=self.METRO,
        )
        # limit3 = max(0, 40k - 50k) = 0
        assert result["limit_rent_minus_10pct"] == 0.0
        assert result["exempt_amount"] == 0.0

    def test_case_insensitive_metro_match(self):
        result = compute_hra_exemption(
            hra_received=100_000,
            basic_salary=500_000,
            rent_paid=100_000,
            city="mumbai",
            metro_cities=self.METRO,
        )
        assert result["is_metro"] is True


class TestCompute80G:
    def test_empty_list(self):
        assert compute_80g_deduction([]) == 0.0

    def test_single_donation_50pct(self):
        donations = [{"entity": "NGO", "amount": 10_000, "deductible_percent": 50}]
        assert compute_80g_deduction(donations) == 5_000.0

    def test_single_donation_100pct(self):
        donations = [{"entity": "PM CARES", "amount": 10_000, "deductible_percent": 100}]
        assert compute_80g_deduction(donations) == 10_000.0

    def test_multiple_donations(self):
        donations = [
            {"entity": "A", "amount": 10_000, "deductible_percent": 100},
            {"entity": "B", "amount": 20_000, "deductible_percent": 50},
        ]
        assert compute_80g_deduction(donations) == 20_000.0

    def test_defaults_to_50pct(self):
        donations = [{"entity": "X", "amount": 10_000}]
        assert compute_80g_deduction(donations) == 5_000.0
