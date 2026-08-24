"""Fail-closed checks shared by all real Windows backends."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class WindowsBackendSafetyError(ValueError):
    """Raised when a fixed backend receives an unsafe or ambiguous target."""


PROTECTED_TERMS = ("microsoft", "windows", "defender", "firewall", "wps", "office", "wechat", "微信", "qq", "edge", "chrome", "firefox", "输入法", "ime")
ALLOWED_TYPES = {"service", "startup", "scheduled_task", "desktop_app", "process"}


def validate_component(component: dict[str, Any], target_id: str | None = None) -> dict[str, Any]:
    name = str(component.get("name", "")).strip()
    component_type = str(component.get("type", component.get("component_type", ""))).strip()
    if not name or component_type not in ALLOWED_TYPES:
        raise WindowsBackendSafetyError("component name and supported type are required")
    if target_id and str(component.get("target_id", target_id)) != target_id:
        raise WindowsBackendSafetyError("component target does not match execution target")
    identity = " ".join(str(component.get(key, "")) for key in ("name", "publisher", "path", "source")).casefold()
    if any(term in identity for term in PROTECTED_TERMS):
        raise WindowsBackendSafetyError("protected Windows or user software component")
    return component


def ensure_windows() -> None:
    if os.name != "nt":
        raise WindowsBackendSafetyError("real Windows backend is available only on Windows")


def safe_child(path: str | Path, root: str | Path) -> Path:
    candidate = Path(path).resolve()
    base = Path(root).resolve()
    if candidate == base or base not in candidate.parents:
        raise WindowsBackendSafetyError("path is outside the configured allowlist")
    return candidate
