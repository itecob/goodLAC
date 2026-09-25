# NEXT SESSION PROMPT — goodLAC / POST-V1 R2 PROJECT-ROOT SESSION WORKSPACE

## 1. Role and controlling rule

You are the next Lead Implementation Engineer for owner-authorized post-v1 remediation of **goodLAC** (repository historically named Local Agent Controller / LAC).

`MODE=IMPLEMENTATION_SEGMENT`
`SESSION_SEGMENT=POSTV1-R2-PROJECT-ROOT-SESSION-WORKSPACE`
`REPOSITORY=itecob/goodLAC`
`PUBLIC_REPOSITORY_TRANSITION_CLOSEOUT=ce20f345a7de5342b33267387d436739af82e6e1`
`NO_OPERATIVE_PROJECT_LICENSE=true`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Web-File-Tool. The authorized local root label may remain `Local Agent Controller`; that label is not the public product name. Any mutation must be delivered as one owner-executable package and one self-contained Bash command.

## 2. Mandatory durable reads

Read first, in order:

1. `PROJECT_STATE.json`
2. `tasks/ACTIVE_TASK.md`
3. `README.md`
4. `BRAND.md`
5. `SECURITY.md`
6. `LICENSE-DRAFT.md`
7. `CLA-DRAFT.md`
8. `docs/ARCHITECTURE.md`
9. `UPSTREAM_LOCK.json`
10. `docs/POST_V1_REMEDIATION_ROADMAP.md`
11. `qualification/evidence/post_v1_r1_owner_permission_decision_owner_execution.json`
12. `qualification/evidence/goodlac_public_transition_closeout.json`

Then inspect only the source/tests needed for R2.

## 3. Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS`
- `PREDECESSOR_GIT_COMMIT=5c598120a182ed88d235cffec326532c90f564c4`
- `HANDOFF_BASE_GIT_COMMIT=5c598120a182ed88d235cffec326532c90f564c4`
- `ACCEPTED_HISTORICAL_RELEASE=1.0.0-rc.11`
- `TARGET_RELEASE_TRAIN=1.0.0-rc.12`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/post_v1_r1_owner_permission_decision_owner_execution.json`
- `EXPECTED_NEXT_TASK=POSTV1-R2-PROJECT-ROOT-SESSION-WORKSPACE`
- `SESSION_SEGMENT=POSTV1-R2-PROJECT-ROOT-SESSION-WORKSPACE`
- `PUBLICATION_COMMIT=b1b70454aa4576c4463c934fdada3d51024c6c98`
- `PUBLIC_REPOSITORY_TRANSITION_CLOSEOUT=ce20f345a7de5342b33267387d436739af82e6e1`

The live HEAD should be exactly one workflow/evidence/state transition commit after `5c598120a182ed88d235cffec326532c90f564c4`. Verify that parent/HEAD delta before relying on this handoff. Any unexpected material delta is a blocker.

## 4. Historical and repository-governance boundary

The rc.11 Phase 7 independent review remains accepted historical evidence. Do not reopen or rewrite it. R1-R6 are a new owner-authorized post-v1 roadmap created from real product-use findings.

`GOODLAC-PUBLIC-001` was completed before this roadmap started. It changed public identity/governance documentation only and did not change authority/runtime implementation. Preserve the repository identity `itecob/goodLAC`, its publication/closeout evidence, the goodLAC capitalization rules, and the compatibility-namespace freeze. Do not create an operative `LICENSE`, activate `LICENSE-DRAFT.md`, activate `CLA-DRAFT.md`, change repository visibility, or alter commercial/security contact claims as part of R2.

## 5. R1 facts to preserve

R1 added an owner-only bounded permission-decision contract. `permissions.decide` is on the isolated admin surface only; the model-facing runtime did not gain a permission tool. Scope is derived from controller-known durable pending/request metadata. `ALLOW_ONCE` and `ASK_EVERY_TIME` establish `REQUIRE_APPROVAL`; the former is intended for host orchestration to approve only the resulting fresh exact canonical request. `DENY_ONCE` closes exactly one continuation non-authoritatively and does not mutate standing policy or the aggregated pending resolution.

Do not expose these admin operations to the governed Pi sandbox.

## 6. R2 binding requirements

Normal installed behavior must become:

```bash
cd /their/project
pi
```

The canonical launch CWD should become the immutable governed project root for that session by default. Do not mutate persistent global workspace configuration merely because Pi was launched elsewhere. Determine and document safe precedence for explicit launch override, any retained fixed-workspace mode, then launch CWD.

The selected root must be canonical, existing, a directory, controller/host-selected before model effects, immutable for the session, and the sole project mount at `/workspace`. Preserve no-parent-traversal, no-symlink-escape, no host-filesystem exposure, and disabled project-local Pi extensions/skills/prompts/themes/context/session resources. Dangerous bypass remains only the accepted explicit dangerous flag.

Most importantly, make project identity participate in trusted permission scope before R3. A standing `Always allow` chosen in Project A must not silently authorize Project B. Do not derive project identity from arbitrary model strings. Reuse or extend the capability/resource contract deterministically and document migration/compatibility effects.

## 7. Required R2 adversarial coverage

At minimum prove:

- launch CWD is canonical session workspace by default;
- two sessions launched from different projects remain isolated;
- model output cannot replace project identity/root;
- Project A standing permission cannot authorize Project B under the displayed scope;
- `../`, absolute path tricks and symlink escapes still fail;
- project-local extension/resource discovery remains disabled;
- admin socket and host filesystem remain unavailable in the sandbox;
- existing R1 permission decisions continue to function with project-aware scope;
- emergency pause, exact approval re-evaluation, one-shot continuation, idempotency and duplicate prevention remain intact;
- explicit dangerous bypass remains unchanged and ungoverned only by the accepted flag.

## 8. Stop gate

Complete only R2 in this segment. Do not implement R3 TUI owner dialogs until R2 is owner-qualified and the project-aware scope contract is durable.

Leave a precise successor prompt and recoverable owner package state.
