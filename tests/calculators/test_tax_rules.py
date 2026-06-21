"""Tests for tax rules loader."""

from __future__ import annotations

import pytest

from scripts.calculators import tax_rules


class TestLoad:
    def test_load_ay2526(self):
        rules = tax_rules.load("25-26")
        assert rules["ay"] == "2025-26"
        assert "old_regime" in rules
        assert "new_regime" in rules

    def test_load_missing_ay_raises(self):
        with pytest.raises(FileNotFoundError, match="No tax rules file"):
            tax_rules.load("19-00")

    def test_load_validates_required_keys(self, tmp_path, monkeypatch):
        bad_file = tmp_path / "ay9900.json"
        bad_file.write_text('{"ay": "9999-00"}')
        monkeypatch.setattr(tax_rules, "RULES_DIR", tmp_path)
        with pytest.raises(ValueError, match="missing keys"):
            tax_rules.load("99-00")


class TestListAvailable:
    def test_returns_list(self):
        available = tax_rules.list_available()
        assert isinstance(available, list)
        assert "2025-26" in available

    def test_latest_ay(self):
        latest = tax_rules.latest_ay()
        assert isinstance(latest, str)
        assert "-" in latest
