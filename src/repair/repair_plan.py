"""Repair-plan data contract with mandatory human confirmation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


RepairLevel = Literal["R0", "R1", "R2", "R3"]
REPAIR_LEVELS = {"R0", "R1", "R2", "R3"}


@dataclass(frozen=True)
class RepairPlan:
    target_id: str
    problem_type: str
    level: RepairLevel
    recommendation: str
    confirm_required: bool = True

    def __post_init__(self) -> None:
        if self.level not in REPAIR_LEVELS:
            raise ValueError(f"Invalid repair level: {self.level}")
        if not self.confirm_required:
            raise ValueError("Repair plans require human confirmation")

    def to_dict(self) -> dict:
        return asdict(self)


class RepairPlanBuilder:
    """Interface for future planners; intentionally has no execute method."""

    def build(self, target_id: str, finding: dict) -> RepairPlan:
        raise NotImplementedError
