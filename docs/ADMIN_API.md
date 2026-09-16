# Local Administrator API — P004 v1

**Status:** Binding implementation contract for `LAC-P004`.

## Boundary

The administrator surface is separate from the runtime effect-submission surface. On Linux v0.1, the controller listens only on an owner-only Unix-domain socket at:

```text
$XDG_RUNTIME_DIR/lac/admin-v1.sock
```

If `XDG_RUNTIME_DIR` is unset, `/run/user/<owner-uid>` is used. The runtime directory and `lac/` subdirectory must be real, canonical, owner-owned directories with no group/other permission bits. The socket is mode `0600` and owned by the controller owner UID.

The controller obtains Linux peer credentials with `SO_PEERCRED` and compares the peer UID to the configured owner UID **before it reads or parses administrator request bytes**. A wrong-UID peer is closed without executing an operation.

Governed agent sandboxes do not mount the owner runtime directory or administrator socket. Runtime adapters and `Dispatcher` expose no administration mutation method.

The v0.1 boundary does not claim protection from arbitrary unsandboxed software already executing as the same owner UID.

## Framing and schemas

One connection carries exactly one UTF-8 JSON request terminated by `\n` and receives exactly one canonical JSON response terminated by `\n`. A message is bounded to 262,144 bytes.

Request schema:

```json
{
  "schema": "lac.admin-request/v1",
  "request_id": "admin-request:example",
  "operation": "skills.list",
  "arguments": {}
}
```

Response schema:

```json
{
  "schema": "lac.admin-response/v1",
  "request_id": "admin-request:example",
  "ok": true,
  "result": {},
  "error": null
}
```

Protocol objects reject duplicate JSON keys, unknown top-level fields, unsupported operations, non-JSON values, and oversized messages.

## Operations

The v1 operations are:

- `skills.list`, `skills.show`, `skills.register`
- `permissions.list`, `permissions.show`, `permissions.replace`, `permissions.revoke`
- `pending.list`, `pending.show`, `pending.resolve`, `pending.dismiss`
- `approvals.list`, `approvals.show`, `approvals.approve`, `approvals.reject`

`skills.register` wraps P001 `CapabilityRegistry.register_admin`; registration remains descriptive and grants zero authority.

`permissions.replace` and `permissions.revoke` wrap P003 `StandingPolicyRepository.replace_admin`; replacement/revocation creates a new canonical standing-policy revision. Revocation never edits historical revisions.

`pending.resolve` and `pending.dismiss` append owner disposition records in a separate administration namespace. They never modify the P002 pending record, immutable capability-denial closure, effect request, lease, or execution state. Resolution can therefore affect only later administrator configuration and future fresh requests.

`approvals.approve` and `approvals.reject` operate on an existing durable `REQUIRE_APPROVAL` policy-decision ID. They create at most one immutable exact approval decision through the existing approval repository. Approval expiry is clamped to the canonical effect request expiry, and the service refuses a new approval after request expiry or after execution has begun. Dispatcher policy re-evaluation remains mandatory before dispatch.

## Permission replacement material

`permissions.replace` accepts exact arrays of canonical `lac.standing-policy-rule/v1` and `lac.standing-policy-default/v1` material. `permissions.revoke` accepts `{ "kind": "RULE"|"DEFAULT", "id": "..." }` and writes a new policy revision with the selected item removed.

## Pending resolution material

`pending.resolve` accepts a P002 `pending_id` plus one of:

- `POLICY_UPDATED`
- `CAPABILITY_UPDATED`
- `POLICY_AND_CAPABILITY_UPDATED`
- `NO_CHANGE`

`pending.dismiss` records `DISMISSED`. These records are append-only, revisioned, owner-UID attributed, and contain no free-form secret-bearing note field.

## Runtime non-authority

Nothing in this API changes these contracts:

- P001 registration grants zero authority.
- P002 unknown/new material is terminally denied and cannot resume.
- P003 conditions consume only P002-validated trusted metadata.
- Exact approvals bind one canonical request and are rechecked at dispatch.
- Runtime consumers cannot mutate registry, standing policy, pending administration state, or exact approvals through the runtime interface.
