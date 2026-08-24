"""Models for discovered Windows background components and plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ComponentType = Literal["service", "startup", "scheduled_task", "desktop_app", "process"]
ComponentAction = Literal["record", "disable_startup", "disable_service", "remove_task", "remove_component"]
COMPONENT_TYPES = {"service", "startup", "scheduled_task", "desktop_app", "process"}
COMPONENT_ACTIONS = {"record", "disable_startup", "disable_service", "remove_task", "remove_component"}
COMPONENT_LEVELS = {"C0", "C1", "C2", "C3", "C4"}


class ComponentError(ValueError):
    """Raised for unsafe or malformed component records."""


@dataclass(frozen=True)
class Component:
    target_id: str
    name: str
    component_type: ComponentType
    publisher: str = ""
    path: str = ""
    startup_type: str = ""
    creator: str = ""
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], target_id: str | None = None) -> "Component":
        component_type = str(data.get("component_type", data.get("type", "")))
        name = str(data.get("name", "")).strip()
        resolved_target = str(data.get("target_id", target_id or "")).strip()
        if not resolved_target or not name or component_type not in COMPONENT_TYPES:
            raise ComponentError("target_id, name and a supported component_type are required")
        return cls(
            resolved_target,
            name,
            component_type,  # type: ignore[arg-type]
            str(data.get("publisher", "")),
            str(data.get("path", data.get("file_path", ""))),
            str(data.get("startup_type", "")),
            str(data.get("creator", "")),
            str(data.get("source", "")),
            dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = result.pop("component_type")
        return result


@dataclass(frozen=True)
class ComponentPlan:
    target_id: str
    component: Component
    action: ComponentAction
    level: str
    risk: str
    matched_rule: str | None
    confirm_required: bool
    protected: bool
    reason: str

    def __post_init__(self) -> None:
        if self.action not in COMPONENT_ACTIONS:
            raise ComponentError(f"Unsupported component action: {self.action}")
        if self.level not in COMPONENT_LEVELS:
            raise ComponentError(f"Unsupported component level: {self.level}")
        if self.component.target_id != self.target_id:
            raise ComponentError("Component target does not match plan target")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "component": self.component.to_dict(),
            "action": self.action,
            "level": self.level,
            "risk": self.risk,
            "matched_rule": self.matched_rule,
            "confirm_required": self.confirm_required,
            "protected": self.protected,
            "reason": self.reason,
        }

