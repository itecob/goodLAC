# R6 rc.12 Candidate Materialization

Date: 2026-10-01

## Finding

Initial R6 review identified `R6-B001-RC12-CANDIDATE-NOT-MATERIALIZED`. The post-v1 roadmap consistently treated `1.0.0-rc.11` as the last accepted historical release and `1.0.0-rc.12` as the target train, but the executable productization identity and current-candidate PI006 assertions remained on rc.11 after R5 integrated qualification completed.

## Historical boundary

The independently reviewed and accepted rc.11 runtime candidate remains:

`818ec607e55f73ef93864ec5a86a793a062262ff`

The public-repository transition through `ce20f345a7de5342b33267387d436739af82e6e1` did not change that accepted authority/runtime baseline. R1-R5 are the post-rc.11 remediation train intended for rc.12.

## Authorized remediation

The owner authorized a bounded release-candidate materialization only. The remediation:

- changes the current productization release identity from rc.11 to rc.12;
- changes the live current-candidate PI006 qualification from rc.11-over-rc.10 rollback coverage to rc.12-over-rc.11 rollback coverage;
- updates live product/workflow documentation to identify rc.12 as the current unaccepted candidate;
- preserves all historical rc.11 / Phase 7 evidence unchanged;
- makes no authorization, policy, approval, emergency, identity, sandbox, credential, dispatcher, continuation, or model-tool-surface change.

## Acceptance boundary

Candidate materialization does not accept rc.12. The exact resulting HEAD requires fresh independent R6 re-review. A PASS must be followed by explicit owner acceptance before rc.12 becomes accepted or is installed/published as an accepted release.
