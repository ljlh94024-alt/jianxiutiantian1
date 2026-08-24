"""Create auditable, target-bound maintenance task packages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


TaskAction = Literal["scan", "analyze", "report", "approved_action"]
RiskLevel = Literal["L0", "L1", "L2"]
ALLOWED_ACTIONS = {"scan", "analyze", "report", "approved_action"}
FORBIDDEN_ACTIONS = {"delete_all", "format", "disable_security", "hidden_execute"}
RISK_LEVELS = {"L0", "L1", "L2"}


class TaskPackageError(ValueError):
    """Raised when an unsafe or malformed task package is encountered."""


@dataclass(frozen=True)
class TaskPackage:
    target_id: str
    task_id: str
    action: TaskAction
    risk: RiskLevel
    require_admin: bool
    created_time: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskPackage":
        required = ("target_id", "task_id", "action", "risk", "require_admin")
        missing = [name for name in required if name not in data]
        if missing:
            raise TaskPackageError(f"Task package is missing: {', '.join(missing)}")
        action = str(data["action"])
        risk = str(data["risk"])
        target_id = str(data["target_id"]).strip()
        task_id = str(data["task_id"]).strip()
        if not target_id or not task_id:
            raise TaskPackageError("target_id and task_id cannot be empty")
        if action not in ALLOWED_ACTIONS or action in FORBIDDEN_ACTIONS:
            raise TaskPackageError(f"Action is not allowed: {action}")
        if risk not in RISK_LEVELS:
            raise TaskPackageError(f"Invalid risk level: {risk}")
        if type(data["require_admin"]) is not bool:
            raise TaskPackageError("require_admin must be a boolean")
        if action in {"scan", "analyze", "report"} and data["require_admin"]:
            raise TaskPackageError(f"Read-only action {action} cannot request administrator permission")
        if risk == "L2" and not data["require_admin"]:
            raise TaskPackageError("L2 tasks must declare administrator permission")
        created_time = str(data.get("created_time") or datetime.now(timezone.utc).isoformat())
        try:
            datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TaskPackageError("created_time must use ISO 8601 format") from exc
        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            raise TaskPackageError("parameters must be an object")
        return cls(
            target_id,
            task_id,
            action,  # type: ignore[arg-type]
            risk,  # type: ignore[arg-type]
            data["require_admin"],
            created_time,
            dict(parameters),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskSender:
    def create(
        self,
        target_id: str,
        task_id: str,
        action: TaskAction,
        risk: RiskLevel = "L0",
        require_admin: bool = False,
        parameters: dict[str, Any] | None = None,
    ) -> TaskPackage:
        return TaskPackage.from_dict(
            {
                "target_id": target_id,
                "task_id": task_id,
                "action": action,
                "risk": risk,
                "require_admin": require_admin,
                "created_time": datetime.now(timezone.utc).isoformat(),
                "parameters": parameters or {},
            }
        )

    def write_offline(self, task: TaskPackage, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(task.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
