# `lacctl` — Local Administration Client

**Status:** P005 v0.1 client for the accepted P004 administrator API.

`lacctl` is a thin local client. It is not a canonical state writer and does not open the LAC SQLite database. Every supported administration operation is encoded as `lac.admin-request/v1` and sent to the P004 owner-only Unix-domain administrator endpoint.

## Boundary

Production `lacctl` resolves exactly:

```text
$XDG_RUNTIME_DIR/lac/admin-v1.sock
```

or, when `XDG_RUNTIME_DIR` is unset:

```text
/run/user/<owner-uid>/lac/admin-v1.sock
```

The client fails closed unless the runtime directory and `lac/` directory are canonical real owner-owned directories with no group/other permission bits, the endpoint is a real owner-owned Unix socket with mode `0600`, and Linux `SO_PEERCRED` reports the connected server process as the current owner UID. The client verifies the server peer UID before it sends request bytes.

The CLI exposes no database/state-file option and no arbitrary socket override. It does not import LAC state, capability, standing-policy, approval-repository, or P004 service mutation implementations.

## Output modes

Human-readable output is the default. List operations use deterministic bounded tabular/summary output; detailed objects use stable sorted JSON formatting.

Use `--json` anywhere in the command to emit canonical compact JSON. Successful machine output is the P004 operation result. Operational failures are non-zero and emit `lac.lacctl-error/v1` when `--json` is selected.

## Commands

```text
lacctl skills list
lacctl skills show <application_id> <skill_id> [--revision N]

lacctl permissions list
lacctl permissions show [--revision N]
lacctl permissions set --file <policy.json>
lacctl permissions revoke <rule|default> <id>

lacctl pending list
lacctl pending show <pending_id>
lacctl pending resolve <pending_id> <POLICY_UPDATED|CAPABILITY_UPDATED|POLICY_AND_CAPABILITY_UPDATED|NO_CHANGE>
lacctl pending dismiss <pending_id>

lacctl approvals list
lacctl approvals show <decision_id>
lacctl approvals approve <decision_id>
lacctl approvals reject <decision_id>
```

`permissions set` replaces the complete canonical standing-policy snapshot using a UTF-8 JSON file containing exactly:

```json
{"rules": [], "defaults": []}
```

Rule/default objects must be canonical P003 `lac.standing-policy-rule/v1` and `lac.standing-policy-default/v1` material. P004 performs authoritative validation and revisioned mutation.

## Authority semantics preserved

- Skill registration remains descriptive and grants zero authority. P005 intentionally does not add a `skills register` CLI command beyond the task-authorized command set.
- Pending permission administration never resumes the P002-denied effect. A fresh effect request is required after any future policy/capability change.
- Standing permission mutation remains P003 deterministic policy with `DENY > REQUIRE_APPROVAL > ALLOW` at equal specificity.
- Exact approval commands create only the existing immutable one-request approval decision. They do not dispatch or execute an effect; current policy is still re-evaluated before dispatch.
- Runtime consumers gain no administration mutation surface from `lacctl`.
