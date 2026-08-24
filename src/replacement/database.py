"""Validated in-memory replacement database."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CONFIDENCE_LEVELS = {"high", "medium", "low"}


class ReplacementDatabaseError(ValueError):
    """Raised when replacement data does not satisfy its schema."""


@dataclass(frozen=True)
class ReplacementData:
    replacements: dict[str, dict[str, Any]]
    categories: dict[str, dict[str, Any]]
    verification_rules: dict[str, dict[str, Any]]

    def validate(self) -> None:
        for key, entry in self.replacements.items():
            if not isinstance(entry, dict):
                raise ReplacementDatabaseError(f"Replacement entry {key!r} must be an object")
            required = {"name", "category", "function", "replacement"}
            missing = required.difference(entry)
            if missing:
                raise ReplacementDatabaseError(f"Replacement entry {key!r} is missing {sorted(missing)}")
            category = entry["category"]
            if category not in self.categories or category not in self.verification_rules:
                raise ReplacementDatabaseError(f"Unknown category {category!r} in {key!r}")
            if not isinstance(entry["function"], list) or not entry["function"]:
                raise ReplacementDatabaseError(f"Entry {key!r} needs at least one function")
            if not isinstance(entry["replacement"], list) or not entry["replacement"]:
                raise ReplacementDatabaseError(f"Entry {key!r} needs at least one replacement")
            allowed_tests = set(self.verification_rules[category].get("tests", []))
            for suggestion in entry["replacement"]:
                fields = {"name", "type", "official_website", "verification", "confidence"}
                if not isinstance(suggestion, dict) or fields.difference(suggestion):
                    raise ReplacementDatabaseError(f"Invalid suggestion in {key!r}")
                if suggestion["confidence"] not in CONFIDENCE_LEVELS:
                    raise ReplacementDatabaseError(f"Invalid confidence in {key!r}")
                unknown_tests = set(suggestion["verification"]).difference(allowed_tests)
                if unknown_tests:
                    raise ReplacementDatabaseError(f"Unknown verification tests in {key!r}: {sorted(unknown_tests)}")

