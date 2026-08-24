# Background Component Cleaner

Task008 adds a fail-closed component layer around the existing software profile and Task005 authorization flow.

## Pipeline

`scanner -> matcher -> planner -> web confirmation -> authorized executor -> verifier -> audit log`

`ComponentScanner` accepts injected records for tests and offline agents. `WindowsComponentScanner` only reads Windows service, registry/startup-folder, scheduled-task and process state; it does not mutate the host. Rules live under `rules/component_behavior/` and are loaded as YAML rather than hard-coded in the planner.

## Protection boundary

Microsoft/Windows components, WPS, Office, WeChat, QQ, browsers, input-method bodies and user dictionaries are always converted to a protected C0 record. Unknown or unmatched components are also record-only. The planner's default maximum is C2. C3/C4 plans remain visible for explicit confirmation and are never silently executed.

## Execution boundary

`ComponentTaskHandler` requires a valid Task005 authorization context and re-plans the supplied component before dispatch. `ComponentExecutor` uses an injected backend; without one it is dry-run only. A protected component or a plan with missing confirmation is blocked. No password, UAC bypass, remote shell, hidden persistence, or automatic server connection is implemented.

## Server and dashboard

The SQLite store persists component inventory and returns it with device details. The dashboard displays type, publisher, risk, level, protection and suggested action. It creates only the existing `approved_action` task shape; the target Agent remains responsible for local authorization and permission checks.

## Test posture

Tests use fake providers/backends and never scan or modify the development computer. Production deployment must supply a reviewed target-side backend, signed/validated task transport and a visible user confirmation host before any C1-C3 action is enabled.
