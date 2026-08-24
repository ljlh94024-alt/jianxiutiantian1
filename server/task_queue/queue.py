from __future__ import annotations

from typing import Any

from server.database import MaintenanceStore


class TaskQueue:
    """Keep queue operations behind a small facade for future broker replacement."""

    def __init__(self, store: MaintenanceStore):
        self.store = store

    def enqueue(self, task: dict[str, Any]) -> dict[str, Any]:
        return self.store.create_task(task)

    def claim(self, machine_id: str) -> list[dict[str, Any]]:
        return self.store.claim_tasks(machine_id)

    def complete(self, machine_id: str, task_id: str, result: dict[str, Any]) -> dict[str, Any]:
        return self.store.complete_task(machine_id, task_id, result)

