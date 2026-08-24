"""Target agent handshake, identity validation, and offline processing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from src.authorization.consent import AuthorizationRecord, ConsentProvider
from src.authorization.permission import NoElevationPermissionProvider, PermissionProvider, required_permission
from src.authorization.session import SessionStore
from src.controller.task_sender import TaskPackage, TaskPackageError

from .audit import AuditLogger
from .executor import WhitelistExecutor


class AgentSecurityError(ValueError):
    """Raised when task identity or authorization binding is invalid."""


@dataclass(frozen=True)
class TargetIdentity:
    target_id: str
    computer_name: str
    hardware_id: str
    created_time: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetIdentity":
        fields = {name: str(data.get(name, "")).strip() for name in cls.__annotations__}
        missing = [name for name, value in fields.items() if not value]
        if missing:
            raise AgentSecurityError(f"Target identity is missing: {', '.join(missing)}")
        try:
            datetime.fromisoformat(fields["created_time"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise AgentSecurityError("created_time must use ISO 8601 format") from exc
        return cls(**fields)


@dataclass(frozen=True)
class AgentResult:
    target_id: str
    task_id: str
    session_id: str
    status: str
    permission: str
    result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OutboundTransport(Protocol):
    """Client-initiated transport only; implementations must use authenticated TLS."""

    def connect(self) -> None: ...

    def send(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def close(self) -> None: ...


class AgentClient:
    def __init__(
        self,
        identity: TargetIdentity,
        executor: WhitelistExecutor,
        logger: AuditLogger,
        sessions: SessionStore | None = None,
        permissions: PermissionProvider | None = None,
    ):
        self.identity = identity
        self.executor = executor
        self.logger = logger
        self.sessions = sessions or SessionStore()
        self.permissions = permissions or NoElevationPermissionProvider()

    def process(self, task: TaskPackage, consent: ConsentProvider) -> AgentResult:
        if task.target_id != self.identity.target_id:
            self.logger.record(
                "session", "target_rejected", task_id=task.task_id,
                expected_target=self.identity.target_id, received_target=task.target_id,
            )
            raise AgentSecurityError("Task target_id does not match this computer")
        session = self.sessions.create(task.target_id, task.task_id)
        permission = required_permission(task)
        permission_name = permission.name
        self.logger.record(
            "session", "session_started", target_id=task.target_id,
            task_id=task.task_id, session_id=session.session_id, action=task.action,
        )
        authorization = consent.request_consent(task, session.session_id, permission_name)
        self._validate_authorization(task, session.session_id, permission_name, authorization)
        self.logger.record(
            "authorization", "consent_recorded", target_id=task.target_id,
            task_id=task.task_id, session_id=session.session_id,
            operator=authorization.operator, permission=permission_name,
            user_confirm=authorization.user_confirm,
        )
        if not self.sessions.consume(session.session_id, task.target_id, task.task_id):
            raise AgentSecurityError("Authorization session is invalid, expired, or already used")
        if not authorization.user_confirm:
            return self._finish(task, session.session_id, "denied", permission_name, {})
        if not self.permissions.request_permission(task, permission):
            return self._finish(
                task, session.session_id, "permission_denied", permission_name,
                {"message": "Required permission was not granted; no handler ran."},
            )
        result = self.executor.execute(task, authorized=True)
        status = str(result.get("status", "completed"))
        return self._finish(task, session.session_id, status, permission_name, result)

    def _validate_authorization(
        self,
        task: TaskPackage,
        session_id: str,
        permission: str,
        authorization: AuthorizationRecord,
    ) -> None:
        expected = (task.target_id, task.task_id, session_id, permission)
        received = (
            authorization.target_id, authorization.task_id,
            authorization.session_id, authorization.permission,
        )
        if received != expected or not authorization.operator.strip():
            raise AgentSecurityError("Authorization is not bound to this target, task, session, and permission")

    def _finish(
        self, task: TaskPackage, session_id: str, status: str, permission: str, result: dict[str, Any]
    ) -> AgentResult:
        self.logger.record(
            "execution", "task_finished", target_id=task.target_id,
            task_id=task.task_id, session_id=session_id,
            action=task.action, permission=permission, status=status,
        )
        return AgentResult(task.target_id, task.task_id, session_id, status, permission, result)

    def process_offline(
        self, task_path: str | Path, result_path: str | Path, consent: ConsentProvider
    ) -> AgentResult:
        try:
            raw = json.loads(Path(task_path).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskPackageError(f"Cannot load offline task package: {exc}") from exc
        if not isinstance(raw, dict):
            raise TaskPackageError("Offline task package must contain an object")
        result = self.process(TaskPackage.from_dict(raw), consent)
        output = Path(result_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
