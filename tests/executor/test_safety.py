import hashlib
import json
from pathlib import Path

from src.agent.executor import (
    InputMethodCleaner,
    Installer,
    PackageCatalog,
    SafeSoftwareExecutor,
    SafetyGate,
    SoftwareExecutionRequest,
    Uninstaller,
    VerificationResult,
    Verifier,
    WhitelistExecutor,
)
from src.controller.task_sender import TaskSender


class Runner:
    def __init__(self, code=0):
        self.code = code
        self.calls = []

    def run(self, *args):
        self.calls.append(args)
        return self.code


class Verify:
    def __init__(self, passed=True):
        self.passed = passed

    def run_test(self, name):
        return self.passed


class Backend:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda software: self.calls.append((name, software))


def request(operation, software, **kwargs):
    return SoftwareExecutionRequest("PC001", operation, software, human_confirmed=True, **kwargs)


def test_fixed_manifests_are_present_and_unprovisioned():
    catalog = PackageCatalog.load("packages")
    assert set(catalog.specs) == {"ImageGlass", "7-Zip", "VLC"}
    assert catalog.specs["7-Zip"].sha256 == "0" * 64
    assert Installer(catalog).install("7-Zip", None) ["reason"] == "package_hash_not_provisioned"


def test_protected_software_is_never_uninstalled():
    gate = SafetyGate()
    request_item = request("uninstall_component", "WPS Office")
    result = Uninstaller(gate).uninstall(request_item, ("uninstall.exe",))
    assert result["status"] == "failed"
    assert "Protected" in result["reason"] or "Protected" in result.get("error", "")


def test_uninstaller_rejects_arbitrary_executable():
    request_item = request("uninstall_component", "360压缩")
    result = Uninstaller(SafetyGate()).uninstall(request_item, ("powershell.exe", "-Command", "Remove-Item"))
    assert result["reason"] == "uninstall_executable_not_allowlisted"


def test_browser_and_input_method_rules():
    gate = SafetyGate()
    browser = request("uninstall_component", "360浏览器")
    assert "Protected" in str(SafeSoftwareExecutor(gate, Installer(PackageCatalog.load("packages")), Uninstaller(gate), InputMethodCleaner(gate), Verifier()).execute(browser, uninstall_command=("x",)))
    backend = Backend()
    cleaner = InputMethodCleaner(gate, backend)
    result = cleaner.optimize(request("optimize_input_method", "搜狗输入法"), execute=True)
    assert result["status"] == "success"
    assert len(backend.calls) == 4


def test_bundle_detection_rejects_forbidden_component(tmp_path: Path):
    package = tmp_path / "ImageGlass.exe"
    package.write_bytes(b"trusted-test-package")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(".exe.manifest.json").write_text(json.dumps({"components": ["browser"]}), encoding="utf-8")
    manifest_dir = tmp_path / "viewer"
    manifest_dir.mkdir()
    (manifest_dir / "package.json").write_text(
        json.dumps({"name": "ImageGlass", "version": "1", "sha256": digest, "source": "local", "silent_args": [], "verification": ["open_jpg"]}),
        encoding="utf-8",
    )
    result = Installer(PackageCatalog.load(tmp_path)).install("ImageGlass", package)
    assert result["reason"] == "forbidden_bundle_components"


def test_verified_install_uses_injected_runner_only(tmp_path: Path):
    package = tmp_path / "7z.exe"
    package.write_bytes(b"trusted-test-package")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    manifest_dir = tmp_path / "archive"
    manifest_dir.mkdir()
    (manifest_dir / "package.json").write_text(
        json.dumps({"name": "7-Zip", "version": "1", "sha256": digest, "source": "local", "silent_args": ["/S"], "verification": ["extract_zip"]}),
        encoding="utf-8",
    )
    runner = Runner()
    installer = Installer(PackageCatalog.load(tmp_path), runner)
    result = installer.install("7-Zip", package, execute=True)
    assert result["status"] == "success"
    assert runner.calls


def test_engine_stops_on_failed_verification(tmp_path: Path):
    package = tmp_path / "7z.exe"
    package.write_bytes(b"trusted-test-package")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (tmp_path / "archive").mkdir()
    (tmp_path / "archive" / "package.json").write_text(json.dumps({"name": "7-Zip", "version": "1", "sha256": digest, "source": "local", "silent_args": [], "verification": ["extract_zip"]}), encoding="utf-8")
    gate = SafetyGate()
    engine = SafeSoftwareExecutor(gate, Installer(PackageCatalog.load(tmp_path), Runner()), Uninstaller(gate), InputMethodCleaner(gate), Verifier(Verify(False)))
    result = engine.execute(request("install_replacement", "2345好压", package="7-Zip", permission_granted=True, dry_run=False), package, verification_tests=("extract_zip",))
    assert result["status"] == "failed"
    assert result["reason"] == "verification_failed"


def test_task_handler_requires_task005_authorization(tmp_path):
    gate = SafetyGate()
    engine = SafeSoftwareExecutor(gate, Installer(PackageCatalog.load("packages")), Uninstaller(gate), InputMethodCleaner(gate), Verifier())
    handler = engine.as_task_handler()
    executor = WhitelistExecutor({"approved_action": handler})
    task = TaskSender().create("PC001", "exec_001", "approved_action", "L1", True, {"operation": "install_replacement", "software": "2345看图王", "package": "ImageGlass"})
    assert executor.execute(task)["status"] == "authorization_required"
    assert executor.execute(task, authorized=True)["status"] == "failed"  # package is intentionally not provisioned
