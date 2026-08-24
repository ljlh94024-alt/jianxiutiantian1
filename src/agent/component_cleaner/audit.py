"""Dedicated append-only component cleanup log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ComponentAuditLogger:
    def __init__(self, directory: str | Path):
        self.path = Path(directory) / "component_clean.log"

    def record(self, component: str, component_type: str, operation: str, result: str, **fields: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "type": component_type,
            "operation": operation,
            "result": result,
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")

