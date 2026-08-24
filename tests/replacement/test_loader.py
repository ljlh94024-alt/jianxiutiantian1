import json

import pytest

from src.replacement.database import ReplacementDatabaseError
from src.replacement.loader import load_replacement_data


def test_loads_and_validates_database():
    data = load_replacement_data("database")
    assert len(data.replacements) == 9
    assert "image_viewer" in data.categories
    assert "open_webp" in data.verification_rules["image_viewer"]["tests"]


def test_rejects_unknown_category(tmp_path):
    (tmp_path / "replacement_database.json").write_text(
        json.dumps({"bad": {"name": "bad", "category": "missing", "function": ["x"], "replacement": [{}]}}),
        encoding="utf-8",
    )
    (tmp_path / "software_category.json").write_text("{}", encoding="utf-8")
    (tmp_path / "verification_rules.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ReplacementDatabaseError, match="Unknown category"):
        load_replacement_data(tmp_path)

