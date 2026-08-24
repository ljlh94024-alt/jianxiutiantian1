"""Fail-closed policy for fixed replacement and component-cleanup operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ExecutionOperation = Literal["install_replacement", "uninstall_component", "optimize_input_method"]
ALLOWED_OPERATIONS = {"install_replacement", "uninstall_component", "optimize_input_method"}
FORBIDDEN_OPERATIONS = {"delete", "delete_all", "uninstall_all", "format", "disable_security", "hidden_execute"}


class SafetyError(ValueError):
    """Raised before any system operation is allowed to start."""


@dataclass(frozen=True)
class SoftwareExecutionRequest:
    target_id: str
    operation: ExecutionOperation
    software: str
    package: str | None = None
    human_confirmed: bool = False
    permission_granted: bool = False
    dry_run: bool = True


class SafetyGate:
    PROTECTED_NAMES = (
        "WPS", "Microsoft Office", "LibreOffice", "微信", "WeChat", "QQ", "企业微信", "钉钉", "飞书",
        "搜狗输入法", "百度输入法", "Microsoft Edge", "Google Chrome", "Mozilla Firefox", "360浏览器", "2345浏览器",
        "Photoshop", "AutoCAD", "Lightroom",
    )
    UNINSTALL_ALLOWLIST = {
        "360压缩", "360安全卫士", "360杀毒", "360驱动大师", "2345看图王", "2345好压", "2345安全组件",
        "驱动人生", "驱动精灵", "快压",
    }

    def validate(self, request: SoftwareExecutionRequest) -> None:
        if request.operation not in ALLOWED_OPERATIONS or request.operation in FORBIDDEN_OPERATIONS:
            raise SafetyError(f"Operation is not allowed: {request.operation}")
        if not request.target_id.strip() or not request.software.strip():
            raise SafetyError("target_id and software are required")
        if not request.human_confirmed:
            raise SafetyError("Human confirmation is required")
        if not request.permission_granted and not request.dry_run:
            raise SafetyError("Required Agent permission was not granted")
        protected = next((item for item in self.PROTECTED_NAMES if item.casefold() in request.software.casefold()), None)
        if protected and request.operation != "optimize_input_method":
            raise SafetyError(f"Protected software cannot be modified: {protected}")
        if request.operation == "optimize_input_method":
            if "输入法" not in request.software and "input" not in request.software.casefold():
                raise SafetyError("optimize_input_method only accepts an input method target")
            return
        if request.operation == "uninstall_component":
            if request.software not in self.UNINSTALL_ALLOWLIST:
                raise SafetyError(f"Software is not on the exact uninstall allowlist: {request.software}")
        if request.operation == "install_replacement" and not request.package:
            raise SafetyError("A fixed package name is required")

