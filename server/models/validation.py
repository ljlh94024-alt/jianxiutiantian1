from __future__ import annotations

from typing import Any


ALLOWED_TASK_ACTIONS = {"scan", "analyze", "report", "approved_action"}


def validate_device_payload(payload: dict[str, Any]) -> None:
    if not all(str(payload.get(key, "")).strip() for key in ("machine_id", "hostname", "os")):
        raise ValueError("machine_id, hostname and os are required")


def validate_task_payload(payload: dict[str, Any]) -> None:
    if str(payload.get("action", "")) not in ALLOWED_TASK_ACTIONS:
        raise ValueError("action is not whitelisted")

