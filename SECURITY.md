# Security Policy

## Scope

This policy applies to security issues in the goodLAC repository and the versions identified by the repository's public release and version metadata.

The current accepted release candidate is **1.0.0-rc.12**. `1.0.0-rc.12` is the first release intended for ordinary public use. The project does not currently publish a general long-term support commitment for earlier or future versions.

## Reporting a vulnerability

Do not publish undisclosed vulnerability details, exploit instructions, credentials, or other sensitive security material in a public GitHub issue, discussion, or pull request.

The designated private reporting mechanism for public launch is **GitHub Private Vulnerability Reporting**.

Use the repository's:

**Security → Report a vulnerability**

interface to submit a private report.

There is no separate fallback security email designated. GitHub Private Vulnerability Reporting is the designated private reporting path for the public repository.

## What to include

A useful private report should include, where possible:

- the exact goodLAC commit/version;
- affected component or trust boundary;
- reproduction steps;
- expected versus observed behavior;
- whether consequential effects, credentials, policy, approval, identity, state, or sandboxing are implicated;
- environmental prerequisites; and
- a minimal proof of concept that avoids unnecessary real-world impact.

Do not include credentials, access tokens, private keys, or unrelated personal information unless specifically necessary to demonstrate the issue.

## Security model

goodLAC is designed around explicit authority/effect boundaries, fail-closed behavior, credential separation, exact approvals, durable effect truth, sandboxing, and related trust invariants documented in `docs/ARCHITECTURE.md` and `docs/THREAT_MODEL.md`.

Those design and qualification statements are not a guarantee against all vulnerabilities.

goodLAC is provided without a guarantee that it is error-free, vulnerability-free, secure in every environment, uninterrupted, compatible with every dependency, or suitable for every use.

## Modified and third-party deployments

ITECOB Inc. does not warrant that modified versions, unsupported combinations, third-party installations, external integrations, or deployments outside the qualified environment preserve the intended security properties.

Any modified goodLAC version must carry the modification/unofficial-distribution notice required by the applicable Community License.

ITECOB Inc. has no obligation to provide support for third-party modifications or modified distributions.

A third-party installer or auditor is not automatically certified, verified, endorsed, or approved by ITECOB Inc.

There is currently no qualified `goodLAC verify-install` system.

## Disclosure coordination

Please allow ITECOB Inc. a reasonable opportunity to investigate and, where appropriate, correct a reported vulnerability before publishing detailed exploit information.

No specific response time, remediation time, bounty, disclosure deadline, or service-level commitment is promised unless ITECOB Inc. expressly agrees to one for a particular matter.
