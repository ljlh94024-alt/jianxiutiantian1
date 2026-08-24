"""Fixed-package installer with hash and bundled-component checks."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


FORBIDDEN_BUNDLE_TERMS = {"browser", "input_method", "security", "desktop_assistant", "ad", "promotion", "ime"}


class PackageError(ValueError):
    pass


@dataclass(frozen=True)
class PackageSpec:
    name: str
    version: str
    sha256: str
    source: str
    silent_args: tuple[str, ...]
    verification: tuple[str, ...]
    forbidden_components: tuple[str, ...] = ()


class PackageCatalog:
    def __init__(self, specs: dict[str, PackageSpec]):
        self.specs = specs

    @classmethod
    def load(cls, directory: str | Path) -> "PackageCatalog":
        specs = {}
        for path in sorted(Path(directory).glob("*/package.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            required = ("name", "version", "sha256", "source", "silent_args", "verification")
            if any(key not in data for key in required):
                raise PackageError(f"Package manifest is incomplete: {path}")
            sha = str(data["sha256"]).lower()
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise PackageError(f"Package manifest has invalid sha256: {path}")
            specs[str(data["name"])] = PackageSpec(
                str(data["name"]), str(data["version"]), sha, str(data["source"]),
                tuple(str(arg) for arg in data["silent_args"]), tuple(str(test) for test in data["verification"]),
                tuple(str(item) for item in data.get("forbidden_components", [])),
            )
        if not specs:
            raise PackageError(f"No package manifests found in {directory}")
        return cls(specs)


class CommandRunner(Protocol):
    def run(self, executable: Path, arguments: tuple[str, ...]) -> int: ...


class ProcessRunner:
    def run(self, executable: Path, arguments: tuple[str, ...]) -> int:
        completed = subprocess.run([str(executable), *arguments], check=False)  # noqa: S603
        return completed.returncode


class Installer:
    def __init__(self, catalog: PackageCatalog, runner: CommandRunner | None = None):
        self.catalog = catalog
        self.runner = runner

    def install(self, package_name: str, package_path: str | Path | None, execute: bool = False) -> dict[str, Any]:
        spec = self.catalog.specs.get(package_name)
        if spec is None:
            return {"status": "failed", "reason": "package_not_allowlisted", "package": package_name}
        if spec.sha256 == "0" * 64:
            return {"status": "failed", "reason": "package_hash_not_provisioned", "package": package_name}
        if package_path is None or not Path(package_path).is_file():
            return {"status": "failed", "reason": "package_unavailable", "package": package_name}
        path = Path(package_path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != spec.sha256:
            return {"status": "failed", "reason": "package_hash_mismatch", "package": package_name}
        bundle = self._bundle_components(path)
        forbidden = set(bundle).intersection(FORBIDDEN_BUNDLE_TERMS.union(spec.forbidden_components))
        if forbidden:
            return {"status": "failed", "reason": "forbidden_bundle_components", "components": sorted(forbidden)}
        if not execute:
            return {"status": "ready", "package": package_name, "version": spec.version, "dry_run": True}
        if self.runner is None:
            return {"status": "failed", "reason": "process_runner_not_configured"}
        code = self.runner.run(path, spec.silent_args)
        return {"status": "success" if code == 0 else "failed", "returncode": code, "package": package_name}

    @staticmethod
    def _bundle_components(package_path: Path) -> set[str]:
        manifest = package_path.with_suffix(package_path.suffix + ".manifest.json")
        if not manifest.is_file():
            return set()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        components = data.get("components", []) if isinstance(data, dict) else []
        return {str(item).casefold() for item in components}

