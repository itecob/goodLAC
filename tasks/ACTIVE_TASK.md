# ACTIVE TASK — LAC-B002

## Task ID

`LAC-B002`

## Objective

Implement the generic Google Calendar typed-effect adapter against the completed P001-P006 permission-management plane. Calendar is a reusable LAC service adapter; it is not Chief of Staff workflow code.

## In scope

- Implement typed Calendar operations: `calendar.search`, `calendar.read`, `calendar.propose`, `calendar.create`, `calendar.modify`, `calendar.cancel`, and recognized `calendar.delete`.
- Define/register the bounded Calendar capability manifest material required by P001/P002 and exercise Calendar requests through `Dispatcher.dispatch_capability` with validated capability context.
- Preserve deterministic standing-policy behavior through P003. Qualification fixtures must demonstrate search/read/propose on an `ALLOW` path, create/modify/cancel on `REQUIRE_APPROVAL`, and delete on `DENY`.
- Bind all security-relevant create/modify/cancel fields into the canonical request: calendar, title, start, end, timezone, attendees, location, recurrence, and conference settings. Any mutation must invalidate exact approval.
- Keep credentials outside agent/model/request/receipt/audit material. Resolve any Calendar credential reference only inside the bounded adapter/transport invocation path.
- Provide deterministic synthetic/local transport fixtures for unit/integration tests. Do not use production credentials, production calendars, or external consequential effects.
- Make mutation execution idempotent where supported and otherwise rely on controller duplicate prevention; reconciliation must never blindly repeat an ambiguous mutation.
- Keep `calendar.delete` without a mutation implementation in this task unless a binding contract explicitly requires one; policy denial must prevent any credential resolution/effect.
- Run focused B002 tests plus the accepted regression gate through P006/P005/P004/P003/P002/P001/B001 and prior accepted phases.

## Out of scope

- Chief of Staff behavior, scheduling logic, meeting preparation, prioritization, memory, reminders, or follow-up workflows.
- `LAC-B003` generic external-consumer integration proof.
- OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, enterprise RBAC, or new permission semantics.
- Production Google accounts/credentials or real external Calendar mutation during development qualification.
- Revival or execution of the superseded pre-permission `LAC_B002_CALENDAR_ADAPTER_v0.1.0` package.

## Required outputs

- Calendar typed-effect adapter and bounded transport contract.
- Capability-manifest material and deterministic permission-aware dispatch tests.
- Exact-approval binding tests over every security-relevant Calendar mutation field.
- Credential-isolation, duplicate/reconciliation, malformed/unknown action, wrong-calendar/resource, and delete-denial tests.
- Applicable accepted regression evidence.
- One owner-executable package completing B002 and activating fresh `LAC-B003` on success.

## Next task on success

`LAC-B003` in a fresh implementation session.
