# ACTIVE TASK — LAC-B001

## Objective

Implement the first Phase 4 typed Gmail effect adapter without changing the Phase 1 authority core, Phase 2 sandbox boundary, or accepted Phase 3 Pi/FreeToken integration.

## In scope

- Typed Gmail operations defined by the controlling specification: `email.search`, `email.read`, `email.draft`, `email.send`, `email.archive`, and `email.delete`.
- Preserve the initial policy semantics: search/read/draft `ALLOW`; send/archive `REQUIRE_APPROVAL`; delete `DENY`.
- Bind `email.send` approval to the exact security-relevant operation, including account, to, cc, bcc, subject, body hash, and attachment hashes. Any security-relevant mutation invalidates approval.
- Route consequential Gmail effects through the existing canonical `EffectRequest -> policy -> approval where required -> pre-dispatch recheck -> execution lease -> Dispatcher -> Gmail EffectAdapter -> durable receipt/audit` path.
- Use credential references resolved controller-side. Gmail/OAuth/service credentials must not enter model/Pi context, generic shell environment, logs, receipts, or tool results.
- Implement deterministic idempotency/duplicate prevention so an approved send cannot be duplicated by retry.
- Add deterministic unit/contract/integration tests using synthetic fixtures or a bounded fake/local provider by default. A real Gmail mutation requires a dedicated test account or separate explicit user authority.
- Preserve all existing Phase 1, H001-H004, A001-A003 regressions.

## Out of scope

- Calendar adapter (`LAC-B002`).
- Chief of Staff end-to-end pilot (`LAC-B003`).
- OpenClaw, Omarchy Agent OS, compatibility-gateway expansion, UI/productization, or unrelated architecture changes.
- Production-account mutation or use of real credentials without explicit bounded authority.

## Required inputs

- `PROJECT_STATE.json`
- `docs/ARCHITECTURE.md`
- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, especially §§18, 22, 34, 38, and 49
- `docs/CONTRACTS.md`
- `docs/THREAT_MODEL.md`
- existing Dispatcher/effect receipt/idempotency/approval implementations and tests
- accepted Phase 3 review facts in the live `NEXT_SESSION_PROMPT.md`

## Required outputs

- Gmail typed effect contract/adapter in the established package structure.
- Deterministic tests for read/search/draft/send/archive/delete semantics and credential isolation.
- Send approval exact-binding and exactly-once evidence.
- Full applicable regression gate.
- One owner-executable package and one Bash command that install the completed B001 segment and hand off to `LAC-B002`.

## Acceptance tests

At minimum prove deterministically:

1. `email.search`, `email.read`, and `email.draft` succeed only through the typed governed path.
2. `email.send` cannot execute without an exact qualifying approval.
3. after approval, exact unchanged `email.send` succeeds exactly once and records a durable receipt.
4. mutation of recipient, cc/bcc, subject, body, attachment, account, principal, agent, or other bound security material invalidates the approval before dispatch.
5. duplicate/retry cannot send twice.
6. `email.archive` follows its configured approval policy.
7. `email.delete` is denied and cannot produce the external deletion effect.
8. Gmail credentials are absent from agent/model context, generic shell environment, logs, receipts, and tool results.
9. unknown Gmail action/resource/state fails closed.
10. Phase 1, H001-H004, A001, A002, and A003 regressions remain green.
11. no B002/B003 or unrelated Phase 4+ implementation is introduced.

## Package required?

Yes.

## Next task on success

`LAC-B002` — Calendar adapter, in a fresh implementation session.
