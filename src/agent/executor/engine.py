"""Safety-gated orchestration for fixed package and component operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cleaner import InputMethodCleaner
from .installer import Installer
from .safety import SafetyGate, SoftwareExecutionRequest
from .uninstaller import Uninstaller
from .verifier import Verifier


class SafeSoftwareExecutor:
    def __init__(self, gate: SafetyGate, installer: Installer, uninstaller: Uninstaller, cleaner: InputMethodCleaner, verifier: Verifier):
        self.gate = gate
        self.installer = installer
        self.uninstaller = uninstaller
        self.cleaner = cleaner
        self.verifier = verifier

    def execute(
        self,
        request: SoftwareExecutionRequest,
        package_path: str | Path | None = None,
        uninstall_command: tuple[str, ...] = (),
        verification_tests: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        try:
            self.gate.validate(request)
            if request.operation == "install_replacement":
                result = self.installer.install(request.package or "", package_path, execute=not request.dry_run)
            elif request.operation == "uninstall_component":
                result = self.uninstaller.uninstall(request, uninstall_command, execute=not request.dry_run)
            elif request.operation == "optimize_input_method":
                result = self.cleaner.optimize(request, execute=not request.dry_run)
            else:
                return {"status": "failed", "reason": "unsupported_operation"}
            if result.get("status") != "success" or not verification_tests:
                return result
            verification = self.verifier.verify(verification_tests)
            if not verification.passed:
                return {"status": "failed", "reason": "verification_failed", "tests": list(verification.tests), "details": verification.details}
            result["verification"] = {"passed": True, "tests": list(verification.tests)}
            return result
        except Exception as exc:
            return {"status": "failed", "reason": "safety_or_execution_error", "error": str(exc)}

    def as_task_handler(self) -> "SafeSoftwareTaskHandler":
        return SafeSoftwareTaskHandler(self)


class SafeSoftwareTaskHandler:
    """Adapter for WhitelistExecutor; it cannot run without Agent authorization."""

    requires_authorization = True

    def __init__(self, engine: SafeSoftwareExecutor):
        self.engine = engine

    def run(self, task, authorized: bool) -> dict[str, Any]:
        if not authorized:
            return {"status": "authorization_required"}
        parameters = task.parameters
        try:
            request = SoftwareExecutionRequest(
                target_id=task.target_id,
                operation=str(parameters["operation"]),
                software=str(parameters["software"]),
                package=parameters.get("package"),
                human_confirmed=True,
                permission_granted=authorized,
                dry_run=bool(parameters.get("dry_run", True)),
            )
        except KeyError as exc:
            return {"status": "failed", "reason": f"missing execution parameter: {exc.args[0]}"}
        command = tuple(str(item) for item in parameters.get("uninstall_command", []))
        tests = tuple(str(item) for item in parameters.get("verification_tests", []))
        return self.engine.execute(request, parameters.get("package_path"), command, tests)
