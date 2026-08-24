"""Fixed-function Windows execution backends with snapshots and rollback."""

from .engine import WindowsComponentTaskHandler, WindowsExecutionBackend, WindowsExecutionEngine
from .file_cleaner import WindowsFileCleaner
from .rollback import RollbackManager
from .service_manager import WindowsServiceManager
from .snapshot import SnapshotStore
from .startup_manager import WindowsStartupManager
from .task_manager import WindowsTaskManager
from .verifier import WindowsExecutionVerifier

__all__ = [
    "RollbackManager", "SnapshotStore", "WindowsComponentTaskHandler",
    "WindowsExecutionBackend", "WindowsExecutionEngine", "WindowsFileCleaner", "WindowsServiceManager",
    "WindowsStartupManager", "WindowsTaskManager", "WindowsExecutionVerifier",
]
