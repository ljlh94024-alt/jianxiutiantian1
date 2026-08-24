"""Atomic JSON execution snapshots under backup/<machine_id>/<timestamp>."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe(value: str) -> str:
    cleaned = _SAFE.sub("_", str(value)).strip("._")
    if not cleaned:
        raise ValueError("snapshot identifier is empty")
    return cleaned[:120]


class SnapshotStore:
    def __init__(self, root: str | Path = "backup"):
        self.root = Path(root)

    def create(self, machine_id: str, task_id: str, action: str, component: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        directory = self.root / _safe(machine_id) / timestamp
        directory.mkdir(parents=True, exist_ok=False)
        payload = {"machine_id": machine_id, "task_id": task_id, "action": action, "component": component, "state": state, "created_at": datetime.now(timezone.utc).isoformat()}
        path = directory / "snapshot.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"snapshot_id": f"{_safe(machine_id)}/{timestamp}", "path": str(path), **payload}

    def load(self, snapshot_id: str) -> dict[str, Any]:
        parts = Path(snapshot_id).parts
        if len(parts) != 2 or any(part in {"", ".", ".."} or _safe(part) != part for part in parts):
            raise ValueError("invalid snapshot id")
        path = self.root.joinpath(*parts, "snapshot.json").resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("snapshot path escapes backup root")
        return json.loads(path.read_text(encoding="utf-8"))
