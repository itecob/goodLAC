# Pull request

## Problem and scope

Describe the problem and the bounded change.

## Files / trust boundaries changed

List the material files and any affected authority, policy, approval, identity, credential, state, sandbox, network, dispatch, receipt, or emergency-control boundary.

## Security invariants

- [ ] This change does not silently grant authority through capability registration.
- [ ] Model output is not treated as authorization.
- [ ] Exact approval binding remains intact where applicable.
- [ ] Current policy is re-evaluated before consequential dispatch where applicable.
- [ ] Credential separation is preserved.
- [ ] Unknown or inconsistent authority state still fails closed.
- [ ] Emergency pause remains authoritative where applicable.
- [ ] New/changed capabilities have tests appropriate to the trust boundary.
- [ ] Any intentional invariant change is explicitly documented and separately authorized.

## Compatibility

- [ ] Existing `LAC`/`lac` technical identifiers were preserved unless migration is explicitly part of this pull request.
- [ ] Historical qualification evidence was not rewritten for cosmetic branding consistency.
- [ ] State/protocol migration, if any, has explicit compatibility and rollback coverage.

## Licensing / provenance

- [ ] No third-party notice or license was removed.
- [ ] New third-party material, if any, is identified with its source and applicable terms.
- [ ] This pull request does not present `LICENSE-DRAFT.md` or `CLA-DRAFT.md` as legally activated.
- [ ] Any public licensing or brand-policy change is explicitly identified below.

## Tests and evidence

List every command run and the result.

## Public documentation impact

Describe README, security, licensing, contribution, conformance, or brand-policy changes.

## Contributor terms

Contributor licensing terms are being finalized. ITECOB Inc. may require completion of a reviewed contributor agreement before accepting external code contributions.
