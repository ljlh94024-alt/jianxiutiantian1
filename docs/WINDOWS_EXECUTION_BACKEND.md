# Windows execution backend and rollback

Task009 keeps the existing Task005 consent and permission handshake as the only entry into a real action. The backend exposes named Python methods; it has no generic `execute(command)` method and never builds a shell command.

## Components

- `WindowsServiceManager` uses the Windows Service Control Manager through `ctypes`. It snapshots exact service configuration, changes only the start type to disabled, stops that exact service, verifies stopped/disabled, and can restore the previous start type/state.
- `WindowsStartupManager` handles only an exact HKCU `Run` value or a file under an explicitly known Startup folder. It stores the original registry value or filename and restores it on rollback.
- `WindowsTaskManager` uses Task Scheduler COM (`pywin32`) for exact task paths. Creator/author and executable path must match before deletion. XML and enabled state are stored for restoration.
- `WindowsFileCleaner` requires an explicit named root in its allowlist and records SHA-256, size and mtime before removing one exact file/directory. It rejects paths outside that root.

## Engine contract

`WindowsExecutionEngine.execute()` checks target identity, authorization, protection and confirmation, then snapshots, dispatches one fixed action, verifies it, and writes an audit record. A failure returns immediately; it does not continue to another operation. With `dry_run=True` it returns a plan without invoking any manager or creating a backup.

Register `WindowsComponentTaskHandler` explicitly under the existing Task005 `approved_action` whitelist. The backend is not auto-registered and therefore cannot silently turn an existing Agent into a system modifier.

`RollbackManager` accepts only a snapshot ID below its configured backup root and only restores service, startup or scheduled-task snapshots. Rollback is itself an authorized task and is target-bound. A file component returns `rollback_not_supported_for_component_type` rather than guessing how to restore user data.

## Production requirements

Production must inject reviewed managers, a visible UAC/permission provider, authenticated Agent transport, and a protected backup location. The repository's tests use fake managers and temporary backups; they never scan or modify the development computer.
