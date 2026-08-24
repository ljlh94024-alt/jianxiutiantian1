"""Append-only JSON Lines audit logs for agent sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_NAMES = {"session": "session.log", "authorization": "authorization.log", "execution": "execution.log"}


class AuditLogger:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def record(self, stream: str, event: str, **fields: Any) -> None:
        if stream not in LOG_NAMES:
            raise ValueError(f"Unknown audit stream: {stream}")
        self.directory.mkdir(parents=True, exist_ok=True)
        record = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
        with (self.directory / LOG_NAMES[stream]).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

