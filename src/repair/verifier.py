"""Repair verification contract; accepts evidence and performs no repair."""

from __future__ import annotations

from typing import Any, Protocol

from .repair_plan import RepairPlan


class RepairVerifier(Protocol):
    def verify(self, plan: RepairPlan, evidence: dict[str, Any]) -> bool:
        """Return whether supplied evidence meets a future repair plan's checks."""
        ...

