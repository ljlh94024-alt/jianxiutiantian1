"""Match software profiles to replacement recommendations."""

from __future__ import annotations

from collections.abc import Iterable
import re

from .database import ReplacementData


def _matches_name(software_name: str, candidate: str) -> bool:
    folded_name = software_name.casefold()
    folded_candidate = candidate.casefold()
    if folded_candidate.isascii():
        pattern = rf"(?<![a-z0-9]){re.escape(folded_candidate)}(?![a-z0-9])"
        return re.search(pattern, folded_name) is not None
    return folded_candidate in folded_name


class ReplacementMatcher:
    def __init__(self, data: ReplacementData):
        self.data = data

    def match(self, profile: dict) -> dict | None:
        software_name = str(profile.get("name", "")).strip()
        if not software_name:
            return None
        # Browsers are an explicit user-protected category. Do not make migration
        # suggestions even if a browser entry is added to the data later.
        if str(profile.get("category", "")).casefold() == "browser":
            return None
        profile_category = str(profile.get("category", "")).casefold()
        candidates = []
        for entry in self.data.replacements.values():
            if profile_category not in {"", "unknown"} and profile_category != entry["category"].casefold():
                continue
            names = [entry["name"], *entry.get("aliases", [])]
            matched_names = [name for name in names if _matches_name(software_name, str(name))]
            if matched_names:
                candidates.append((max(len(str(name)) for name in matched_names), entry))
        if not candidates:
            return None
        entry = max(candidates, key=lambda candidate: candidate[0])[1]
        return {
            "software": software_name,
            "function": entry["category"],
            "category": entry["category"],
            "capabilities": list(entry["function"]),
            "suggestions": [dict(suggestion) for suggestion in entry["replacement"]],
        }

    def match_all(self, profiles: Iterable[dict]) -> list[dict]:
        return [suggestion for profile in profiles if (suggestion := self.match(profile)) is not None]
