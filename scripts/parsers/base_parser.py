"""Abstract base class for all document parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ParseResult:
    def __init__(self, data: dict, confidence: str, warnings: list[str], raw_fields: dict | None = None):
        assert confidence in ("high", "medium", "low"), f"Bad confidence: {confidence}"
        self.data = data
        self.confidence = confidence
        self.warnings = warnings
        self.raw_fields = raw_fields or {}

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }

    def ok(self) -> bool:
        return self.confidence in ("high", "medium")


class BaseParser(ABC):
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

    @abstractmethod
    def parse(self) -> ParseResult:
        """Parse the document and return a ParseResult."""

    @classmethod
    def doc_type(cls) -> str:
        """Return canonical document type string."""
        return cls.__name__.lower().replace("parser", "")
