"""Windows Clean Agent read-only command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.software.classifier import SoftwareClassifier
from src.software.fingerprint import FingerprintDatabase
from src.software.inventory import collect_windows_inventory


PROJECT_ROOT = Path(__file__).resolve().parent


def _read_json_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return data


def _write_json(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scan(inventory_path: Path, profile_path: Path, rules_path: Path, refresh: bool = False) -> int:
    if refresh or not inventory_path.exists():
        _write_json(inventory_path, collect_windows_inventory())
    inventory = _read_json_list(inventory_path)
    classifier = SoftwareClassifier(FingerprintDatabase.load(rules_path))
    profiles = classifier.classify_all(inventory, include_unmatched=True)
    _write_json(profile_path, profiles)
    print(f"Inventory: {inventory_path} ({len(inventory)} records)")
    print(f"Profile:   {profile_path} ({len(profiles)} records)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows Clean Agent (analysis only)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="generate inventory and software profile")
    scan_parser.add_argument("--inventory", type=Path, default=PROJECT_ROOT / "software_inventory.json")
    scan_parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "software_profile.json")
    scan_parser.add_argument("--rules", type=Path, default=PROJECT_ROOT / "rules" / "software_fingerprint")
    scan_parser.add_argument("--refresh-inventory", action="store_true", help="re-read the read-only Windows inventory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "scan":
        return scan(args.inventory, args.output, args.rules, args.refresh_inventory)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

