# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / DURABLE CONTINUATION LAUNCHER

## Purpose

Continue the Local Agent Controller project from live durable state without reconstructing progress from conversation memory, without stopping after a single verification/status action, and without creating unnecessary review loops.

Use the connected read-only Tunnel/Web-File-Tool.

Project root label:

`Local Agent Controller`

## Mandatory first reads

Read exactly these project files first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`

Then read:

5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Read the controlling specification and only the additional files needed for the active task.

Durable project state and Git are authoritative. Do not infer completion from earlier chats.

## Handoff fields

Unless the owner supplies more specific predecessor facts with this prompt, use:

- `PREDECESSOR_ROLE=NONE`
- `PREDECESSOR_RESULT=NONE`
- `PREDECESSOR_GIT_COMMIT=NONE`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=NONE`
- `EXPECTED_NEXT_TASK=AUTO_FROM_DURABLE_STATE`

If the owner pastes a fresh independent review result or owner-execution output along with this prompt, preserve those exact facts and apply the template's rules for that handoff. Do not repeat a valid phase-boundary review merely because the repository could not be mutated by the read-only reviewer or because a later commit changed only review-preserving workflow/handoff files. Verify the exact Git delta first; any material candidate change invalidates review preservation.

## Required behavior

Follow `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` as the session operating protocol.

In particular:

1. establish current project position;
2. objectively verify the predecessor's material work in a bounded way;
3. determine whether this is ordinary implementation continuation or the one required phase-boundary independent review;
4. **continue into the next authorized work in the same session** whenever no real external gate prevents it;
5. use deterministic tests during implementation;
6. reserve formal independent review for phase boundaries;
7. if owner mutation is needed, create one meaningful package and one self-contained Bash command;
8. after owner output is returned, verify the live installed state through the Tunnel and continue if possible;
9. before any legitimate stop, provide the exact next action and the complete successor prompt required for the next fresh session.

Do not end after only reporting what has been done or what should happen next when you can perform the next authorized work now.
