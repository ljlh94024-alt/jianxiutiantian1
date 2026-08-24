"""Exact-name component uninstaller; no broad or inferred removal."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .safety import SafetyError, SafetyGate, SoftwareExecutionRequest


class UninstallRunner(Protocol):
    def run(self, command: tuple[str, ...]) -> int: ...


class Uninstaller:
    ALLOWED_EXECUTABLES = {"uninstall.exe", "unins000.exe", "msiexec.exe", "setup.exe"}

    def __init__(self, gate: SafetyGate, runner: UninstallRunner | None = None):
        self.gate = gate
        self.runner = runner

    def uninstall(self, request: SoftwareExecutionRequest, command: tuple[str, ...], execute: bool = False) -> dict[str, Any]:
        try:
            self.gate.validate(request)
        except SafetyError as exc:
            return {"status": "failed", "reason": str(exc)}
        if request.operation != "uninstall_component":
            raise ValueError("Uninstaller only accepts uninstall_component")
        if not command or any(not str(part).strip() for part in command):
            return {"status": "failed", "reason": "empty_uninstall_command"}
        executable = Path(command[0]).name.casefold()
        if executable not in self.ALLOWED_EXECUTABLES:
            return {"status": "failed", "reason": "uninstall_executable_not_allowlisted"}
        if any(any(character in str(part) for character in "&|<>\n\r") for part in command):
            return {"status": "failed", "reason": "unsafe_uninstall_argument"}
        if not execute:
            return {"status": "ready", "software": request.software, "dry_run": True}
        if self.runner is None:
            return {"status": "failed", "reason": "uninstall_runner_not_configured"}
        code = self.runner.run(tuple(command))
        return {"status": "success" if code == 0 else "failed", "returncode": code, "software": request.software}
