# B002 Owner Calendar Permission UAT

The B002 owner package runs this UAT automatically after deterministic tests pass. No production Google Calendar account or credential is required.

The harness uses isolated local SQLite state and a synthetic Calendar transport. The permission choices are made through the owner-only P004/P005 administration path; the governed request path cannot mutate policy.

For each first-use scenario, the harness shows trusted application/skill/action/resource/security scope and asks the owner to choose one of the still-unexercised outcomes: **Always allow**, **Ask me each time**, **Not now**, or **Always deny**. It does not provide an automatic/default answer.

When **Ask me each time** is selected, the harness displays the exact request ID, action, resource, canonical hash, and exact arguments and requires the owner to exercise both **Allow once** and **Deny once** on fresh requests. A later fresh request is verified to ask again.

Successful completion records bounded evidence at `qualification/evidence/b002_owner_execution.json`. A cancelled or failed UAT does not advance durable project state to B003.
