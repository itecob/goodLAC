# Native Local Consumer Contract v1

**Task:** `LAC-PI003`
**Contract:** `lac.native-local-consumer-contract/v1`

## Purpose and authority boundary

This is the smallest versioned local-consumer surface stabilized from the accepted B003,
PI001, PI002 and D001 paths. It is a local controller contract, not a generic transport
protocol and not an authority system.

The controller remains authoritative for principal, agent, application and skill identity;
capability registration/revision; standing policy; exact approval; emergency pause; execution
lease; adapter dispatch; credentials; receipts and durable effect state. A consumer cannot
supply or mutate those values through this contract.

Pi remains the sole reference harness for the active v1 roadmap. A non-Pi conformance fixture
exists only to prove that these semantics are consumer-neutral; it is not another harness
integration.

## Request

The native v1 request deliberately reuses the already accepted
`lac.external-consumer-request/v1` schema rather than introducing a parallel authority request.
It contains exactly:

- `schema`
- `request_id`
- `run_id`
- `action`
- `resource`
- `arguments`
- `idempotency_key`

Unknown fields fail closed. In particular, consumer-supplied principal/agent/application/skill
identity, capability revision, policy/authority decisions, approval identifiers,
administration operations, lease/executor identifiers and credential references are rejected.
The controller-created durable B003 binding over principal + agent + application + skill remains
required before request reuse, status disclosure, approval discovery, receipt replay or effect
dispatch.

## Result

`lac.native-local-consumer-result/v1` contains exactly:

- `schema`
- `request_id`
- `canonical_request_hash`
- `authority_outcome`: `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`
- `execution_state`
- `reason`
- `decision_id` or null
- typed `result` or null
- bounded public `receipt` or null
- `replayed`
- `permission_configuration`
- `workflow_continuation` or null

`permission_configuration` is informational workflow metadata only. `required=true` binds one
pending-permission identifier and reason after the canonical request has already been terminally
closed. It is never authorization.

## Continuation status

`lac.native-local-consumer-continuation-status/v1` exposes only bounded workflow state:

- continuation/original-request/pending identities;
- state and expiry;
- whether the one fresh-request budget was consumed;
- fresh request/decision identities when one was actually claimed;
- pending-resolution baseline revision;
- bounded outcome and owner-resolution projection.

Captured arguments and idempotency material are not exposed through status. Continuation state
contains no service credential and exposes no administration operation.

States are `WAITING_PERMISSION`, `FRESH_REQUEST_CLAIMED`, `PENDING_APPROVAL`, `COMPLETED`,
`CLOSED_NONAUTH`, and `EXPIRED`.

## Explicit resume

`lac.native-local-consumer-resume/v1` contains exactly `schema`, `continuation_id`, and
`expected_request` (the immutable original request or null for explicit restart recovery).
The host result is `lac.native-local-consumer-resume-result/v1` with `ok`, `kind`,
`workflow_continuation`, and `result`.

Resume never revives the original denied request. An owner disposition may make a continuation
eligible to claim **at most one fresh request identity**; that fresh request traverses the full
current capability, policy, exact-approval, emergency, lease, dispatch, sandbox and receipt
path. `NO_CHANGE`, dismissal, expiry, malformed/stale state, mutation mismatch and ambiguous
state are non-authorizing. A fresh request that is still configuration-denied consumes the
one-shot budget and does not recursively create another automatic continuation.

Continuation state may survive restart, but startup/list/status are read-only. Dispatch requires
an explicit resume call. Restart itself never authorizes or dispatches an effect.

## Compatibility and persistence

Unsupported schema versions and unknown fields fail closed; v1 does not negotiate or silently
ignore extensions. The accepted D001 Pi-specific continuation record remains the internal v1
durable representation so PI003 does not migrate or reinterpret already accepted state. The
consumer-neutral runtime facade validates that representation and projects only the native v1
status/result schemas. This persistence compatibility is implementation detail, not a second
public contract.

## Conformance

`scripts/test-pi003` proves:

- a stdlib-only non-Pi fixture can use the request/result/status/resume contract without LAC or
  administrator imports;
- controller-owned four-dimensional request binding still prevents cross-consumer reuse;
- authority/admin/credential-bearing, unsupported, malformed, stale and mutated material fails
  closed;
- original permission-denied requests remain terminal and continuation uses at most one fresh
  request;
- non-authorizing outcomes perform no effect;
- governed Pi emits the same stabilized native result/status surface;
- the complete retained `scripts/test-pi002-d001` -> `scripts/test-pi001` -> Phase 4 chain still
  passes using local synthetic fixtures only.
