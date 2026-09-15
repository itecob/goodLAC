# Capability Manifest v1

**Schema:** `lac.capability-manifest/v1`
**Manifest version:** `1`
**Authority semantics:** descriptive only; registration grants zero authority.

P001 defines the canonical capability/skill declaration consumed by the Local Agent Controller. A manifest says what an application/skill is structurally capable of requesting. It does **not** create policy, approval, credentials, an execution lease, or permission to perform any effect.

## Canonical shape

```json
{
  "schema": "lac.capability-manifest/v1",
  "manifest_version": 1,
  "application_id": "example-app",
  "skill_id": "example-skill",
  "actions": [
    {
      "action": "document.read",
      "resource": {
        "type": "document.local",
        "selectors": ["document:workspace"]
      },
      "arguments": {
        "type": "object",
        "properties": {
          "document_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          }
        },
        "required": ["document_id"],
        "additionalProperties": false
      },
      "security_properties": ["read_only"]
    }
  ],
  "display": {
    "name": "Example skill",
    "description": "Optional non-authority metadata"
  }
}
```

Top-level and nested objects are closed contracts: unknown fields fail validation. Raw JSON with duplicate object keys fails validation. `application_id`, `skill_id`, action IDs, resource types, and selectors use bounded canonical identifiers. Action identities and resource selectors may not be duplicated. Resource selectors are exact bounded selectors in v1; wildcard/glob selectors are rejected as ambiguous.

## Bounded argument-schema subset

Every action declares an `arguments` schema whose root type is `object`. Objects must enumerate `properties`, enumerate `required`, and set `additionalProperties` to `false`. Nested schemas support only these deterministic bounded forms:

- `object`: `type`, `properties`, `required`, `additionalProperties=false`;
- `array`: `type`, `items`, `maxItems`, optional `minItems`;
- `string`: `type`, `maxLength`, optional `minLength`, optional bounded `enum`;
- `integer` / `number`: `type`, `minimum`, `maximum`, optional bounded `enum`;
- `boolean`: `type`, optional bounded `enum`;
- `null`: `type` only.

Schema depth, node count, property count, string length bounds, array item bounds, action count, and selector count are controller-bounded. Keywords such as `default`, `examples`, `$ref`, `pattern`, `oneOf`, arbitrary extension fields, or model-authored annotations are not accepted in v1. This keeps material request shape deterministic and policy-addressable.

## Security-property vocabulary

Only these v1 properties are accepted:

`read_only`, `local_mutation`, `external_mutation`, `destructive`, `external_communication`, `credential_sensitive`, `security_sensitive`, `permission_change`, `network_egress`, `privilege_change`.

They are trusted controller/manifest metadata. A model cannot create, alter, or reinterpret them at runtime.

## Canonical hashes and revisions

A manifest has two SHA-256 identities:

- `canonical_hash` covers the full normalized manifest, including optional display metadata;
- `security_hash` covers only authority-relevant material and excludes display metadata.

The registry persists immutable revisions. Re-registering byte-equivalent canonical material is idempotent. Any changed canonical manifest creates a new revision. A security-relevant change necessarily changes `security_hash`; a display-only change may create a new revision while preserving the same `security_hash`. Earlier revisions are never silently mutated.

P001 stores revisions, latest pointers, and bounded audit metadata atomically in the existing SQLite `system_state` transaction boundary. It deliberately introduces no new runtime mutation surface and no new authority state. The authenticated external administration transport is P004 scope.
