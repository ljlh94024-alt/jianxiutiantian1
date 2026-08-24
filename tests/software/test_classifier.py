import json

import pytest

from main import scan
from src.software.classifier import SoftwareClassifier
from src.software.fingerprint import FingerprintDatabase


@pytest.fixture(scope="module")
def classifier():
    return SoftwareClassifier(FingerprintDatabase.load("rules/software_fingerprint"))


@pytest.mark.parametrize(
    ("item", "family", "category", "risk"),
    [
        ({"name": "2345看图王", "publisher": "2345"}, "2345", "image_viewer", "S2"),
        ({"name": "360安全卫士"}, "360", "security", "S3"),
        ({"name": "360杀毒"}, "360", "security", "S3"),
        ({"name": "360浏览器"}, "360", "browser", "S2"),
        ({"name": "360压缩"}, "360", "archive", "S2"),
        ({"name": "360驱动大师"}, "360", "driver_tool", "S3"),
        ({"name": "2345浏览器"}, "2345", "browser", "S2"),
        ({"name": "2345好压"}, "2345", "archive", "S2"),
        ({"name": "腾讯电脑管家", "publisher": "Tencent"}, "tencent", "security", "S3"),
        ({"name": "QQ浏览器", "publisher": "Tencent"}, "tencent", "browser", "S1"),
        ({"name": "腾讯软件中心"}, "tencent", "software_manager", "S1"),
        ({"name": "百度浏览器", "publisher": "Baidu"}, "baidu", "browser", "S1"),
        ({"name": "搜狗输入法", "publisher": "Sogou"}, "sogou", "input_method", "S1"),
        ({"name": "迅雷", "publisher": "Xunlei"}, "xunlei", "downloader", "S1"),
    ],
)
def test_supported_products(classifier, item, family, category, risk):
    profile = classifier.classify(item)
    assert profile is not None
    assert (profile.family, profile.category, profile.risk_level) == (family, category, risk)


def test_matches_all_supported_fields(classifier):
    profile = classifier.classify(
        {
            "name": "安全工具",
            "publisher": "Qihoo Technology",
            "install_path": r"C:\Program Files\360safe",
            "file_paths": [r"C:\Program Files\360safe\360tray.exe"],
        }
    )
    assert profile is not None
    assert profile.family == "360"
    assert profile.category == "security"
    assert set(profile.matched_by) == {"publisher", "install_path", "file_paths"}


def test_unmatched_software_is_s0_when_requested(classifier):
    profiles = classifier.classify_all([{"name": "Google Chrome"}], include_unmatched=True)
    assert profiles[0]["family"] == "unknown"
    assert profiles[0]["risk_level"] == "S0"


def test_scan_writes_profile_from_existing_inventory(tmp_path):
    inventory = tmp_path / "software_inventory.json"
    output = tmp_path / "software_profile.json"
    inventory.write_text(json.dumps([{"name": "2345看图王", "publisher": "2345"}]), encoding="utf-8")
    scan(inventory, output, __import__("pathlib").Path("rules/software_fingerprint"))
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result[0]["family"] == "2345"
    assert result[0]["category"] == "image_viewer"
