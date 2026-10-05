# goodLAC 1.0.0-rc.12 - Release Notes

**1.0.0-rc.12** is the first goodLAC release intended for ordinary public use.

goodLAC is a source-available Local Agent Controller developed by ITECOB Inc. It places a deterministic authority/effect boundary between agent/model requests and consequential execution.

> **Model output is not authorization.**

## What rc.12 provides

- default-governed installed `pi` entrypoint;
- pinned Pi 0.85.1 reference harness;
- exact four-tool model-facing effect surface:
  - `lac_fs_read`
  - `lac_fs_create`
  - `lac_fs_replace`
  - `lac_shell_exec`
- owner permission decisions and standing policy;
- project-aware permission scope and isolation;
- exact one-time approval binding;
- policy re-evaluation immediately before dispatch;
- durable execution leases, receipts and effect truth;
- idempotency and duplicate-effect prevention;
- credential separation from the governed model context;
- owner-only administration surface;
- emergency pause;
- fail-closed handling of stale, malformed, expired, unknown or inconsistent authority state;
- explicit fresh-request-only continuation after permission configuration;
- versioned user-level installation and rollback.

## Public release identity

Accepted private source candidate:

`f83fcf57a30b85288796f04161c8e1fc2fc28936`

Qualified sanitized-history head:

`e9a816b69a0ed09ac74900f6da9e4578a3782a02`

Qualified publication snapshot:

`447f4dd23f5f56d90ec40ac2b344793f9dbf575a`

Qualified publication tree:

`c0ad5a4a9cb392f4f100177c0a3631e6f0a58e39`

The public repository contains a privacy-sanitized historical lineage. Earlier development states are retained for provenance and are not recommendations to deploy those states.

## Installation

See [`INSTALL.md`](INSTALL.md).

For the fastest evaluation:

```bash
git clone https://github.com/itecob/goodLAC.git
cd goodLAC
python3 scripts/p006_owner_permission_demo.py --auto
```

## Runtime limitation

The full managed local-model path requires the exact qualified Pi and FreeToken checkouts plus the accepted model/runtime assets. rc.12 does not yet provide a one-command public bootstrap for those heavyweight assets and will not silently substitute unqualified versions.

## Platform

The accepted reference path is Linux. Qualification claims do not automatically extend to unreviewed operating systems, modified builds, alternate harnesses, or unrelated runtime combinations.

## Security

Private vulnerability reporting is available through the repository Security interface.

See [`../SECURITY.md`](../SECURITY.md).

## License

See [`../LICENSE`](../LICENSE) and [`../COMMERCIAL-LICENSING.md`](../COMMERCIAL-LICENSING.md).

## Contributions

External code and other copyrightable contributions are not currently being accepted for incorporation into goodLAC. Bug reports, feature requests, reproducible observations and other feedback are welcome.

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
