"""Permission levels and a non-elevating provider contract."""

from __future__ import annotations

from enum import IntEnum
from typing import Protocol

from src.controller.task_sender import TaskPackage


class PermissionLevel(IntEnum):
    A0 = 0
    A1 = 1
    A2 = 2


def required_permission(task: TaskPackage) -> PermissionLevel:
    if task.risk == "L2":
        return PermissionLevel.A2
    if task.require_admin:
        return PermissionLevel.A1
    return PermissionLevel.A0


class PermissionProvider(Protocol):
    def request_permission(self, task: TaskPackage, required: PermissionLevel) -> bool:
        """Request visible OS/user authorization; implementations must never bypass UAC."""
        ...


class NoElevationPermissionProvider:
    """Safe default: A0 succeeds and elevated requests remain unfulfilled."""

    def request_permission(self, task: TaskPackage, required: PermissionLevel) -> bool:
        return required == PermissionLevel.A0

