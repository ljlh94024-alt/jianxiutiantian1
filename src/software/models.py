"""Models shared by the software fingerprint engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


MATCH_FIELDS = ("name", "publisher", "install_path", "file_paths")


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]
    return [str(value)]


@dataclass(frozen=True)
class SoftwareInventoryItem:
    name: str
    publisher: str = ""
    install_path: str = ""
    file_paths: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SoftwareInventoryItem":
        paths = data.get("file_paths", data.get("files", data.get("file_path")))
        return cls(
            name=str(data.get("name", data.get("display_name", ""))),
            publisher=str(data.get("publisher", "") or ""),
            install_path=str(data.get("install_path", data.get("path", "")) or ""),
            file_paths=tuple(_strings(paths)),
        )

    def searchable_values(self) -> dict[str, list[str]]:
        return {
            "name": [self.name],
            "publisher": [self.publisher],
            "install_path": [self.install_path],
            "file_paths": list(self.file_paths),
        }


@dataclass(frozen=True)
class KeywordSet:
    names: tuple[str, ...] = ()
    publishers: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    files: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "KeywordSet":
        data = data or {}
        return cls(
            names=tuple(_strings(data.get("names"))),
            publishers=tuple(_strings(data.get("publishers"))),
            paths=tuple(_strings(data.get("paths"))),
            files=tuple(_strings(data.get("files"))),
        )


@dataclass(frozen=True)
class ProductRule:
    category: str
    risk_level: str
    keywords: KeywordSet


@dataclass(frozen=True)
class FingerprintRule:
    family: str
    risk_level: str
    keywords: KeywordSet
    products: tuple[ProductRule, ...] = ()


@dataclass(frozen=True)
class SoftwareProfile:
    name: str
    family: str
    category: str
    risk_level: str
    matched_by: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["matched_by"] = list(self.matched_by)
        return result

