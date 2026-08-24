"""Rule-driven Windows background component inventory and cleanup."""

from .executor import ComponentExecutor, ComponentTaskHandler
from .audit import ComponentAuditLogger
from .matcher import ComponentRuleSet
from .models import Component, ComponentPlan, ComponentType
from .planner import ComponentPlanner
from .scanner import ComponentScanner, WindowsComponentScanner
from .verifier import ComponentVerifier

__all__ = [
    "Component", "ComponentAuditLogger", "ComponentExecutor", "ComponentTaskHandler", "ComponentPlan", "ComponentPlanner", "ComponentRuleSet",
    "ComponentScanner", "ComponentType", "ComponentVerifier", "WindowsComponentScanner",
]
