"""Load YAML component-behavior rules and match normalized snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import Component


@dataclass(frozen=True)
class ComponentRule:
    name: str
    component_type: str
    match: tuple[str, ...]
    publishers: tuple[str, ...]
    paths: tuple[str, ...]
    action: str
    risk: str
    level: str

    def matches(self, component: Component) -> bool:
        if self.component_type and self.component_type != component.component_type:
            return False
        values = (component.name, component.publisher, component.path, component.source)
        folded = [value.casefold() for value in values if value]
        return bool(self.match and any(needle.casefold() in value for needle in self.match for value in folded)) or (
            bool(self.publishers) and any(needle.casefold() in component.publisher.casefold() for needle in self.publishers)
        ) or (
            bool(self.paths) and any(needle.casefold() in component.path.casefold() for needle in self.paths)
        )


class ComponentRuleSet:
    def __init__(self, rules: tuple[ComponentRule, ...]):
        self.rules = rules

    @classmethod
    def load(cls, directory: str | Path) -> "ComponentRuleSet":
        rules = []
        for path in sorted(Path(directory).glob("*.yaml")):
            document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            for entry in (document.get("rules", []) if isinstance(document, dict) else []):
                rules.append(ComponentRule(
                    str(entry.get("name", path.stem)),
                    str(entry.get("type", "")),
                    tuple(str(item) for item in entry.get("match", [])),
                    tuple(str(item) for item in entry.get("publisher", [])),
                    tuple(str(item) for item in entry.get("path", [])),
                    str(entry.get("action", "record")),
                    str(entry.get("risk", "S1")),
                    str(entry.get("level", "C0")),
                ))
        if not rules:
            raise ValueError(f"No component rules found in {directory}")
        return cls(tuple(rules))

    def match(self, component: Component) -> ComponentRule | None:
        return next((rule for rule in self.rules if rule.matches(component)), None)

