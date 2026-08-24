"""YAML-driven protection and target-scope policy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import MigrationPlanError


PROTECTION_LEVELS = {"P0", "P1", "P2", "P3", "P4"}
POLICY_ACTIONS = {"ignore", "report_only", "review", "analyze"}


@dataclass(frozen=True)
class ProtectionDecision:
    protection: str
    action: str
    reason: str


@dataclass(frozen=True)
class ProtectionRule:
    protection: str
    action: str
    reason: str
    names: tuple[str, ...]
    categories: tuple[str, ...]
    families: tuple[str, ...]

    def matches(self, profile: dict) -> bool:
        name = str(profile.get("name", "")).casefold()
        category = str(profile.get("category", "")).casefold()
        family = str(profile.get("family", "")).casefold()
        return (
            any(candidate.casefold() in name for candidate in self.names)
            or category in {candidate.casefold() for candidate in self.categories}
            or family in {candidate.casefold() for candidate in self.families}
        )


class ProtectionPolicy:
    def __init__(self, rules: tuple[ProtectionRule, ...]):
        self.rules = rules

    @classmethod
    def load(cls, directory: str | Path) -> "ProtectionPolicy":
        rule_dir = Path(directory)
        rules = []
        for path in sorted(rule_dir.glob("*.yaml")):
            try:
                document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise MigrationPlanError(f"Cannot load protection rule {path}: {exc}") from exc
            entries = document.get("rules", []) if isinstance(document, dict) else []
            for entry in entries:
                protection = str(entry.get("protection", ""))
                action = str(entry.get("action", ""))
                if protection not in PROTECTION_LEVELS or action not in POLICY_ACTIONS:
                    raise MigrationPlanError(f"Invalid protection rule in {path}")
                rules.append(
                    ProtectionRule(
                        protection,
                        action,
                        str(entry.get("reason", "")),
                        tuple(str(value) for value in entry.get("names", [])),
                        tuple(str(value) for value in entry.get("categories", [])),
                        tuple(str(value) for value in entry.get("families", [])),
                    )
                )
        if not rules:
            raise MigrationPlanError(f"No software protection rules found in {rule_dir}")
        return cls(tuple(rules))

    def evaluate(self, profile: dict) -> ProtectionDecision:
        matches = [rule for rule in self.rules if rule.matches(profile)]
        if not matches:
            return ProtectionDecision("P2", "report_only", "Normal software outside the target scope.")
        # P0/P1 protection always wins. Otherwise assess explicitly targeted P4
        # before P3 review candidates.
        priority = {"P0": 50, "P1": 40, "P4": 30, "P3": 20, "P2": 10}
        selected = max(matches, key=lambda rule: priority[rule.protection])
        return ProtectionDecision(selected.protection, selected.action, selected.reason)

