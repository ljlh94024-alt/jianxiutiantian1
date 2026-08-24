import json
from pathlib import Path

import pytest

from main import plan_migration
from src.migration.generator import generate_migration_artifacts
from src.migration.models import MigrationPlanError, TargetProfile
from src.migration.planner import MigrationPlanner
from src.migration.protection import ProtectionPolicy
from src.replacement.loader import load_replacement_data
from src.replacement.matcher import ReplacementMatcher


TARGET_ID = "PC001"


@pytest.fixture(scope="module")
def target():
    return TargetProfile.from_dict(
        {"target_id": TARGET_ID, "os": "Windows11", "user_type": "family", "scan_time": "2026-08-24"}
    )


@pytest.fixture(scope="module")
def planner(target):
    return MigrationPlanner(target, ProtectionPolicy.load("rules/software_protection"))


def _profile(name, category, family="unknown", risk="S0"):
    return {"target_id": TARGET_ID, "name": name, "category": category, "family": family, "risk_level": risk}


def _suggestions(*profiles):
    return ReplacementMatcher(load_replacement_data("database")).match_all(profiles)


@pytest.mark.parametrize(
    ("profile", "replacement"),
    [
        (_profile("2345看图王", "image_viewer", "2345", "S2"), "ImageGlass"),
        (_profile("360压缩", "archive", "360", "S2"), "7-Zip"),
        (_profile("360安全卫士", "security", "360", "S3"), "Windows Defender"),
        (_profile("360驱动大师", "driver_tool", "360", "S3"), "Windows Update"),
    ],
)
def test_target_ecosystem_generates_recommendation(planner, profile, replacement):
    item = planner.create_plan([profile], _suggestions(profile))[0]
    assert (item.action, item.protection, item.recommended_replacement) == ("recommend", "P4", replacement)
    assert item.confirm_required is True


@pytest.mark.parametrize(
    "profile",
    [
        _profile("WPS Office", "office"),
        _profile("Microsoft Office Professional", "office"),
        _profile("微信", "communication", "tencent"),
        _profile("QQ", "communication", "tencent"),
        _profile("搜狗输入法", "input_method", "sogou"),
        _profile("Adobe Photoshop", "design"),
        _profile("AutoCAD 2026", "cad"),
        _profile("360浏览器", "browser", "360", "S2"),
        _profile("2345浏览器", "browser", "2345", "S2"),
    ],
)
def test_protected_software_is_ignored(planner, profile):
    item = planner.create_plan([profile], [])[0]
    assert (item.protection, item.action, item.recommended_replacement) == ("P1", "ignore", None)


@pytest.mark.parametrize("name", ["驱动人生", "驱动精灵", "鲁大师", "快压"])
def test_p3_software_requires_review(planner, name):
    profile = _profile(name, "unknown", risk="S2")
    item = planner.create_plan([profile], _suggestions(profile))[0]
    assert (item.protection, item.action, item.confirm_required) == ("P3", "review", True)


def test_normal_software_is_report_only(planner):
    item = planner.create_plan([_profile("VLC media player", "media")], [])[0]
    assert (item.protection, item.action) == ("P2", "report_only")


def test_rejects_missing_or_mismatched_target(planner):
    with pytest.raises(MigrationPlanError, match="no target_id"):
        planner.create_plan([{"name": "360压缩", "category": "archive"}], [])
    with pytest.raises(MigrationPlanError, match="does not match"):
        planner.create_plan([{**_profile("360压缩", "archive"), "target_id": "PC002"}], [])


def test_generator_keeps_protected_items_out_of_migration_plan(tmp_path, planner, target):
    profiles = [_profile("WPS Office", "office"), _profile("360压缩", "archive", "360", "S2")]
    plans = planner.create_plan(profiles, _suggestions(*profiles))
    plan_doc, report_doc = generate_migration_artifacts(
        target, plans, tmp_path / "migration_plan.json", tmp_path / "migration_report.json"
    )
    assert [item["software"] for item in plan_doc["plans"]] == ["360压缩"]
    assert report_doc["summary"]["ignore"] == 1
    assert report_doc["summary"]["migration_plan_count"] == 1


def test_cli_planning_flow(tmp_path):
    target_path = tmp_path / "target_profile.json"
    profile_path = tmp_path / "software_profile.json"
    suggestion_path = tmp_path / "replacement_suggestion.json"
    plan_path = tmp_path / "reports" / "migration_plan.json"
    report_path = tmp_path / "reports" / "migration_report.json"
    target_path.write_text(
        json.dumps({"target_id": TARGET_ID, "os": "Windows11", "user_type": "family", "scan_time": "2026-08-24"}),
        encoding="utf-8",
    )
    profiles = [_profile("2345看图王", "image_viewer", "2345", "S2")]
    profile_path.write_text(json.dumps(profiles), encoding="utf-8")
    suggestion_path.write_text(json.dumps(_suggestions(*profiles)), encoding="utf-8")
    assert plan_migration(
        target_path, profile_path, suggestion_path, plan_path, report_path, Path("rules/software_protection")
    ) == 0
    assert json.loads(plan_path.read_text(encoding="utf-8"))["plans"][0]["recommended_replacement"] == "ImageGlass"

