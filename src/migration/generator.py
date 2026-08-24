"""Generate deterministic migration plan and maintenance report JSON."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .models import MigrationPlanItem, TargetProfile


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_migration_artifacts(
    target: TargetProfile,
    plans: list[MigrationPlanItem],
    plan_path: Path,
    report_path: Path,
) -> tuple[dict, dict]:
    generated_at = datetime.now(timezone.utc).isoformat()
    migration_items = [item for item in plans if item.action not in {"ignore", "report_only"}]
    plan_document = {
        "target_profile": target.to_dict(),
        "generated_at": generated_at,
        "mode": "planning_only",
        "plans": [item.to_dict() for item in migration_items],
    }
    actions = Counter(item.action for item in plans)
    report_document = {
        "target_id": target.target_id,
        "generated_at": generated_at,
        "mode": "maintenance_planning",
        "summary": {
            "software_count": len(plans),
            "migration_plan_count": len(migration_items),
            "ignore": actions["ignore"],
            "report_only": actions["report_only"],
            "recommend": actions["recommend"],
            "review": actions["review"],
            "migrate_ready": actions["migrate_ready"],
            "blocked": actions["blocked"],
            "confirm_required": len(plans),
        },
        "software": [
            {
                "name": item.software,
                "function": item.current_function,
                "recommended_replacements": list(item.recommended_replacements),
                "risk": item.risk,
                "protection": item.protection,
                "action": item.action,
                "confirm_required": item.confirm_required,
            }
            for item in plans
        ],
    }
    _write_json(plan_path, plan_document)
    _write_json(report_path, report_document)
    return plan_document, report_document
