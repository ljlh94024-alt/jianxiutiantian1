"""Native fixed-function Windows Service Control Manager adapter."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any

from .safety import ensure_windows, validate_component


SC_MANAGER_CONNECT = 0x0001
SERVICE_QUERY_CONFIG = 0x0001
SERVICE_QUERY_STATUS = 0x0004
SERVICE_CHANGE_CONFIG = 0x0002
SERVICE_START = 0x0010
SERVICE_STOP = 0x0020
SERVICE_NO_CHANGE = 0xFFFFFFFF
SERVICE_DISABLED = 0x00000004
SERVICE_CONTROL_STOP = 0x00000001
SERVICE_STOPPED = 0x00000001
SC_STATUS_PROCESS_INFO = 0


class _ServiceStatusProcess(ctypes.Structure):
    _fields_ = [("service_type", wintypes.DWORD), ("current_state", wintypes.DWORD), ("controls", wintypes.DWORD), ("win32_exit", wintypes.DWORD), ("service_exit", wintypes.DWORD), ("check_point", wintypes.DWORD), ("wait_hint", wintypes.DWORD), ("process_id", wintypes.DWORD), ("flags", wintypes.DWORD)]


class _QueryServiceConfig(ctypes.Structure):
    _fields_ = [("service_type", wintypes.DWORD), ("start_type", wintypes.DWORD), ("error_control", wintypes.DWORD), ("binary_path", wintypes.LPWSTR), ("load_order", wintypes.LPWSTR), ("tag_id", wintypes.DWORD), ("dependencies", wintypes.LPWSTR), ("start_name", wintypes.LPWSTR), ("display_name", wintypes.LPWSTR)]


class WindowsServiceManager:
    """Disable/restore one exact service without invoking a shell."""

    def _handles(self, name: str):
        ensure_windows()
        api = ctypes.WinDLL("advapi32", use_last_error=True)
        manager = api.OpenSCManagerW(None, None, SC_MANAGER_CONNECT)
        if not manager:
            raise OSError(ctypes.get_last_error(), "OpenSCManagerW failed")
        service = api.OpenServiceW(manager, name, SERVICE_QUERY_CONFIG | SERVICE_QUERY_STATUS | SERVICE_CHANGE_CONFIG | SERVICE_START | SERVICE_STOP)
        if not service:
            api.CloseServiceHandle(manager)
            raise OSError(ctypes.get_last_error(), f"OpenServiceW failed for {name}")
        return api, manager, service

    @staticmethod
    def _close(api, manager, service) -> None:
        api.CloseServiceHandle(service)
        api.CloseServiceHandle(manager)

    def snapshot(self, component: dict[str, Any]) -> dict[str, Any]:
        component = validate_component(component)
        if component.get("type", component.get("component_type")) != "service":
            raise ValueError("service manager only accepts service components")
        api, manager, service = self._handles(component["name"])
        try:
            needed = wintypes.DWORD()
            api.QueryServiceConfigW(service, None, 0, ctypes.byref(needed))
            buffer = ctypes.create_string_buffer(needed.value)
            if not api.QueryServiceConfigW(service, ctypes.cast(buffer, ctypes.POINTER(_QueryServiceConfig)), needed, ctypes.byref(needed)):
                raise OSError(ctypes.get_last_error(), "QueryServiceConfigW failed")
            config = ctypes.cast(buffer, ctypes.POINTER(_QueryServiceConfig)).contents
            status = _ServiceStatusProcess()
            needed_status = wintypes.DWORD()
            if not api.QueryServiceStatusEx(service, SC_STATUS_PROCESS_INFO, ctypes.byref(status), ctypes.sizeof(status), ctypes.byref(needed_status)):
                raise OSError(ctypes.get_last_error(), "QueryServiceStatusEx failed")
            return {"name": component["name"], "path": config.binary_path or "", "startup_type": int(config.start_type), "state": int(status.current_state)}
        finally:
            self._close(api, manager, service)

    def disable_service(self, component: dict[str, Any]) -> None:
        before = self.snapshot(component)
        api, manager, service = self._handles(component["name"])
        try:
            if not api.ChangeServiceConfigW(service, SERVICE_NO_CHANGE, SERVICE_DISABLED, SERVICE_NO_CHANGE, None, None, None, None, None, None, None):
                raise OSError(ctypes.get_last_error(), "ChangeServiceConfigW failed")
            if before["state"] != SERVICE_STOPPED:
                status = _ServiceStatusProcess()
                if not api.ControlService(service, SERVICE_CONTROL_STOP, ctypes.byref(status)):
                    error = ctypes.get_last_error()
                    # ERROR_SERVICE_NOT_ACTIVE is already a safe stopped result.
                    if error != 1062:
                        raise OSError(error, "ControlService stop failed")
        finally:
            self._close(api, manager, service)

    def restore_service(self, snapshot: dict[str, Any]) -> None:
        api, manager, service = self._handles(str(snapshot["name"]))
        try:
            if not api.ChangeServiceConfigW(service, SERVICE_NO_CHANGE, int(snapshot["startup_type"]), SERVICE_NO_CHANGE, None, None, None, None, None, None, None):
                raise OSError(ctypes.get_last_error(), "ChangeServiceConfigW restore failed")
            if int(snapshot.get("state", SERVICE_STOPPED)) != SERVICE_STOPPED and not api.StartServiceW(service, 0, None):
                raise OSError(ctypes.get_last_error(), "StartServiceW restore failed")
        finally:
            self._close(api, manager, service)

    def verify_disabled(self, component: dict[str, Any]) -> bool:
        state = self.snapshot(component)
        return state["startup_type"] == SERVICE_DISABLED and state["state"] == SERVICE_STOPPED
