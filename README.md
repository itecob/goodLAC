# Local Agent Controller (LAC)

LAC is a deterministic, local-first authority and effect-control plane for AI agents.

## Controlling rule

The AI may propose an action. Deterministic software decides whether that action is authorized and whether it may become an effect.

## Current status

Phase 0 only: upstream qualification and adoption lock. No controller runtime, model integration, host-effect adapter, service, production credential, or future-phase feature is installed by this bootstrap.

The Phase 0 package pins upstream revisions, verifies checked-out licenses, performs code-level probes, runs targeted Airlock tests, records the Airlock disposition, and prepares one candidate for one fresh independent phase-boundary review.

## Mandatory session reads

Every development session starts with exactly:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`

Read other files only as the active task requires.

## Repository history

Git is the implementation audit trail. `PROJECT_STATE.json` is current durable project truth. Do not create per-conversation checkpoint directory chains.

## Controlling specification

The owner-provided planning baseline is preserved at `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`. It is controlling. The concise operating files do not supersede it.
