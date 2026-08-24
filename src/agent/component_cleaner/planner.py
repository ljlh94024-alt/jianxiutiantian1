"""Create fail-closed component plans; default maximum is C2."""

from __future__ import annotations

from collections.abc import Iterable

from .matcher import ComponentRuleSet
from .models import Component, ComponentPlan


class ComponentPlanner:
    PROTECTED_PUBLISHERS = ("microsoft", "windows")
    PROTECTED_NAMES = ("wps", "office", "微信", "wechat", "qq", "edge", "chrome", "firefox", "输入法", "ime")
    LEVEL_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4}

    def __init__(self, rules: ComponentRuleSet, max_level: str = "C2"):
        if max_level not in self.LEVEL_ORDER:
            raise ValueError("Invalid component max level")
        self.rules = rules
        self.max_level = max_level

    def plan(self, components: Iterable[dict], target_id: str) -> list[ComponentPlan]:
        plans = []
        for raw in components:
            component = Component.from_dict(raw, target_id)
            rule = self.rules.match(component)
            if self._is_protected(component):
                plans.append(ComponentPlan(target_id, component, "record", "C0", "protected", None, False, True, "Protected system or user software component."))
                continue
            if rule is None:
                plans.append(ComponentPlan(target_id, component, "record", "C0", "unknown", None, False, False, "No behavior rule matched; record only."))
                continue
            if self.LEVEL_ORDER[rule.level] > self.LEVEL_ORDER[self.max_level]:
                plans.append(ComponentPlan(target_id, component, rule.action, rule.level, rule.risk, rule.name, True, False, f"Rule {rule.name} exceeds default execution level {self.max_level}; explicit web confirmation required."))
                continue
            plans.append(ComponentPlan(target_id, component, rule.action, rule.level, rule.risk, rule.name, self.LEVEL_ORDER[rule.level] >= 3, False, f"Matched component rule {rule.name}."))
        return plans

    def _is_protected(self, component: Component) -> bool:
        publisher = component.publisher.casefold()
        name = component.name.casefold()
        return any(item in publisher for item in self.PROTECTED_PUBLISHERS) or any(item in name for item in self.PROTECTED_NAMES)
