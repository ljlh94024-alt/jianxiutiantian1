"""Explicit rollback for service, startup and scheduled-task snapshots."""

from __future__ import annotations

from typing import Any, Protocol

from .snapshot import SnapshotStore


class RollbackBackend(Protocol):
    def restore_service(self, state: dict[str, Any]) -> None: ...
    def restore_startup(self, state: dict[str, Any]) -> None: ...
    def restore_task(self, state: dict[str, Any]) -> None: ...


class RollbackManager:
    def __init__(self, snapshots: SnapshotStore, backend: RollbackBackend):
        self.snapshots = snapshots
        self.backend = backend

    def rollback(self, snapshot_id: str, authorized: bool, human_confirmed: bool) -> dict[str, Any]:
        if not authorized:
            return {"status": "authorization_required"}
        if not human_confirmed:
            return {"status": "confirmation_required"}
        snapshot = self.snapshots.load(snapshot_id)
        kind = str(snapshot["component"].get("type", snapshot["component"].get("component_type", "")))
        method = {"service": "restore_service", "startup": "restore_startup", "scheduled_task": "restore_task"}.get(kind)
        if method is None:
            return {"status": "failed", "reason": "rollback_not_supported_for_component_type"}
        getattr(self.backend, method)(snapshot["state"])
        return {"status": "success", "snapshot_id": snapshot_id, "component": snapshot["component"].get("name", "")}
