# ACTIVE TASK — LAC-P004

## Task ID

`LAC-P004`

## Objective

Implement the isolated local administrator API and Linux owner-identity boundary for capability/permission administration, wrapping the already-internal P001–P003 mutation surfaces without exposing them to governed runtime consumers.

## In scope

- Define a versioned local administration request/response contract for capability registration, standing-policy replacement/revocation, pending-permission inspection/administrative resolution semantics, and exact-approval administration needed by the later CLI.
- Implement a separate owner-only Unix-domain administration socket beneath the owning user's runtime directory.
- Enforce owner-only filesystem permissions and controller-observed Linux peer UID before any administrative operation is accepted.
- Keep the admin endpoint unavailable inside governed agent sandboxes and logically separate from the runtime effect-submission surface.
- Wrap existing internal P001 registry, P002 pending-permission, and P003 standing-policy mutation/read surfaces; do not duplicate canonical state.
- Ensure every administrative mutation remains atomic, revisioned/auditable where applicable, and incapable of reviving any closed effect.
- Add deterministic local/synthetic unit, integration, and negative-security tests plus the accepted regression gate through P003/P002/P001/B001.

## Out of scope

- `lacctl` command-line client (`LAC-P005`).
- Permission-management E2E/security qualification (`LAC-P006`).
- Calendar (`LAC-B002`), generic external-consumer proof (`LAC-B003`), Chief of Staff, OpenClaw, Omarchy Agent OS, web UI/TUI, enterprise RBAC, remote administration, or multi-user policy.
- Weakening P001 zero-authority registration, P002 terminal quarantine/non-resumability, P003 deterministic standing-policy semantics, exact approval binding, credential isolation, emergency pause, or any other LAC invariant.

## Required outputs

- Versioned isolated administration protocol/domain.
- Owner-only Unix-domain admin transport with deterministic peer-UID enforcement.
- Administrative handlers wrapping canonical registry/pending/policy/approval state without runtime exposure.
- Tests proving unauthorized/wrong-UID/runtime access cannot mutate administration state and closed effects remain closed.
- Applicable accepted regression evidence.
- One owner-executable package completing P004 and activating fresh `LAC-P005` on success.

## Next task on success

`LAC-P005` in a fresh implementation session.
