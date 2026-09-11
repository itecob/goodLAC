# Local Agent Controller (LAC)

LAC is a deterministic, local-first authority and effect-control plane for AI agents.

## Controlling rule

The AI may propose an action. Deterministic software decides whether that action is authorized and whether it may become an effect.

## Current status

Phase 1 (`PHASE_1_CONTROLLER_WALKING_SKELETON`) is in progress.

Completed Phase 1 tasks:

- `LAC-C001`: durable SQLite/WAL `StateStore` foundation.
- `LAC-C002`: canonical versioned effect request and durable request persistence.
- `LAC-C003`: deterministic `PolicyDecisionProvider`, `DENY > REQUIRE_APPROVAL > ALLOW` precedence, fail-closed unknown/no-match behavior, request/hash-bound policy decisions, and durable decision persistence.

The active task is `LAC-C004`, durable approval state.

No approval execution, lease, dispatcher, simulated/real effect, emergency pause, sandbox, model/harness integration, production credential, or consequential external effect is introduced through C003.

## Mandatory session reads

Every development session starts with exactly:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`

Then read `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` and only the additional files needed for the active task.

## Repository history

Git is the implementation audit trail. `PROJECT_STATE.json` is current durable project truth. Do not create per-conversation checkpoint directory chains.

## Controlling specification

The owner-provided planning baseline is preserved at `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`. It is controlling.
