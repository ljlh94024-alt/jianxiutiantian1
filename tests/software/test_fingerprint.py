from pathlib import Path

import pytest

from src.software.fingerprint import FingerprintDatabase, FingerprintRuleError


def test_loads_six_family_files():
    database = FingerprintDatabase.load("rules/software_fingerprint")
    assert {rule.family for rule in database.rules} == {"360", "2345", "tencent", "baidu", "sogou", "xunlei"}


def test_rejects_invalid_risk_level(tmp_path: Path):
    (tmp_path / "bad.yaml").write_text("family: bad\nrisk_level: S9\n", encoding="utf-8")
    with pytest.raises(FingerprintRuleError, match="Invalid risk level"):
        FingerprintDatabase.load(tmp_path)

