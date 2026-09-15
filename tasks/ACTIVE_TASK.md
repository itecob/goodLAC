# ACTIVE TASK — LAC-A004

## Objective

Implement a thin interactive terminal harness that lets the owner use and evaluate the already-accepted Phase 3 stack — sandboxed Pi, the pinned FreeToken/model runtime, and the governed LAC filesystem/shell surface — before any Chief of Staff Gmail or Calendar capability is added.

## In scope

- Add one user-facing local terminal entrypoint for multi-turn interaction with the accepted Phase 3 governed agent path.
- Reuse the accepted A003 architecture and exact pins; do not create a second authority path.
- Start or connect to the exact pinned FreeToken runtime/model on loopback using a reproducible launcher that discovers and validates the local CUDA toolkit, including when `CUDA_HOME` was initially unset.
- Keep the Pi process inside the accepted H001 Bubblewrap boundary with the same exact governed tool surface: `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
- Use a dedicated bounded owner-test workspace. The Pi process must not receive ambient access to the repository, home directory, controller database, credentials, or arbitrary network.
- Show the owner concise observable tool/effect information: requested governed tool, policy/dispatch outcome, and durable receipt identity/outcome. Do not expose hidden model reasoning.
- Provide simple terminal session controls sufficient for usability testing (at minimum help/status/quit, whether implemented as slash commands or an equivalent small interface).
- Provide an owner user-testing guide that exercises normal conversation, governed read/create/replace/shell work, receipts, denied/out-of-bound requests, restart/shutdown behavior, and qualitative observations.
- Preserve all Phase 1, H001-H004, A001-A003 tests and security invariants.

## Out of scope

- Gmail, Calendar, Chief of Staff behavior or prompts, B001/B002/B003 implementation.
- New authority semantics, new effect types, new sandbox design, new credential system, new model orchestration, memory architecture, web UI, voice UI, or productization.
- Production credentials, production accounts, arbitrary host access, or weakening the accepted Phase 3 boundary for convenience.
- Replacing Pi, FreeToken, the accepted local model, Bubblewrap, or the authority core.

## Required inputs

- `PROJECT_STATE.json`
- `docs/ARCHITECTURE.md`
- `UPSTREAM_LOCK.json`
- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, especially §§17, 19, 20, 33, 38, 49, 50, 54, and 59
- `docs/PHASE3_A003_QUALIFICATION.md`
- `docs/MODEL_PROVIDER_CONTRACT.md`
- accepted A003 sandbox/model/provider/controller bridge implementation and evidence
- `qualification/evidence/a003_runtime.json`
- `qualification/evidence/a003_owner_execution.json`

## Required outputs

- Interactive local terminal harness using the accepted governed Pi path.
- Reproducible FreeToken/model launcher with CUDA-toolkit discovery/validation and loopback-only serving.
- Dedicated bounded baseline-test workspace and safe lifecycle/cleanup behavior.
- Deterministic tests proving the interactive harness does not add an ambient-authority or direct-effect bypass.
- Owner baseline user-testing guide with concrete prompts/tasks and expected controller observations.
- One owner-executable installation package and one Bash command.
- Successful package must advance durable state to `LAC-A004-UAT`, not to B001, so the owner performs hands-on validation before Chief of Staff development resumes.

## Acceptance tests

At minimum prove deterministically:

1. the launcher succeeds on the current qualified host when `CUDA_HOME` begins unset by resolving and validating the installed CUDA toolkit rather than assuming an interactive-shell environment;
2. the exact pinned FreeToken commit, model revision, served model id, Pi commit, and Bubblewrap backend are used;
3. an owner can conduct a multi-turn terminal conversation through sandboxed Pi and the LAC ModelProvider path;
4. Pi sees exactly the four accepted governed tools and no direct host filesystem/shell/network/credential route;
5. governed workspace read/create/replace and allowed shell inspection execute only through the existing Dispatcher/adapters and create durable receipts;
6. attempts to operate outside the bounded workspace fail and do not produce the prohibited host effect;
7. inherited service/synthetic credentials remain absent from the agent/model/tool surfaces;
8. arbitrary agent network access and arbitrary host-process execution remain unavailable;
9. startup failure and shutdown are clean: no false-ready state, orphaned FreeToken/Pi child, or false successful receipt;
10. A001, A002, A003 and applicable Phase 1/H001-H004 regression gates remain green;
11. no Gmail/Calendar/COS implementation or new authority semantics are introduced;
12. the owner-test guide can be executed without editing project source or manually assembling infrastructure commands.

## Package required?

Yes.

## Next task on success

`LAC-A004-UAT` — owner hands-on baseline user validation. `LAC-B001` remains deferred until that validation is explicitly accepted.
