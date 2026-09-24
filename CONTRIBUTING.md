# Contributing to goodLAC

goodLAC is developed by ITECOB Inc. around explicit authority and effect-control boundaries. Contributions that change a trust boundary require correspondingly strong tests and evidence.

## Contributor licensing status

> **Contributor licensing terms are being finalized. ITECOB Inc. may require completion of a contributor agreement before accepting external code contributions.**

The intended contributor model is:

- the contributor retains copyright ownership of their contribution;
- the contributor confirms they have authority to contribute the work;
- ITECOB Inc. receives sufficiently broad, perpetual rights to use, reproduce, modify, distribute, sublicense, and relicense accepted contributions;
- ITECOB Inc. must be able to distribute accepted contributions under both the public goodLAC license and separate commercial licenses;
- applicable patent rights and third-party restrictions must be addressed; and
- ITECOB Inc. is not obligated to accept, merge, maintain, or distribute a contribution.

`CLA-DRAFT.md` records the current draft framework. It is **not active** and requires legal review before activation.

No automated CLA acceptance should be inferred from this repository.

## Before opening a pull request

1. Keep the change bounded to a clearly stated problem.
2. Identify any authority, policy, approval, credential, identity, persistence, sandbox, network, or effect boundary touched by the change.
3. Do not treat capability registration, model output, audit records, or administrative disposition as authorization.
4. Add or update deterministic tests appropriate to the affected boundary.
5. Preserve existing third-party notices and disclose any new externally sourced material or licensing restriction.
6. Do not silently rename `LAC`/`lac` compatibility identifiers as part of unrelated branding work.
7. Run the relevant regression gates and `git diff --check`.

## Security-sensitive changes

Security-sensitive changes must preserve the documented invariants unless an explicit architecture decision authorizes a change.

In particular:

- new capabilities must not silently create authority;
- exact approvals must remain bound to the exact canonical operation;
- policy must remain current at dispatch;
- credentials must remain outside agent/model context;
- unknown or inconsistent authority state must fail closed;
- denied or closed effects must not be revived by later policy changes;
- emergency pause must remain authoritative; and
- administration must remain isolated from the governed runtime surface.

See `docs/ARCHITECTURE.md`.

## Pull-request information

A pull request should explain:

- the problem being solved;
- files and trust boundaries changed;
- tests run;
- evidence produced;
- compatibility implications;
- whether third-party code or material is introduced; and
- whether any public documentation, licensing, or security statement changes.

The repository pull-request template captures these items.

## Security reports

Do not submit undisclosed vulnerabilities through a public pull request or issue. Follow `SECURITY.md`.

## Acceptance

ITECOB Inc. may decline, defer, limit, or request changes to any contribution.

Until a reviewed contributor agreement is activated, ITECOB Inc. may defer merging external code when accepting the contribution could create ambiguity about the rights needed to continue public and commercial distribution.
