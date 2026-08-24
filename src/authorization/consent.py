"""Task-specific user consent records and UI-provider contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Protocol

from src.controller.task_sender import TaskPackage


@dataclass(frozen=True)
class AuthorizationRecord:
    target_id: str
    task_id: str
    session_id: str
    user_confirm: bool
    operator: str
    time: str
    permission: str

    @classmethod
    def create(
        cls,
        task: TaskPackage,
        session_id: str,
        user_confirm: bool,
        operator: str,
        permission: str,
    ) -> "AuthorizationRecord":
        return cls(
            task.target_id,
            task.task_id,
            session_id,
            user_confirm,
            operator,
            datetime.now(timezone.utc).isoformat(),
            permission,
        )

    def to_dict(self) -> dict:
        return asdict(self)


class ConsentProvider(Protocol):
    def request_consent(self, task: TaskPackage, session_id: str, permission: str) -> AuthorizationRecord:
        """Display a visible prompt and return the target user's explicit decision."""
        ...

