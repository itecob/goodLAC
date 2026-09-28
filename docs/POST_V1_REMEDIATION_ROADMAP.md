# goodLAC Post-v1 Remediation / Productization Roadmap

## Authority and historical boundary

This roadmap is a new owner-authorized body of work discovered through real product usage after the accepted `1.0.0-rc.11` Phase 7 review. It does not reopen or rewrite the closed prior roadmap, its accepted evidence, or its acceptance criteria.

Accepted baseline remains:

- accepted release: `1.0.0-rc.11`;
- Phase 7 independent review: `PASS`;
- historical roadmap: `CLOSED`.

Repository/governance state at roadmap start is also preserved:

- `GOODLAC-PUBLIC-001`: `COMPLETE`;
- publication commit: `b1b70454aa4576c4463c934fdada3d51024c6c98`;
- closeout/start commit for this roadmap: `ce20f345a7de5342b33267387d436739af82e6e1`;
- repository identity: `itecob/goodLAC`;
- the public transition changed no authority/runtime implementation and created no new security qualification;
- `LICENSE-DRAFT.md` and `CLA-DRAFT.md` remain drafts; no operative project `LICENSE` is activated by this roadmap.

This roadmap must not erase, roll back, or rewrite the completed public-repository transition while changing the current active-task state for newly authorized technical work.

The target release train for this bounded remediation is `1.0.0-rc.12`. That target is not accepted or published merely because an implementation segment completes; acceptance requires integrated owner UAT and a fresh independent security/product review.

## Governing invariant

**AI proposes. Deterministic software determines authorization and effects.**

No segment may give the model permission-management authority, policy mutation authority, exact-approval authority, access to the owner administrator socket, arbitrary host filesystem access, an alternate consequential-effect path, or any ability to answer an owner decision gate through model output.

## Dependency order

R1 is deliberately resource-selector scoped rather than hard-coding the current logical word `workspace` as a global permission boundary. R2 will make the canonical session resource/project identity project-aware before the R3 TUI presents `Always` choices. This keeps R1 compatible with the narrow project scope required by the product without allowing Project A policy to silently authorize Project B.

### R1 — Owner permission-decision contract

Status: `COMPLETE` — owner package execution and retained regression gate PASS.

Define deterministic owner choices over a blocked first-use continuation and canonical pending permission record. The operation accepts only an exact continuation identity, exact pending identity, an enumerated choice, and an enumerated scope. It derives action/resource/application/skill/principal/agent scope from controller-known durable state rather than owner- or model-supplied strings.

Binding semantics:

- `ALLOW_ONCE` -> standing `REQUIRE_APPROVAL`; resolve pending configuration; resume one fresh continuation request; create an exact one-time approval only for that fresh canonical request; future matches remain `REQUIRE_APPROVAL`.
- `ALWAYS_ALLOW` -> standing `ALLOW`; resolve; fresh continuation passes normal policy/dispatch checks.
- `ASK_EVERY_TIME` -> standing `REQUIRE_APPROVAL`; resolve; current and future requests need exact owner approval.
- `DENY_ONCE` -> close only the exact workflow continuation non-authoritatively; do not mutate standing policy and do not use the aggregated pending resolution as a per-request denial.
- `ALWAYS_DENY` -> standing `DENY`; resolve; current fresh request is denied and future matching requests fail without recurring first-use discovery.

The original first-use effect remains terminally denied in every case. Policy changes never revive it.

### R2 — Project-root / session workspace

Status: `COMPLETE` — owner package qualification and retained regression PASS at implementation commit `97c93d6386d689216cf166c1ba81d3ef4ee7011a`.

Make ordinary installed governed Pi bind the canonical launch CWD as an immutable session project root by default, while retaining an explicit fixed-workspace mode where justified. Introduce controller-known project identity into the trusted resource/policy scope so Project A standing permission does not silently authorize Project B. Preserve path/symlink containment and disabled project-local Pi resources.

### R3 — Pi TUI owner permission gate

Status: `COMPLETE` — owner package qualification and retained regression PASS at implementation commit `971148ca33083d4a8015d8c2692e8f49303582b2`.

Feasibility was verified before R1 implementation against the exact accepted Pi pin `da840b6216578c2a571d0374ac6a2091a83f9d91` / Pi 0.85.1: `ExtensionUIContext` exposes blocking owner-facing `select()` and `confirm()` dialogs. Use those exact pinned APIs to render the permission gate from the explicit goodLAC extension. The trusted extension is therefore part of the owner-input capture TCB; do not claim the TUI is outside the authorization boundary. Canonical policy/approval truth remains in goodLAC. Add bounded opaque challenges with exact session/continuation/pending binding, expiry, one-use consumption, fail-closed cancellation/disconnect/restart behavior, and no model-facing permission tool. The general owner admin socket must remain outside the sandbox.

### R4 — Installed terminal fallback and UX cleanup

Status: `COMPLETE` — retained regression PASS at implementation commit `6838dbf80c4d9a2572194891d3b355f39a6efbce`.

Provide a concise installed owner command surface for the same bounded choices. Preserve low-level `lacctl permissions set --file` only as an administrator/scripting primitive. Correct ordinary documentation from repository-relative commands to installed commands.

### R5 — Integrated owner UAT and release qualification

Run real owner UAT from at least two ordinary project directories and exercise Allow once, Always allow, Ask every time, Deny once, Always deny, overwrite/replace, restart/recovery, scope display, and exact project isolation. Record bounded owner evidence and produce the `1.0.0-rc.12` review candidate only after integrated qualification passes.

### R5-R001 — Multi-Pi administrator control-plane blocker remediation

Status: `ACTIVE` — discovered during R5 owner UAT before the first permission choice.

R5 reached the installed governed Pi path only after retained regression, candidate build/install,
doctor/pin checks, and external FreeToken readiness passed. The first Pi launch then failed because
the R5 harness had orphaned an owner `lac-admin-server` on the candidate runtime socket: `admin_start`
was invoked inside Bash command substitution, so its `ADMIN_PID` assignment was lost to the parent
shell. This is an R5 harness lifecycle defect.

The incident also exposed a product-level concurrency limitation: each native governed Pi host
currently starts its own `pi_v1_admin_server.py`, and that server competes for the same fixed
owner-only `admin-v1.sock`. goodLAC must support multiple simultaneous governed Pi sessions on one
machine/server against one canonical controller truth, subject to actual host/model-runtime
capacity.

R5-R001 must separate machine/controller-scoped administrator ownership from Pi-session lifecycle
(or implement an equivalently secure multiplexed design), preserve all Phase 7 socket-race
protections and R1-R4 authority invariants, add deterministic multi-session isolation/emergency/
lifecycle coverage, repair the R5 orphan-process bug, and add an installed concurrent-Pi owner-UAT
scenario.

R5 remains `BLOCKED` until this remediation passes and a fresh integrated owner UAT is rerun.
`1.0.0-rc.12` is not accepted.

### R6 — Fresh independent security/product review

A fresh reviewer, not the implementation agent, reviews the exact R5 candidate. Final disposition is `PASS` or `BLOCKED`. The prior rc.11 PASS remains historical baseline either way.
