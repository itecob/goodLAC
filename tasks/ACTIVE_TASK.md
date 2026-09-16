# ACTIVE TASK — LAC-P005

## Task ID

`LAC-P005`

## Objective

Implement the first authoritative local `lacctl` administration client as a thin consumer of the accepted P004 owner-only administrator API. The CLI must not write canonical controller state directly and must not create an alternate administration authority path.

## In scope

- Implement a local `lacctl` command-line client that connects only to the P004 owner-only Unix-domain administrator socket.
- Support deterministic human-readable output plus machine-readable JSON for operations equivalent to:
  - `lacctl skills list`
  - `lacctl skills show <skill>`
  - `lacctl permissions list`
  - `lacctl permissions show ...`
  - `lacctl permissions set ...`
  - `lacctl permissions revoke ...`
  - `lacctl pending list`
  - `lacctl pending show <id>`
  - `lacctl pending resolve <id> ...`
  - `lacctl pending dismiss <id>`
  - `lacctl approvals list`
  - `lacctl approvals show <id>`
  - `lacctl approvals approve <id>`
  - `lacctl approvals reject <id>`
- Use only the versioned P004 admin protocol; no SQLite/system-state direct writes and no imports of internal mutation repositories from the CLI.
- Fail closed on malformed responses, socket/identity boundary failures, unsupported protocol versions, ambiguous command arguments, or unavailable administrator endpoint.
- Add deterministic local/synthetic unit/integration tests and the accepted regression gate through P004/P003/P002/P001/B001.

## Out of scope

- Permission-management E2E/security qualification (`LAC-P006`).
- Calendar (`LAC-B002`), generic external-consumer proof (`LAC-B003`), Chief of Staff, OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, enterprise RBAC, or multi-user policy.
- Direct mutation of the LAC database or bypass of the P004 administrator transport.
- Weakening any LAC invariant or P001–P004 contract.

## Required outputs

- `lacctl` local administration client consuming P004 admin API only.
- Machine-readable JSON output mode and deterministic bounded human-readable output.
- Tests proving the CLI has no direct canonical-state mutation path and fails closed when the P004 admin boundary rejects/unavailable/malformed conditions.
- Applicable accepted regression evidence.
- One owner-executable package completing P005 and activating fresh `LAC-P006` on success.

## Next task on success

`LAC-P006` in a fresh implementation session.
