# ACTIVE TASK — LAC-P001

## Task ID

`LAC-P001`

## Objective

Implement the first permission-management segment: a durable, deterministic capability/skill registry and canonical manifest contract that lets LAC know what an external application or skill may request without granting any authority merely because the capability is registered.

## In scope

- Define a versioned canonical capability manifest schema for applications/skills, including stable application/skill identity, manifest version, declared actions, resource types/selectors, bounded argument schemas, and deterministic security-property classifications.
- Implement a durable local registry/repository for canonical manifests using the existing local state-store architecture and migration discipline.
- Enforce strict manifest validation and fail closed on unknown fields, malformed schemas, duplicate identities/actions, unsupported security-property names, ambiguous resource declarations, or non-canonical persisted records.
- Preserve the distinction: capability registration describes possible requests; it never creates an `ALLOW`, `REQUIRE_APPROVAL`, approval, execution lease, credential capability, or effect authority.
- Keep registry mutation internal/admin-side only in P001. Do not expose a runtime/agent tool that can register or modify capabilities.
- Establish the initial deterministic security-property vocabulary needed by later conditional policy, such as `read_only`, `local_mutation`, `external_mutation`, `destructive`, `external_communication`, `credential_sensitive`, `security_sensitive`, `permission_change`, `network_egress`, and `privilege_change`. Properties are controller/manifest metadata, never model judgments.
- Add deterministic unit/integration/negative-security tests for the registry and persistence contract.
- Run the applicable accepted regression gate including B001.

## Out of scope

- Pending-permission queue/quarantine behavior (`LAC-P002`).
- Scoped/conditional user-policy evaluation (`LAC-P003`).
- Secure external admin API/socket (`LAC-P004`).
- `lacctl` permissions UI (`LAC-P005`).
- Permission-management E2E (`LAC-P006`).
- Calendar adapter (`LAC-B002`) or generic external-consumer proof (`LAC-B003`).
- Chief of Staff implementation or workflow/business logic.
- Web UI/TUI, enterprise RBAC, autonomous policy generation, or model-authored policy changes.

## Required inputs

- `docs/PERMISSION_MANAGEMENT.md`.
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`.
- `docs/ARCHITECTURE.md` and `docs/CONTRACTS.md`.
- Existing SQLite state-store/repository patterns and migrations.
- Existing policy/effect request interfaces only as needed to prove registration grants zero authority.

## Required outputs

- Versioned capability/skill manifest domain model and strict canonical validation.
- Durable capability registry/repository and any required bounded migration.
- Deterministic tests proving persistence, validation, canonical round-trip, fail-closed behavior, and zero authority from registration alone.
- Applicable accepted regression evidence including B001.
- One owner-executable package completing P001 and activating fresh `LAC-P002` on success.

## Acceptance tests

At minimum prove deterministically that:

1. a canonical manifest can register an application/skill identity, version, actions, resource types, argument schemas, and security properties and survive controller restart;
2. unknown fields/property names, malformed argument schemas, duplicate actions/identities, non-canonical records, and unsupported manifest versions fail closed;
3. changing security-relevant manifest material produces a distinct canonical identity/revision and cannot silently mutate a previously accepted record;
4. merely registering a capability does not create an `ALLOW`, `REQUIRE_APPROVAL`, approval, credential access, lease, or external effect;
5. no runtime/agent-facing interface in P001 can register or modify capability manifests;
6. registry/audit/state records contain no raw service credentials;
7. applicable Phase 1–3/A004/B001 regressions remain passing.

## Package required?

Yes.

## Next task on success

`LAC-P002` in a fresh implementation session.
