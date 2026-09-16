# ACTIVE TASK — LAC-P006-UAT

## Task ID

`LAC-P006-UAT`

## Objective

Perform owner-facing acceptance and operator walkthrough of the completed P001-P006 permission-management plane before B002, and close the clarified first-use permission-discovery requirement without weakening any accepted authority invariant.

## Owner requirement added at this gate

A first-time request for a **registered/known capability that has no user-configured matching standing permission/default** must not silently collapse into an unexplained default denial.

Required behavior for that unconfigured-permission case:

```text
fresh request arrives
→ capability/resource/material is already registered and valid
→ no applicable user-configured standing permission/default exists
→ terminal DENY for this effect
→ no execution lease
→ no adapter mutation
→ create/aggregate a bounded owner-reviewable permission-configuration item
→ original effect remains closed forever
→ owner configures future permission through the isolated admin plane
→ application/agent must issue a fresh request
→ fresh request is evaluated against current policy
```

This does **not** add a fourth runtime authority state. Enforcement remains `DENY`. It is administrative discovery/work for future requests, not a resumable effect or exact approval.

An explicit user-configured `DENY` (including a matching configured default) is already a decision and must not be treated as an unconfigured permission merely to generate repeated review noise.

## In scope

- Give the owner a practical operator walkthrough of the software already built: project/evidence status, the real A004 model/harness/controller/sandbox terminal, the P004/P005 owner admin boundary and `lacctl`, P001 capability registration, P002 pending queue, P003 standing policy, exact approval, original-request non-resumption, receipts/duplicate prevention, and negative-security checks.
- Add owner-visible deterministic adversarial stress that does not rely on model cooperation: deliberately attack the Model→Pi tool boundary, Pi process sandbox, filesystem/shell adapters, sandbox containment, and P004-P006 administration/permission boundaries. The stress gate must include unknown tool names, authority-field smuggling, malformed arguments, host-file/network/credential/process attempts, traversal/symlink escape, unauthorized executables/interpreters/launchers, child-process containment, explicit DENY, exact approval, wrong-UID admin paths, and admin-socket isolation.
- Demonstrate standing-policy outcomes directly in the owner permission walkthrough: configured `DENY`, a deterministic conditional `ALLOW` ("allow if"), `REQUIRE_APPROVAL`, and `ALLOW`, with adapter invocation counts proving which paths did or did not execute.
- Treat permissive/less-refusal local-model testing as a supplemental behavioral stress layer, not as the security oracle. Any alternate model/runtime must be separately qualified and must not replace deterministic hostile-request tests.
- Keep walkthrough state isolated under owner-local cache/runtime paths. Do not use production Gmail/Calendar credentials or external consequential effects.
- Verify and, where necessary, minimally remediate the known-capability/no-configured-policy discovery behavior described above.
- Preserve P001 registration as zero authority, P002 closed-effect non-resumption, deterministic P003 precedence, P004/P005 admin isolation, P006 acceptance, exact approval binding, re-evaluation before dispatch, deny precedence, idempotency, credential isolation, and fail-closed behavior.
- Update binding permission-management/contracts documentation if implementation semantics are amended.
- Run focused tests plus applicable deterministic accepted regression.
- Produce one owner-executable completion package that activates fresh `LAC-B002` only after this UAT/remediation passes.
- Strengthen the B002 handoff so Calendar qualification explicitly exercises: first-use terminal deny + owner-reviewable permission item; owner scope configuration; proof original request cannot resume; fresh request; then `ALLOW`/`REQUIRE_APPROVAL`/`DENY` handling.

## Out of scope

- Implementing the Calendar adapter itself.
- Chief of Staff workflow/business logic.
- B003, OpenClaw, Omarchy Agent OS, web/TUI, remote administration, enterprise RBAC.
- Production external service credentials or consequential external effects.

## Required outputs

- Owner walkthrough remains usable and documented.
- Focused deterministic proof of the clarified unconfigured-permission discovery behavior.
- Any minimal controller/admin-state remediation required by that proof.
- Updated binding docs/contracts where needed.
- Regression evidence showing no accepted invariant weakened.
- Owner-executable handoff package to B002 with the strengthened first-use Calendar sequence.

## Next task on success

`LAC-B002` in a fresh implementation session.
