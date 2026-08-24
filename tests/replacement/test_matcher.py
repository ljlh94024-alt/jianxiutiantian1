import json
from pathlib import Path

import pytest

from main import analyze
from src.replacement.loader import load_replacement_data
from src.replacement.matcher import ReplacementMatcher


@pytest.fixture(scope="module")
def matcher():
    return ReplacementMatcher(load_replacement_data("database"))


@pytest.mark.parametrize(
    ("software", "category", "expected"),
    [
        ("2345看图王", "image_viewer", "ImageGlass"),
        ("360压缩", "archive", "7-Zip"),
        ("2345好压 6.5", "archive", "7-Zip"),
        ("360安全卫士", "security", "Windows Defender"),
        ("360杀毒", "security", "Windows Defender"),
        ("360驱动大师", "driver_tool", "Windows Update"),
        ("驱动人生", "driver_tool", "Windows Update"),
        ("驱动精灵", "driver_tool", "Windows Update"),
        ("迅雷 12", "downloader", "浏览器下载"),
    ],
)
def test_required_replacements(matcher, software, category, expected):
    result = matcher.match({"name": software, "category": category})
    assert result is not None
    assert result["suggestions"][0]["name"] == expected


@pytest.mark.parametrize("software", ["360浏览器", "2345浏览器", "Google Chrome"])
def test_browsers_are_protected(matcher, software):
    assert matcher.match({"name": software, "category": "browser"}) is None


def test_unknown_software_has_no_suggestion(matcher):
    assert matcher.match({"name": "Unknown Application", "category": "unknown"}) is None
    assert matcher.match({"name": "Mozilla Thunderbird", "category": "unknown"}) is None


def test_profile_category_must_agree(matcher):
    assert matcher.match({"name": "迅雷", "category": "security"}) is None


def test_analyze_writes_suggestions(tmp_path: Path):
    profile = tmp_path / "software_profile.json"
    output = tmp_path / "replacement_suggestion.json"
    profile.write_text(
        json.dumps([
            {"name": "2345看图王", "category": "image_viewer"},
            {"name": "360浏览器", "category": "browser"},
        ]),
        encoding="utf-8",
    )
    analyze(profile, output, Path("database"))
    result = json.loads(output.read_text(encoding="utf-8"))
    assert [item["software"] for item in result] == ["2345看图王"]
