"""Load and validate the three replacement JSON databases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import ReplacementData, ReplacementDatabaseError


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplacementDatabaseError(f"Cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplacementDatabaseError(f"{path} must contain a JSON object")
    return value


def load_replacement_data(directory: str | Path) -> ReplacementData:
    database_dir = Path(directory)
    data = ReplacementData(
        replacements=_load_object(database_dir / "replacement_database.json"),
        categories=_load_object(database_dir / "software_category.json"),
        verification_rules=_load_object(database_dir / "verification_rules.json"),
    )
    data.validate()
    return data

