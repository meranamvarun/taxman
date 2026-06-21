"""Tests for state manager — init, load, save, get/set, checkpoint, backup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.utils import state_manager


@pytest.fixture(autouse=True)
def isolate_state(tmp_path, monkeypatch):
    """Redirect state file and backup dir to a temp directory for every test."""
    state_file = tmp_path / "session.json"
    monkeypatch.setattr(state_manager, "STATE_PATH", state_file)
    monkeypatch.setattr(state_manager, "BACKUP_DIR", tmp_path)
    return tmp_path


class TestInit:
    def test_creates_state_file(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test User")
        assert state_manager.STATE_PATH.exists()
        assert state["taxpayer"]["pan"] == "ABCDE1234F"
        assert state["session"]["ay"] == "2025-26"
        assert state["session"]["fy"] == "2025-26"

    def test_pan_uppercased(self, isolate_state):
        state = state_manager.init("2025-26", "abcde1234f", "Test")
        assert state["taxpayer"]["pan"] == "ABCDE1234F"

    def test_extra_kwargs_set(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test", taxpayer__dob="1990-01-01")
        assert state["taxpayer"]["dob"] == "1990-01-01"


class TestLoadSave:
    def test_load_after_init(self, isolate_state):
        state_manager.init("2025-26", "ABCDE1234F", "Test")
        loaded = state_manager.load()
        assert loaded["taxpayer"]["name"] == "Test"

    def test_save_updates_timestamp(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test")
        old_ts = state["session"]["last_updated"]
        state["taxpayer"]["name"] = "Updated"
        state_manager.save(state)
        reloaded = state_manager.load()
        assert reloaded["taxpayer"]["name"] == "Updated"
        assert reloaded["session"]["last_updated"] >= old_ts

    def test_load_without_init_exits(self, isolate_state):
        with pytest.raises(SystemExit):
            state_manager.load()


class TestGetSetPath:
    def test_get_nested(self):
        obj = {"a": {"b": {"c": 42}}}
        assert state_manager._get_path(obj, "a.b.c") == 42

    def test_get_missing_returns_none(self):
        assert state_manager._get_path({"a": 1}, "b.c") is None

    def test_set_nested(self):
        obj = {"a": {"b": 1}}
        state_manager._set_path(obj, "a.b", 99)
        assert obj["a"]["b"] == 99

    def test_set_creates_intermediate(self):
        obj = {}
        state_manager._set_path(obj, "x.y.z", "hello")
        assert obj["x"]["y"]["z"] == "hello"


class TestCheckpoint:
    def test_add_checkpoint(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test")
        state_manager.add_checkpoint(state, "form16_parsed", "Parsed Form 16")
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["name"] == "form16_parsed"

    def test_multiple_checkpoints(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test")
        state_manager.add_checkpoint(state, "cp1")
        state_manager.add_checkpoint(state, "cp2")
        assert len(state["checkpoints"]) == 2


class TestAddDocument:
    def test_add_document(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test")
        state_manager.add_document(state, "form16", "form16.pdf", "high", {"gross": 1000000})
        assert len(state["documents_processed"]) == 1
        assert state["documents_processed"][0]["type"] == "form16"


class TestAddDiscrepancy:
    def test_add_discrepancy(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test")
        state_manager.add_discrepancy(
            state, "salary.gross", "form16", 1000000, "26as", 1100000,
        )
        assert len(state["discrepancies"]) == 1
        assert state["discrepancies"][0]["resolved"] is False


class TestBackup:
    def test_creates_backup_file(self, isolate_state):
        state_manager.init("2025-26", "ABCDE1234F", "Test")
        dest = state_manager.backup()
        assert dest.exists()
        assert "backup" in dest.name


class TestProgressSummary:
    def test_summary_fields(self, isolate_state):
        state = state_manager.init("2025-26", "ABCDE1234F", "Test User")
        summary = state_manager.progress_summary(state)
        assert summary["ay"] == "2025-26"
        assert summary["taxpayer"] == "Test User"
        assert summary["filing_status"] == "not_started"
        assert summary["discrepancies_unresolved"] == 0
