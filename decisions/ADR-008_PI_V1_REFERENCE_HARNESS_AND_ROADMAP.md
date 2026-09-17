# ADR-008 — Pi v1 Reference Harness and Product Roadmap

**Status:** ACCEPTED BY OWNER  
**Date:** 2026-09-17

## Context

Phase 4 completed the reusable permission-management and external-consumer authority boundary. The project also already has a real Pi integration from A001-A004, but the owner-facing A004 Pi path predates P001-P006 and still uses a fixed local qualification policy. The two accepted paths therefore prove different halves of the product but are not yet joined into one production user path.

The owner requires the first usable LAC product to be exercised in a real supported harness before additional integrations or products are added.

## Decision

1. **Pi is the sole reference harness for the active LAC v1 roadmap.**
2. The next LAC work joins the real Pi path to the accepted Phase 4 permission-aware runtime.
3. LAC-governed Pi is an explicit launch/profile with a constrained tool surface and sandbox. Ordinary Pi remains separately runnable outside that profile; LAC makes no governance claim for an unmanaged Pi process.
4. The governed Pi path must reuse the canonical LAC capability, policy, approval, identity, lease, receipt, emergency and state semantics. Pi-specific integration code stays at the edge and must not create a second authority model.
5. A protocol or tool-transport connection is not itself an enforcement boundary. The v1 roadmap therefore does not add a generic compatibility facade merely for breadth. A future transport/interface may be added only when a concrete product requirement exists and only if the governed launch/bypass model remains explicit.
6. Additional harness integrations are not part of the active v1 roadmap.
7. External application/product projects are not part of the LAC roadmap. They may consume the finished LAC contract from their own repositories when their owners choose to start them.
8. Additional model-provider expansion is not part of the current active roadmap. The existing `ModelProvider` abstraction remains the boundary for future work.

## v1 sequence from the accepted Phase 4 boundary

```text
LAC-PI001  production LAC-governed Pi integration
LAC-PI002  real owner UAT of permission-aware Pi
LAC-PI003  stabilize the native local consumer contract/conformance surface proven by Pi
LAC-V001   v1 packaging/productization of the accepted Pi reference path
```

A phase-boundary independent review occurs after the Pi production-integration/conformance phase is complete, before v1 productization is accepted.

## Security consequence

A harness being able to call LAC is not sufficient to call the harness "LAC-governed." Governed mode requires that consequential effects cannot take an alternate route around LAC. For Pi v1 this means a qualified LAC-managed launch/profile, bounded ambient authority, controller-backed effect tools only, credential/admin isolation, and deterministic bypass tests.

## Product consequence

LAC remains a standalone authority/effect-control product. Pi is the reference user-facing harness for v1, not part of the authority core. The design must continue to keep harness-specific mechanics outside canonical policy, approval, identity, state and effect semantics.
