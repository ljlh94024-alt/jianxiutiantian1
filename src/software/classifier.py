"""Classify inventory records by matching YAML fingerprints."""

from __future__ import annotations

from collections.abc import Iterable

from .fingerprint import FingerprintDatabase
from .models import KeywordSet, SoftwareInventoryItem, SoftwareProfile


FIELD_KEYWORDS = {
    "name": "names",
    "publisher": "publishers",
    "install_path": "paths",
    "file_paths": "files",
}


def _matched_fields(item: SoftwareInventoryItem, keywords: KeywordSet) -> tuple[str, ...]:
    matched = []
    values = item.searchable_values()
    for field, keyword_attr in FIELD_KEYWORDS.items():
        candidates = [value.casefold() for value in values[field] if value]
        needles = [value.casefold() for value in getattr(keywords, keyword_attr) if value]
        if any(needle in candidate for needle in needles for candidate in candidates):
            matched.append(field)
    return tuple(matched)


class SoftwareClassifier:
    def __init__(self, database: FingerprintDatabase):
        self.database = database

    def classify(self, raw_item: dict) -> SoftwareProfile | None:
        item = SoftwareInventoryItem.from_dict(raw_item)
        best: tuple[int, SoftwareProfile] | None = None
        for family_rule in self.database.rules:
            family_matches = _matched_fields(item, family_rule.keywords)
            product_matches = []
            for product in family_rule.products:
                matched = _matched_fields(item, product.keywords)
                if matched:
                    product_matches.append((len(matched), product, matched))
            if not family_matches and not product_matches:
                continue
            if product_matches:
                _, product, specific_matches = max(product_matches, key=lambda result: result[0])
                all_matches = tuple(dict.fromkeys((*specific_matches, *family_matches)))
                category, risk = product.category, product.risk_level
                score = 100 + len(specific_matches) * 10 + len(family_matches)
            else:
                all_matches = family_matches
                category, risk = "unknown", family_rule.risk_level
                score = len(family_matches)
            profile = SoftwareProfile(item.name, family_rule.family, category, risk, all_matches)
            if best is None or score > best[0]:
                best = (score, profile)
        return best[1] if best else None

    def classify_all(self, inventory: Iterable[dict], include_unmatched: bool = False) -> list[dict]:
        profiles = []
        for raw_item in inventory:
            profile = self.classify(raw_item)
            if profile:
                profiles.append(profile.to_dict())
            elif include_unmatched:
                profiles.append(
                    SoftwareProfile(
                        SoftwareInventoryItem.from_dict(raw_item).name,
                        "unknown",
                        "unknown",
                        "S0",
                    ).to_dict()
                )
        return profiles

