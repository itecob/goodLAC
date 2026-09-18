# ADR-009 — Permission-Gated Workflow Continuation Without Effect Resurrection

**Status:** ACCEPTED BY OWNER  
**Date:** 2026-09-17

## Context

LAC Phase 4 deliberately makes an unconfigured effect request terminal: the request is denied,
permission-discovery work is recorded for the owner, and later configuration never revives that
request. LAC-PI002 owner UAT confirmed the security value of this rule, but also exposed a
workflow problem in the Pi reference path: an ordinary terminal denial can cause the model or
user workflow to stop, require manual re-prompting, or encourage the model to search for another
route to accomplish the same effect.

The owner wants Codex-like interaction semantics—pause for a human permission decision and
continue afterward—without weakening fail-closed authorization.

## Decision

1. **Effect authorization and workflow continuation remain separate concepts.**
2. The original unconfigured effect request remains terminal `DENY` and permanently
   non-resumable. This preserves accepted Phase 4 invariants.
3. The governed consumer may maintain a separate, bounded, non-authoritative continuation state
   representing a blocked workflow/tool turn.
4. On `permission_configuration.required`, the trusted host suspends the workflow before the
   model can treat the denial as an ordinary failure and improvise alternative consequential
   effect routes.
5. Permission configuration remains an owner-admin action through the isolated admin plane.
6. After owner resolution, the host may make at most one automatic continuation attempt from the
   immutable captured intent. It creates a **fresh canonical effect request** with new request and
   idempotency identity.
7. The fresh request passes complete current capability validation, standing policy, exact
   approval when required, emergency pause, lease, dispatch, sandbox and receipt processing.
8. A changed action/resource/security-relevant argument is not continuation; it is a new proposal.
9. `DENY`, dismissal, no-change, expiry, malformed state, or any ambiguous status produces no
   effect and an explicit non-authorizing/owner-declined workflow outcome.
10. Continuation state must be restart-recoverable, but restart alone never dispatches the effect.
    A trusted owner/consumer resume event is required before the one fresh submission.
11. Continuation state grants no authority and contains no service credentials.
12. Equivalent permission-discovery aggregation must never merge the authority or continuation
    identity of distinct denied effect requests.

## Security consequence

The strongest accepted rule remains unchanged: **later policy or registry changes never revive
a closed effect**. Usability is improved above that boundary by resuming the workflow with a new
request, not by changing the authorization status of the old request.

The model-facing process still cannot configure permissions, create approvals, access the owner
admin socket, or bypass the controller. Suspending the workflow also reduces incentive for the
model to probe alternate effect routes after a permission-configuration denial.

## Product consequence

The Pi v1 reference harness gains a safe permission-wait/resume interaction. This is an edge
workflow behavior, not a second authority system and not a general workflow-engine expansion of
LAC.

PI003 must not stabilize the native consumer contract until this behavior is implemented and
qualified in `LAC-PI002-D001`.

## Roadmap amendment

The active Phase 5 sequence becomes:

`LAC-PI001 -> LAC-PI002 -> LAC-PI002-D001 -> LAC-PI003 -> phase-boundary independent review -> LAC-V001`
