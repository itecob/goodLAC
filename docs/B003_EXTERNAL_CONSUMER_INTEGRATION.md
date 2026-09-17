# B003 Generic External-Consumer Integration

**Task:** `LAC-B003`
**Status:** corrected Phase 4 candidate; P4-B001 controller-owned identity binding pending fresh independent re-review after owner verification

## Boundary proved

A separate application may provide a canonical capability declaration and submit strict JSON typed-effect request material. The declaration is descriptive only. It does not register itself, set policy, create approvals, choose controller identities, create execution leases, or gain a credential capability.

The controller binds the external application to one configured `principal_id`, `agent_id`, `application_id`, and `skill_id`. These four values are controller-owned runtime configuration, not declaration-derived authority. The declaration's `application_id` and `skill_id` are compatibility/schema claims that must exactly match the controller-owned application/skill binding before capability lookup or standing-policy evaluation. The external request schema accepts only:

- `schema`
- `request_id`
- `run_id`
- `action`
- `resource`
- `arguments`
- `idempotency_key`

Any consumer-supplied identity, authority decision, capability revision, approval identifier, lease/executor identifier, administration operation, credential reference, or other extra top-level material is rejected before dispatch.

## Capability declaration and registration

`ExternalConsumerDeclaration` validates the ordinary `lac.capability-manifest/v1` declaration without mutating canonical registry state. Its application/skill identity is non-authoritative declaration material. `ExternalConsumerRuntime` first validates those claims against the controller-owned `application_id`/`skill_id` binding; mismatch fails closed before standing policy, lease creation, or adapter invocation. Canonical registration remains owner/admin-only through the accepted P004/P005 administration surface. An identity-matched but unregistered declaration enters the existing P002 unknown-capability fail-closed path. A declaration that does not match the current owner-registered manifest revision cannot execute.

Registration alone still grants zero authority. A valid registered request with no applicable owner-configured standing permission remains terminally denied and creates bounded permission-configuration work for a fresh future request.

## Runtime authority sequence

`ExternalConsumerRuntime` is controller-side code. It constructs/reuses the canonical `EffectRequest` using controller-bound principal/agent identity, resolves the current registered capability revision, derives trusted resource type from the canonical manifest, and invokes the existing capability-aware `Dispatcher`.

The external consumer receives only the three authority outcomes:

- `ALLOW`
- `REQUIRE_APPROVAL`
- `DENY`

For `REQUIRE_APPROVAL`, the consumer receives the policy-decision identifier needed for owner inspection, but it cannot create or supply an approval. On a later identical retry, LAC discovers an unconsumed owner-created exact approval from canonical controller state and passes that approval to the dispatcher. Immediate policy re-evaluation remains in the dispatcher, so a later `DENY` still wins and an obsolete approval is not consumed.

An owner `REJECT` is treated as terminal for that exact request at this runtime boundary. A P002 capability denial remains closed through later capability/policy administration. Only a fresh request may use later authority.

## Result and receipt surface

A successful effect returns the typed adapter result plus a public receipt projection containing controller binding/hashes and outcome metadata. Raw `result_json` is not duplicated into the public receipt projection. Credential-shaped result keys fail closed at this boundary; effect adapters remain responsible for never returning credentials under innocuous fields.

A duplicate identical request returns the existing terminal result/receipt and does not invoke the adapter a second time.

## Separate consumer fixture

`tests/fixtures/b003_external_consumer_app.py` is a stdlib-only process that imports no LAC package. It emits a capability declaration/request and validates a returned runtime response. The controller-side acceptance test registers the declaration only through the admin service and feeds the fixture's JSON request through the generic runtime boundary.

No Chief of Staff workflow or business logic is present.

## Security/regression requirement

`scripts/test-b003` runs the B003-focused integration/negative-security suite and then the accepted B002 gate, which in turn reruns the accepted deterministic P006/P006-UAT and prior regression. The B003 proof therefore retains explicit `DENY`, conditional standing-policy, exact approval, admin-socket isolation, capability closure, credential isolation, sandbox and prior authority/effect coverage.

All B003 mutation fixtures are synthetic/local. No production Gmail/Calendar credential or consequential external effect is required.
