# goodLAC Brand and Reference Policy

## Exact product identity

The public product brand is:

**goodLAC**

Use that exact capitalization in normal product prose.

Do not use `GoodLac`, `GoodLAC`, `Good LAC`, or `goodlac` in product prose except where a technical system, filename, package identifier, URL behavior, compatibility identifier, or case-insensitive environment requires another form.

goodLAC is a product/source-code project of **ITECOB Inc.**

The underlying technology may be described as:

**Local Agent Controller (LAC)**

A suitable factual description is:

> goodLAC is a source-available Local Agent Controller developed by ITECOB Inc.

## Technical compatibility namespace

`LAC` and `lac` remain established technical compatibility namespaces.

Branding changes do not imply migration of:

- `lac.*` protocol or schema identifiers;
- `LAC_*` environment variables;
- commands such as `lacctl` and `lac-pi`;
- model-facing tools such as `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, and `lac_shell_exec`;
- `/lac-*` owner commands;
- capability/application/skill identifiers;
- socket/protocol identifiers;
- durable state, receipt, request, approval, or audit identities; or
- existing `local-agent-controller` installation, state, configuration, cache, or migration paths.

Those names may remain technical identifiers even when public prose uses goodLAC.

## Trademark status

This policy does **not** state that `goodLAC` is a registered trademark. Trademark registration has not been completed.

Do not use the ® symbol.

Do not claim that goodLAC is patented, patent-pending, trademark-registered, certified, or formally trademark-protected unless that status is independently established later.

## Permitted factual references

Accurate factual references are permitted, for example:

- "Based on goodLAC by ITECOB Inc."
- "Designed to integrate with goodLAC."
- "Assessment performed using the goodLAC Conformance Specification."
- "Compatible with the goodLAC interface," where factually correct.

Factual reference does not imply endorsement.

## Controlled claims

Third parties must not claim or imply any of the following without specific authorization from ITECOB Inc.:

- Official goodLAC
- goodLAC Certified
- goodLAC Verified
- Official goodLAC Partner
- ITECOB approved
- ITECOB certified
- an official goodLAC badge or logo
- endorsement, verification, partnership, or approval by ITECOB Inc.

Technical conformance and brand endorsement are separate.

## Modified versions

Any Modified Version of goodLAC must use a primary project or product name clearly different from `goodLAC` unless ITECOB Inc. expressly authorizes otherwise.

Every Modified Version must carry a clear notice communicating substantially the following facts:

- it is based on goodLAC by ITECOB Inc.;
- it has been modified;
- it is not an official ITECOB Inc. distribution;
- ITECOB Inc. has not reviewed, verified, certified, approved, or endorsed the modifications unless expressly stated otherwise;
- ITECOB Inc. makes no representation that the modified version preserves official goodLAC's security, authority, compatibility, or operational properties; and
- ITECOB Inc. does not provide support for the modifications or modified distribution under the Community License.

The notice requirement applies to every Modified Version. It is not conditioned on whether the version is public, private, internal, or redistributed.

The notice must remain with the modified repository, package, distribution, or equivalent durable material.

Substantially equivalent wording is permitted. Exact wording is not required.

See `docs/MODIFIED_VERSION_NOTICE.md` for a copy/paste example.

## Official distribution

ITECOB's official unmodified distribution does not require a separate "official/unmodified" status declaration beyond ordinary copyright, licence, NOTICE, version, and release information.

## Historical records

Accepted qualification evidence, historical logs, ADRs, hashes, and other provenance may continue to contain "Local Agent Controller", `LAC`, `lac`, old repository paths, or earlier project terminology.

Do not rewrite historical evidence solely to make branding uniform.
