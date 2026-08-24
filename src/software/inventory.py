"""Read-only Windows installed-software inventory adapter."""

from __future__ import annotations

import sys


def collect_windows_inventory() -> list[dict[str, str]]:
    """Read standard uninstall registry keys without changing system state."""
    if sys.platform != "win32":
        return []
    import winreg

    locations = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    results: dict[tuple[str, str, str], dict[str, str]] = {}
    for hive, location in locations:
        try:
            root = winreg.OpenKey(hive, location, access=winreg.KEY_READ)
        except OSError:
            continue
        with root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                try:
                    key_name = winreg.EnumKey(root, index)
                    with winreg.OpenKey(root, key_name, access=winreg.KEY_READ) as entry:
                        name = _value(entry, "DisplayName")
                        if not name:
                            continue
                        publisher = _value(entry, "Publisher")
                        path = _value(entry, "InstallLocation")
                        record = {"name": name, "publisher": publisher, "install_path": path}
                        results[(name.casefold(), publisher.casefold(), path.casefold())] = record
                except OSError:
                    continue
    return sorted(results.values(), key=lambda item: item["name"].casefold())


def _value(key: object, name: str) -> str:
    import winreg

    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value or "")
    except OSError:
        return ""

