# ACTIVE TASK — LAC-PI003

## Task ID
`LAC-PI003`

## Objective
Stabilize the native local consumer contract and deterministic conformance surface already
proven by the production LAC-governed Pi reference path, including the accepted D001
permission-gated workflow-continuation semantics.

This task converts the Pi-proven integration boundary into a versioned local-consumer contract
that another local consumer can implement without importing Pi-specific host mechanics or
creating a second authority model.

## Binding constraints

1. Pi remains the sole reference harness for the active v1 roadmap.
2. LAC remains the authority/effect controller; a consumer contract is not authority.
3. Preserve Phase 4 principal/agent/application/skill binding, capability validation, standing
   policy, exact approval, emergency, lease, idempotency, receipt and credential isolation.
4. Preserve ADR-009 / INV-020: a permission-discovery request is terminally closed; any
   workflow continuation is separate, non-authoritative, bounded and uses a fresh request.
5. Stabilization must describe/version the already-proven native local consumer behavior; do
   not add a generic compatibility facade, new harness integration, external product, or new
   model-provider surface.
6. Consumer-supplied authority/admin/credential material remains rejected.
7. Ordinary standalone Pi remains outside the LAC-governed claim.

## In scope

- Identify the smallest versioned native local-consumer request/result/status/continuation
  contract implied by the accepted B003, PI001, PI002 and D001 implementations.
- Separate consumer-neutral contract semantics from Pi-specific terminal/broker mechanics.
- Add deterministic conformance fixtures/tests proving a non-Pi fixture can exercise the
  contract without importing administrator capability or bypassing the controller.
- Include continuation status/resume semantics, one-shot fresh-request identity, explicit
  non-authorizing outcomes and restart-safe explicit resume in the conformance surface where
  required by the accepted Pi behavior.
- Document compatibility/versioning/fail-closed behavior for unsupported or malformed
  consumer material.
- Run the complete retained Phase 5/Phase 4 deterministic regression chain.

## Out of scope

- A generic compatibility protocol facade merely for breadth.
- Additional harness integrations.
- Chief of Staff or other external-product implementation.
- Additional model-provider expansion.
- Product packaging/UI (`LAC-V001`).
- Weakening or redesigning accepted authority semantics.

## Acceptance

- One explicit versioned native local-consumer contract is documented and represented in
  deterministic code/tests without Pi-specific authority logic leaking into the controller.
- A separate local fixture demonstrates conformance through the authoritative controller path.
- Malformed, authority-bearing, admin-bearing, credential-bearing, stale and unsupported
  consumer material fails closed.
- D001 continuation semantics remain non-authoritative and one-shot; original denied requests
  cannot be revived.
- No alternate filesystem/process/network/admin/effect path is introduced.
- Production governed Pi remains conformant to the stabilized contract.
- `scripts/test-pi002-d001`, `scripts/test-pi001`, and applicable Phase 4 gates remain PASS.
- No active-roadmap scope expansion occurs.

## Next task on success

Create the Phase 5 candidate and hand it to one fresh **phase-boundary independent review**.
Do not begin `LAC-V001` until that review returns PASS.
