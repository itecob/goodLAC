# Active Task

**Task ID:** `LAC-P2-REMEDIATION-P2-B001`

**Objective:** Remediate only Phase 2 blocker `P2-B001`: the `shell:v1` reviewed non-launching executable set currently admits GNU `/usr/bin/sort`, whose `--compress-program=PROG` facility can invoke another program and therefore violates H004 executable-class closure.

**Secure-SDLC scope:** This is defensive remediation of owner-controlled software. Use source inspection and deterministic tests limited to the repository, temporary local workspaces, synthetic files/canary values, local test databases, isolated local sandbox instances, and other non-production fixtures. Do not use real credentials, production accounts, third-party systems, external targets, or generalized procedures for circumventing security controls.

**In scope:** verify the blocked-review handoff; make `/usr/bin/sort` ineligible for generic `shell:v1`; add permanent deterministic regression coverage; inspect the existing reviewed safe-leaf set only as necessary to ensure no equivalent external-program launcher remains admitted; rerun `scripts/test-h004`, `scripts/test-h003`, `scripts/test-h002`, `scripts/test-h001`, and the complete applicable Phase 1 regression; create one corrected Phase 2 candidate and one owner-executable remediation package; stage a fresh Phase 2 independent re-review prompt.

**Out of scope:** architecture redesign; new generic execution mechanisms; new interpreter/shell contracts; Phase 3 implementation; Pi or FreeToken integration; Gmail, Calendar, Slack, Git, deployment, package/service or other future effects; remediation unrelated to `P2-B001`.

**Required inputs:** blocked Phase 2 implementation candidate `5cdd824b083ede92c192ef17f039cdbf0206cc44`; blocked-review live handoff commit `e91773530125ebcd01a441d83b6bc91018864325`; Phase 1 reviewed commit `ba21d50c26540147c458a8e3f402e15e71efe9c7`; owner execution evidence `${HOME}/Downloads/LAC_P2_INDEPENDENT_REVIEW_EVIDENCE_20260913_223217.log`; `docs/CONTRACTS.md`; `packages/effects/shell/adapter.py`; H003/H004 tests and gates.

**Required outputs:** corrected implementation and permanent blocker-specific regression; all affected/full gates passing; one corrected Phase 2 candidate commit; one owner-executable package that installs the corrected candidate and a fresh `LAC-P2-REVIEW` successor prompt.

**Acceptance tests:** `/usr/bin/sort` cannot be selected through runtime/user configuration for generic `shell:v1`; any equivalent launcher discovered within the reviewed safe-leaf set is likewise excluded with regression coverage; existing positive bounded workspace effects remain functional; H001/H002/H003/H004 gates pass; applicable Phase 1 regressions pass; no Phase 3 capability is introduced.

**Package required?** yes

**Next task on success:** `LAC-P2-REVIEW` in one fresh independent re-review session. Do not begin Phase 3 until that review returns `PASS`.
