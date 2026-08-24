"""Models for target-bound, recommendation-only migration plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


MigrationAction = Literal["ignore", "report_only", "recommend", "review", "migrate_ready", "blocked"]
ALLOWED_ACTIONS = {"ignore", "report_only", "recommend", "review", "migrate_ready", "blocked"}
FORBIDDEN_ACTIONS = {"delete", "uninstall", "force_remove"}


class MigrationPlanError(ValueError):
    """Raised for invalid or cross-target planning input."""


@dataclass(frozen=True)
class TargetProfile:
    target_id: str
    os: str
    user_type: str
    scan_time: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetProfile":
        values = {name: str(data.get(name, "")).strip() for name in ("target_id", "os", "user_type", "scan_time")}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise MigrationPlanError(f"Target profile is missing: {', '.join(missing)}")
        try:
            datetime.fromisoformat(values["scan_time"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise MigrationPlanError("target scan_time must use ISO 8601 format") from exc
        return cls(**values)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class MigrationPlanItem:
    target_id: str
    software: str
    current_function: str
    recommended_replacement: str | None
    recommended_replacements: tuple[str, ...]
    action: MigrationAction
    risk: str
    protection: str = "P2"
    confirm_required: bool = True
    verification_required: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""

    def __post_init__(self) -> None:
        if self.action not in ALLOWED_ACTIONS or self.action in FORBIDDEN_ACTIONS:
            raise MigrationPlanError(f"Forbidden migration action: {self.action}")
        if self.action not in {"ignore", "report_only"} and not self.confirm_required:
            raise MigrationPlanError("Every migration plan requires human confirmation")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["recommended_replacements"] = list(self.recommended_replacements)
        result["verification_required"] = list(self.verification_required)
        return result
