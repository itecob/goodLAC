# ACTIVE TASK — LAC-PI002

## Task ID
`LAC-PI002`

## Objective
Perform real owner UAT of the LAC-PI001 production LAC-governed Pi v1 profile.

## In scope
- Launch `scripts/lac-pi`.
- Exercise known/unconfigured permission discovery, configured ALLOW, conditional ALLOW,
  REQUIRE_APPROVAL, explicit DENY, restart durability, duplicate prevention, receipts,
  emergency pause and bypass resistance.
- Use only the accepted owner P004/P005 administration path from a separate owner terminal.
- Confirm exact approval preserves the same canonical request while waiting/retrying.
- Record owner UAT evidence, then advance to LAC-PI003 only on PASS.

## Out of scope
Additional harnesses, external products, generic compatibility facades, model-provider
expansion, accepted-authority redesign, and Phase 6.

## Required outputs
Owner-visible UAT procedure; durable evidence; deterministic regression confirmation; and,
on PASS, one owner-executable handoff package to LAC-PI003.

## Acceptance
Real Pi 0.85.1 + Bubblewrap/network-none; exact four tools; registration zero authority;
terminal first-use discovery; fresh configured allow; trusted conditional allow; exact
approval with no self-approval; explicit deny without discovery noise; restart/duplicate/
receipt semantics; no admin socket/credential/host-fs/process/network/direct-effect bypass;
standalone Pi remains outside the governed-profile claim; accepted regression PASS.

## Next task on success
`LAC-PI003` — stabilize native local consumer contract/conformance proven by Pi.
