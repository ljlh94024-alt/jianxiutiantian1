"""Create target-bound migration recommendations from analysis artifacts."""

from __future__ import annotations

from collections.abc import Iterable

from .models import MigrationPlanError, MigrationPlanItem, TargetProfile
from .protection import ProtectionPolicy


class MigrationPlanner:
    def __init__(self, target: TargetProfile, policy: ProtectionPolicy):
        self.target = target
        self.policy = policy

    def create_plan(self, profiles: Iterable[dict], suggestions: Iterable[dict]) -> list[MigrationPlanItem]:
        profile_list = list(profiles)
        suggestion_list = list(suggestions)
        self._assert_same_target((*profile_list, *suggestion_list))
        suggestions_by_name = {str(item.get("software", "")).casefold(): item for item in suggestion_list}
        return [self._plan_item(profile, suggestions_by_name.get(str(profile.get("name", "")).casefold())) for profile in profile_list]

    def _assert_same_target(self, records: Iterable[dict]) -> None:
        records = tuple(records)
        missing_count = sum(not record.get("target_id") for record in records)
        if missing_count:
            raise MigrationPlanError(
                f"{missing_count} input record(s) have no target_id; rescan and analyze with a target profile"
            )
        mismatches = {
            str(record["target_id"])
            for record in records
            if record.get("target_id") and str(record["target_id"]) != self.target.target_id
        }
        if mismatches:
            raise MigrationPlanError(
                f"Input target_id does not match {self.target.target_id}: {', '.join(sorted(mismatches))}"
            )

    def _plan_item(self, profile: dict, suggestion: dict | None) -> MigrationPlanItem:
        software = str(profile.get("name", "")).strip()
        if not software:
            raise MigrationPlanError("Software profile contains an empty name")
        category = str(profile.get("category", "unknown"))
        risk = str(profile.get("risk_level", "S0"))
        decision = self.policy.evaluate(profile)
        if decision.action == "ignore":
            return MigrationPlanItem(
                self.target.target_id, software, category, None, (), "ignore", risk, decision.protection, False,
                reason=decision.reason,
            )
        if decision.action == "report_only":
            return MigrationPlanItem(
                self.target.target_id, software, category, None, (), "report_only", risk, decision.protection, False,
                reason=decision.reason,
            )
        if decision.action == "review":
            return MigrationPlanItem(
                self.target.target_id, software, category, None, (), "review", risk, decision.protection,
                reason=decision.reason,
            )
        if suggestion is None:
            return MigrationPlanItem(
                self.target.target_id, software, category, None, (), "blocked", risk, decision.protection,
                reason="Target software has no validated replacement suggestion.",
            )
        replacements = tuple(str(item["name"]) for item in suggestion.get("suggestions", []))
        verification = tuple(
            dict.fromkeys(
                test
                for item in suggestion.get("suggestions", [])
                for test in item.get("verification", [])
            )
        )
        if not replacements:
            return MigrationPlanItem(
                self.target.target_id, software, category, None, (), "blocked", risk, decision.protection,
                reason="Replacement record contains no candidate.",
            )
        return MigrationPlanItem(
            self.target.target_id,
            software,
            str(suggestion.get("function", category)),
            replacements[0],
            replacements,
            "recommend",
            risk,
            decision.protection,
            verification_required=verification,
            reason="Recommendation only; verification and explicit human confirmation are required.",
        )
