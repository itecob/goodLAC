# ACTIVE TASK — LAC-PI002-D001

## Task ID
`LAC-PI002-D001`

## Objective
Implement secure permission-gated workflow continuation for the governed Pi v1 path without
weakening the accepted Phase 4 rule that an unconfigured effect request is terminally denied
and can never be revived.

The user-facing workflow should pause for owner permission configuration instead of exposing
an ordinary tool failure that invites the model to improvise alternate consequential-effect
paths. After owner configuration, continuation may submit exactly one fresh request derived
from the immutable captured intent.

## Binding design

1. The original unconfigured effect remains terminal `DENY`. It never resumes, is never
   converted to pending execution, and later policy/registry changes never authorize it.
2. The existing pending-permission record remains informational/administrative only and
   never grants authority.
3. A separate continuation object/state is non-authoritative. It may retain only the bounded
   information required to suspend/resume the consumer workflow.
4. When Pi receives `permission_configuration.required=true`, the trusted host/broker must
   transition the current workflow/tool turn to an explicit owner-permission wait state before
   returning an ordinary failure to the model.
5. While waiting, the model must not be allowed to continue the turn and search for equivalent
   consequential-effect routes.
6. Owner policy configuration remains exclusively through the accepted owner administration
   plane. The model-facing process receives no admin socket or policy mutation capability.
7. After the owner resolves/configures permission, the host may perform at most one automatic
   continuation attempt using the immutable captured operation, but that attempt MUST be a
   fresh canonical effect request with a new request/idempotency identity and complete current
   capability/policy/approval/emergency/dispatch re-evaluation.
8. If the resulting current policy is `REQUIRE_APPROVAL`, normal exact-approval semantics apply.
   If it is `DENY`, dismissed, unresolved, malformed, expired, or otherwise non-authorizing,
   no effect occurs and the model receives an explicit owner-declined/non-authorizing outcome.
9. Any material mutation of action/resource/security-relevant arguments invalidates the
   continuation; it must become a new proposal/request rather than reusing the owner's prior
   permission decision.
10. Continuation retry is bounded to one automatic fresh submission per owner resolution.
    There is no infinite retry loop.
11. Continuation state must survive a governed-Pi restart sufficiently to recover the blocked
    user workflow, but restart alone must never dispatch the effect. Recovery requires an
    explicit owner/consumer resume event and then a fresh authority evaluation.
12. Continuation storage/output must not contain raw service credentials or create an alternate
    authority, effect, filesystem, process, network, or admin path.
13. Distinct denied requests must not become confused merely because pending-permission
    discovery aggregates equivalent permission work.
14. Ordinary standalone Pi remains outside the LAC-governed claim.

## In scope
- Governed Pi host/broker workflow behavior for `permission_configuration.required`.
- A bounded, non-authoritative continuation state/token/record as needed.
- Read-only status/signaling needed for the trusted host to know the owner has resolved the
  permission item, without giving the model or sandbox administration authority.
- Fresh-request resubmission mechanics and one-shot continuation budget.
- Explicit user/model-visible outcomes for waiting, owner denial/non-authorization, successful
  fresh continuation, and `REQUIRE_APPROVAL`.
- Restart recovery of blocked workflow state without automatic dispatch.
- Deterministic unit/integration/acceptance/adversarial tests.
- Documentation updates to the Pi v1 governed profile and native-consumer contract material
  needed for later PI003 stabilization.

## Out of scope
- Reviving any terminal effect request.
- Changing accepted Phase 4 `ALLOW` / `REQUIRE_APPROVAL` / `DENY` authority semantics.
- Giving the model-facing process administrator capability.
- Additional harnesses, external products, generic compatibility facades, model-provider
  expansion, or Phase 6 work.
- Product UI beyond the minimum owner-facing CLI/terminal behavior needed to prove the contract.

## Acceptance
- Original first-use request remains durably terminal and non-resumable.
- Governed Pi pauses the tool/workflow before the model can continue after configuration-required denial.
- Owner configuration occurs only through the isolated admin plane.
- Exactly one fresh request is generated from unchanged captured intent after authorized continuation.
- Fresh request has a new request/idempotency identity and passes complete current authority evaluation.
- `ALLOW`, `REQUIRE_APPROVAL`, and `DENY` after continuation each behave correctly.
- Mutation, stale/expired state, duplicate resume, restart-only recovery, malformed state, and
  cross-request confusion all fail closed.
- Restart preserves recoverability but never auto-dispatches.
- Model/admin/credential/host-fs/process/network/direct-effect bypass resistance remains intact.
- Existing PI001/PI002 and Phase 4 regression gates pass.
- No accepted Phase 4 invariant is weakened.

## Next task on success
`LAC-PI003` — stabilize the native local consumer contract/conformance surface proven by Pi.
