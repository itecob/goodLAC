# P006-UAT First-Use Permission Discovery Qualification

**Task:** `LAC-P006-UAT`
**Purpose:** Close the owner-required first-use discoverability gap without adding runtime authority.

## Binding behavior

For a request that is valid against a registered capability but has no applicable owner-configured standing rule/default:

```text
validate registered capability/resource/material
→ standing policy returns DENY because no configured permission applies
→ persist DENY decision + bounded owner-review item atomically
→ no execution lease
→ no adapter invocation
→ exact original request remains closed
→ owner configures future permission through P004/P005
→ only a fresh request is evaluated under current policy
```

The review item uses the existing bounded, deterministic, credential-safe pending-permission queue and records reason `NO_CONFIGURED_STANDING_PERMISSION`.

A matching configured `DENY` rule or configured default is already an owner decision and does not create permission-discovery work.

## Deterministic proof

`tests/acceptance/test_p006_first_use_permission_discovery.py` proves:

- known/valid + no policy is `DENY`;
- no lease or adapter effect occurs;
- owner-review work is created and equivalent requests aggregate;
- raw argument values are not copied into review metadata;
- later owner configuration cannot revive the exact denied request;
- a fresh request can use newly configured policy;
- explicit rule-level `DENY` creates no discovery item;
- explicit default `DENY` creates no discovery item.

The owner walkthrough additionally proves this through the P004/P005 admin path, and the owner-visible adversarial stress matrix plus the accepted deterministic P006 regression remain mandatory before B002 activation.
