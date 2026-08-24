"""Problem detector contract; Task 004 provides no system implementation."""

from __future__ import annotations

from typing import Any, Protocol


class ProblemDetector(Protocol):
    def detect(self, target_id: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        """Inspect supplied snapshot data and return findings without changing the target."""
        ...

