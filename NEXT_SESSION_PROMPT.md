# NEXT SESSION PROMPT — goodLAC / POST-V1 R3 PI TUI OWNER PERMISSION GATE

## 1. Role and controlling rule

You are the next Lead Implementation Engineer for owner-authorized post-v1 remediation of **goodLAC**.

`MODE=IMPLEMENTATION_SEGMENT`
`SESSION_SEGMENT=POSTV1-R3-PI-TUI-OWNER-PERMISSION-GATE`
`REPOSITORY=itecob/goodLAC`
`R2_IMPLEMENTATION_COMMIT=97c93d6386d689216cf166c1ba81d3ef4ee7011a`
`ACCEPTED_HISTORICAL_RELEASE=1.0.0-rc.11`
`TARGET_RELEASE_TRAIN=1.0.0-rc.12`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Web-File-Tool. Any mutation must be delivered as one owner-executable package and one self-contained Bash command.

## 2. Mandatory durable reads

Read first, in order: `PROJECT_STATE.json`, `tasks/ACTIVE_TASK.md`, `README.md`, `BRAND.md`, `SECURITY.md`, `LICENSE-DRAFT.md`, `CLA-DRAFT.md`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `docs/POST_V1_REMEDIATION_ROADMAP.md`, the R1 owner execution evidence, and the R2 owner execution evidence if present. Then inspect only source/tests needed for R3.

## 3. R2 facts to preserve

Ordinary governed Pi now binds exactly one canonical existing project root per session. Workspace precedence is explicit governed `--workspace`, then `workspace_mode=fixed`, then launch CWD; launch-CWD selection does not rewrite config. The project is mounted read-only at `/workspace` inside native Pi while project-local extensions, skills, prompts, themes, context and session resources remain disabled. Project identity is controller-derived from canonical path plus filesystem device/inode and encoded into a project-specific Pi application identity. R1 permission decisions therefore scope to the current project; Project A `Always allow` cannot match Project B. Continuation list/status/resume is project-filtered and cross-project resume fails closed. Dangerous bypass remains only the explicit accepted flag.

## 4. R3 binding requirements

Use the exact pinned Pi 0.85.1 ExtensionUIContext blocking owner-facing dialog APIs already identified by the roadmap. The trusted goodLAC extension is part of the owner-input capture TCB, but canonical policy/approval truth remains in goodLAC. Present the R1 bounded choices: Allow once, Always allow, Ask every time, Deny once, Always deny. Display the trusted project scope derived by the host/controller; do not accept project identity from model text or arbitrary extension payload.

The TUI must not gain the general administrator socket. Introduce only a bounded permission-decision channel/challenge necessary for the active blocked continuation. Bind it exactly to session/project/continuation/pending identity, expire it, consume once, and fail closed on cancellation, disconnect, stale state or restart. Owner choice must route to the accepted R1 `permissions.decide` semantics. `ALLOW_ONCE` may approve only the resulting fresh exact request; approval creation itself never dispatches. Emergency pause, deny precedence and policy re-evaluation remain authoritative.

## 5. Stop gate

Complete only R3. Do not begin R4 terminal-fallback cleanup until the TUI decision path is qualified. Leave a precise successor prompt and recoverable owner package state.
