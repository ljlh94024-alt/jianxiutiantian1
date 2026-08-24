"""Load extensible software fingerprints from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import FingerprintRule, KeywordSet, ProductRule


VALID_RISK_LEVELS = {"S0", "S1", "S2", "S3"}


class FingerprintRuleError(ValueError):
    """Raised when a fingerprint YAML file is invalid."""


class FingerprintDatabase:
    def __init__(self, rules: tuple[FingerprintRule, ...]):
        self.rules = rules

    @classmethod
    def load(cls, directory: str | Path) -> "FingerprintDatabase":
        rule_dir = Path(directory)
        if not rule_dir.is_dir():
            raise FileNotFoundError(f"Fingerprint rule directory not found: {rule_dir}")
        rules = tuple(cls._load_file(path) for path in sorted(rule_dir.glob("*.yaml")))
        if not rules:
            raise FingerprintRuleError(f"No YAML fingerprint rules found in {rule_dir}")
        families = [rule.family.casefold() for rule in rules]
        if len(families) != len(set(families)):
            raise FingerprintRuleError("Fingerprint family names must be unique")
        return cls(rules)

    @staticmethod
    def _load_file(path: Path) -> FingerprintRule:
        try:
            data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise FingerprintRuleError(f"Invalid YAML in {path}: {exc}") from exc
        if not isinstance(data, dict) or not str(data.get("family", "")).strip():
            raise FingerprintRuleError(f"Rule {path} must define a family")
        default_risk = str(data.get("risk_level", "S1"))
        FingerprintDatabase._validate_risk(default_risk, path)
        products = []
        for product in data.get("products", []) or []:
            if not isinstance(product, dict) or not product.get("category"):
                raise FingerprintRuleError(f"Every product in {path} needs a category")
            risk = str(product.get("risk_level", default_risk))
            FingerprintDatabase._validate_risk(risk, path)
            products.append(ProductRule(str(product["category"]), risk, KeywordSet.from_dict(product.get("keywords"))))
        return FingerprintRule(
            family=str(data["family"]),
            risk_level=default_risk,
            keywords=KeywordSet.from_dict(data.get("keywords")),
            products=tuple(products),
        )

    @staticmethod
    def _validate_risk(risk: str, path: Path) -> None:
        if risk not in VALID_RISK_LEVELS:
            raise FingerprintRuleError(f"Invalid risk level {risk!r} in {path}")

