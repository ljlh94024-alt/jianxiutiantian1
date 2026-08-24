# Safe Software Execution

Task007 is the first execution-layer package, but it remains fail-closed.

## Fixed packages

`packages/viewer/package.json` → ImageGlass

`packages/archive/package.json` → 7-Zip

`packages/player/package.json` → VLC

These are manifests only. A zero SHA-256 marks a package that has not been provisioned. The installer never downloads from `source`; a local file must be supplied, match the manifest hash, and have no forbidden bundle component.

## Allowed operations

- `install_replacement`
- `uninstall_component` for exact allowlisted names only
- `optimize_input_method` for promotion cleanup only

The safety gate rejects browsers, WPS/Office/LibreOffice, communication software, professional software, input-method replacement, broad uninstall, delete, format, security disabling, hidden execution and missing human confirmation.

## Execution and verification

The Agent's Task005 consent/permission handshake must finish before `SafeSoftwareTaskHandler` runs. The default package metadata is not provisioned and the default verifier has no system backend. Production deployment must inject a reviewed package cache, a visible permission host, an exact uninstall resolver, and a verifier. A failed install, cleanup, or verification returns `failed` and stops the chain; it never proceeds to another deletion.

