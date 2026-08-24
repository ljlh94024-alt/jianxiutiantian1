import pytest

from src.migration.models import MigrationPlanError, MigrationPlanItem, TargetProfile
from src.repair.repair_plan import RepairPlan


def test_target_profile_requires_iso_date():
    with pytest.raises(MigrationPlanError, match="ISO 8601"):
        TargetProfile.from_dict({"target_id": "PC1", "os": "Windows11", "user_type": "family", "scan_time": "today"})


def test_forbidden_action_cannot_be_constructed():
    with pytest.raises(MigrationPlanError, match="Forbidden migration action"):
        MigrationPlanItem("PC1", "app", "tool", None, (), "uninstall", "S2")  # type: ignore[arg-type]


def test_repair_interface_rejects_invalid_level_or_bypassed_confirmation():
    with pytest.raises(ValueError, match="Invalid repair level"):
        RepairPlan("PC1", "disk_space", "R9", "inspect")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="human confirmation"):
        RepairPlan("PC1", "disk_space", "R1", "inspect", confirm_required=False)
