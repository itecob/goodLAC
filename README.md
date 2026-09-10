# Local Agent Controller (LAC)

LAC is a deterministic, local-first authority and effect-control plane for AI agents.

## Controlling rule

The AI may propose an action. Deterministic software decides whether that action is authorized and whether it may become an effect.

## Current status

Phase 0 upstream qualification received its fresh independent review PASS at
`41dd4173ce62b311a1ab6fdde107937237940c2d`. The review was preserved across
the verified workflow-only delta through
`3ca7febb9699910fb26b91b5dd290637e332524d`.

Phase 1 (`PHASE_1_CONTROLLER_WALKING_SKELETON`) is in progress. `LAC-C001`
established the durable SQLite/WAL `StateStore` foundation with migration
integrity and deterministic restart/transaction tests. The active task is
`LAC-C002`, canonical effect request.

No model integration, host-effect adapter, sandbox, production credential,
or consequential external effect is introduced by C001.

## Mandatory session reads

Every development session starts with exactly:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`

Then read `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` and only the additional
files needed for the active task.

## Repository history

Git is the implementation audit trail. `PROJECT_STATE.json` is current durable
project truth. Do not create per-conversation checkpoint directory chains.

## Controlling specification

The owner-provided planning baseline is preserved at
`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`. It is
controlling. The concise operating files do not supersede it.
