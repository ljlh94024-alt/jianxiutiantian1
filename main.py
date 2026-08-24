"""Windows Clean Agent read-only command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.migration.generator import generate_migration_artifacts
from src.migration.models import TargetProfile
from src.migration.planner import MigrationPlanner
from src.migration.protection import ProtectionPolicy
from src.replacement.loader import load_replacement_data
from src.replacement.matcher import ReplacementMatcher
from src.controller.task_sender import TaskSender
from src.software.classifier import SoftwareClassifier
from src.software.fingerprint import FingerprintDatabase
from src.software.inventory import collect_windows_inventory


PROJECT_ROOT = Path(__file__).resolve().parent


def _read_json_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return data


def _read_json_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scan(
    inventory_path: Path,
    profile_path: Path,
    rules_path: Path,
    refresh: bool = False,
    target_profile_path: Path | None = None,
) -> int:
    if refresh or not inventory_path.exists():
        _write_json(inventory_path, collect_windows_inventory())
    inventory = _read_json_list(inventory_path)
    classifier = SoftwareClassifier(FingerprintDatabase.load(rules_path))
    profiles = classifier.classify_all(inventory, include_unmatched=True)
    if target_profile_path:
        target = TargetProfile.from_dict(_read_json_object(target_profile_path))
        for profile in profiles:
            profile["target_id"] = target.target_id
    _write_json(profile_path, profiles)
    print(f"Inventory: {inventory_path} ({len(inventory)} records)")
    print(f"Profile:   {profile_path} ({len(profiles)} records)")
    return 0


def analyze(profile_path: Path, output_path: Path, database_path: Path) -> int:
    profiles = _read_json_list(profile_path)
    matcher = ReplacementMatcher(load_replacement_data(database_path))
    suggestions = matcher.match_all(profiles)
    _write_json(output_path, suggestions)
    print(f"Profile:     {profile_path} ({len(profiles)} records)")
    print(f"Suggestions: {output_path} ({len(suggestions)} records)")
    return 0


def plan_migration(
    target_profile_path: Path,
    profile_path: Path,
    suggestion_path: Path,
    plan_path: Path,
    report_path: Path,
    protection_rules_path: Path,
) -> int:
    target = TargetProfile.from_dict(_read_json_object(target_profile_path))
    profiles = _read_json_list(profile_path)
    suggestions = _read_json_list(suggestion_path)
    policy = ProtectionPolicy.load(protection_rules_path)
    plans = MigrationPlanner(target, policy).create_plan(profiles, suggestions)
    plan_document, _ = generate_migration_artifacts(target, plans, plan_path, report_path)
    print(f"Target: {target.target_id}")
    print(f"Plan:   {plan_path} ({len(plan_document['plans'])} scoped records)")
    print(f"Report: {report_path}")
    return 0


def create_task_package(
    target_id: str, task_id: str, action: str, risk: str, require_admin: bool, output_path: Path
) -> int:
    task = TaskSender().create(
        target_id, task_id, action, risk, require_admin  # type: ignore[arg-type]
    )
    TaskSender().write_offline(task, output_path)
    print(f"Task package: {output_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows Clean Agent (analysis only)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="generate inventory and software profile")
    scan_parser.add_argument("--inventory", type=Path, default=PROJECT_ROOT / "software_inventory.json")
    scan_parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "software_profile.json")
    scan_parser.add_argument("--rules", type=Path, default=PROJECT_ROOT / "rules" / "software_fingerprint")
    scan_parser.add_argument("--refresh-inventory", action="store_true", help="re-read the read-only Windows inventory")
    scan_parser.add_argument("--target-profile", type=Path, help="bind generated profiles to a target computer")
    analyze_parser = subparsers.add_parser("analyze", help="generate replacement suggestions without executing changes")
    analyze_parser.add_argument("--profile", type=Path, default=PROJECT_ROOT / "software_profile.json")
    analyze_parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "replacement_suggestion.json")
    analyze_parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "database")
    plan_parser = subparsers.add_parser("plan", help="create a target-bound migration plan without executing changes")
    plan_parser.add_argument("--target-profile", type=Path, required=True)
    plan_parser.add_argument("--profile", type=Path, default=PROJECT_ROOT / "software_profile.json")
    plan_parser.add_argument("--suggestions", type=Path, default=PROJECT_ROOT / "replacement_suggestion.json")
    plan_parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "migration_plan.json")
    plan_parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "reports" / "migration_report.json")
    plan_parser.add_argument(
        "--protection-rules",
        type=Path,
        default=PROJECT_ROOT / "rules" / "software_protection",
    )
    task_parser = subparsers.add_parser("create-task", help="create a target-bound offline task package")
    task_parser.add_argument("--target-id", required=True)
    task_parser.add_argument("--task-id", required=True)
    task_parser.add_argument("--action", choices=("scan", "analyze", "report", "approved_action"), required=True)
    task_parser.add_argument("--risk", choices=("L0", "L1", "L2"), default="L0")
    task_parser.add_argument("--require-admin", action="store_true")
    task_parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "task_package.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "scan":
        return scan(args.inventory, args.output, args.rules, args.refresh_inventory, args.target_profile)
    if args.command == "analyze":
        return analyze(args.profile, args.output, args.database)
    if args.command == "plan":
        return plan_migration(
            args.target_profile,
            args.profile,
            args.suggestions,
            args.output,
            args.report,
            args.protection_rules,
        )
    if args.command == "create-task":
        return create_task_package(
            args.target_id, args.task_id, args.action, args.risk, args.require_admin, args.output
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
