# ACTIVE TASK — LAC-P003

## Task ID

`LAC-P003`

## Objective

Implement the deterministic scoped/conditional standing-permission policy model over trusted capability/resource/request metadata, while preserving all existing authority invariants and the P002 terminal unknown-request quarantine.

## In scope

- Define a versioned canonical standing-policy rule/snapshot model with outcomes `ALLOW`, `REQUIRE_APPROVAL`, and `DENY`.
- Scope rules by principal, application/agent, skill, action, resource selector, and deterministic conditions over trusted capability/resource/request metadata.
- Implement most-specific-match evaluation and equal-specificity precedence `DENY > REQUIRE_APPROVAL > ALLOW`.
- Support configured application/skill defaults; absence of a matching fallback remains `DENY`.
- Ensure non-overridable controller invariants and P002 capability/resource/material-shape validation run before standing policy.
- Keep policy mutation internal/controller-only in P003; external admin socket/API remains P004 scope.
- Add deterministic unit/integration/negative-security tests and run the accepted regression gate including P001, P002, and B001.

## Out of scope

- External administrator Unix-domain socket/API and peer-UID authentication (`LAC-P004`).
- `lacctl` (`LAC-P005`).
- Permission-management E2E (`LAC-P006`).
- Calendar (`LAC-B002`), generic external-consumer proof (`LAC-B003`), Chief of Staff, OpenClaw, Omarchy Agent OS, web UI/TUI, enterprise RBAC, or model-authored policy.
- Resuming any P002-closed effect. Policy changes affect only fresh requests.

## Required outputs

- Canonical standing-policy domain/repository/evaluator.
- Deterministic specificity and deny-precedence behavior.
- Trusted-metadata conditional evaluation only.
- Tests proving defaults, specificity, conflicts, fail-closed unknowns, P002 closure preservation, and zero runtime administration authority.
- Applicable accepted regression evidence.
- One owner-executable package completing P003 and activating fresh `LAC-P004` on success.

## Next task on success

`LAC-P004` in a fresh implementation session.
