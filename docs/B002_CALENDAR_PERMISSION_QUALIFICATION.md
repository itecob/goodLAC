# B002 Calendar Adapter Against Permission Management

**Task:** `LAC-B002`
**Scope:** Generic Google Calendar typed-effect adapter integrated with the accepted P001-P006 permission plane.

## Typed actions

- `calendar.search`
- `calendar.read`
- `calendar.propose`
- `calendar.create`
- `calendar.modify`
- `calendar.cancel`
- `calendar.delete`

`calendar.delete` is represented for capability/policy enforcement but has no mutation implementation in B002.

## Authority sequence

A registered valid Calendar request with no owner-configured standing rule/default is terminally `DENY`, creates/aggregates `NO_CONFIGURED_STANDING_PERMISSION` owner-review work, receives no lease, does not resolve the Calendar credential, and does not invoke the adapter. Later administration cannot revive the original request. Only a fresh request is evaluated under the current policy.

Configured `DENY` produces no recurring discovery work. `REQUIRE_APPROVAL` uses the existing exact one-time approval path and immediate pre-dispatch policy re-evaluation.

## Exact mutation binding

Calendar mutation requests bind the calendar resource and all applicable event material: event identity/etag, title, start/end, timezone, attendees, location, recurrence, conference settings, and notification mode. Changing any bound material changes the canonical effect hash and invalidates an approval for the prior request.

## Credential and transport boundary

The model/runtime sees no Google credential or credential reference. The adapter resolves the configured opaque credential reference only after current authorization reaches invocation/reconciliation. Provider results containing credential-shaped keys are rejected.

`calendar.propose` is local and resolves no service credential. Production Google Calendar transport exists behind the same bounded adapter interface but is not used for B002 acceptance. All automated and owner UAT effects use synthetic/local transport only.

## Owner acceptance

Automated tests are necessary but insufficient. `scripts/b002_owner_permission_uat.py` requires a real interactive terminal and forces the owner to personally exercise:

- Always allow
- Ask me each time
- Not now
- Always deny
- Allow once
- Deny once

The UAT proves policy durability across controller/admin reopen, original-request non-resumption, Ask-every-time behavior for later fresh requests, configured-DENY discovery silence, and absence of the owner admin socket from the governed sandbox.
