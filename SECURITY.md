# Security Policy

## Scope

This policy applies to security issues in the goodLAC repository and the exact versions identified by the repository's durable project state.

The current durable state identifies **1.0.0-rc.11** as the last accepted release candidate. The project does not yet publish a general long-term support policy for earlier or future versions.

## Reporting a vulnerability

Do not publish undisclosed vulnerability details, exploit instructions, credentials, or other sensitive security material in a public GitHub issue.

If the repository host exposes **private vulnerability reporting** for this repository, use that private mechanism.

If no private vulnerability-reporting mechanism is available, this repository currently does not document a separate private security contact.

> **OWNER ACTION REQUIRED BEFORE PUBLIC RELEASE:** configure an appropriate private vulnerability-reporting channel or add an approved private security contact.

Do not invent or infer a security email address from the company or repository name.

## What to include

A useful private report should include, where possible:

- the exact goodLAC commit/version;
- affected component or trust boundary;
- reproduction steps;
- expected versus observed behavior;
- whether consequential effects, credentials, policy, approval, identity, state, or sandboxing are implicated;
- environmental prerequisites; and
- a minimal proof of concept that avoids unnecessary real-world impact.

## Security model

goodLAC is designed around explicit authority/effect boundaries, fail-closed behavior, credential separation, exact approvals, durable effect truth, sandboxing, and related trust invariants documented in `docs/ARCHITECTURE.md` and `docs/THREAT_MODEL.md`.

Those design and qualification statements are not a guarantee against all vulnerabilities.

No guarantee is made that goodLAC is error-free, vulnerability-free, secure in every environment, or suitable for every use.

## Modified and third-party deployments

ITECOB Inc. does not warrant that modified versions, unsupported combinations, third-party installations, external integrations, or deployments outside the qualified environment preserve the intended security properties.

A third-party installer or auditor is not automatically certified, verified, endorsed, or approved by ITECOB Inc.

There is currently no qualified `goodLAC verify-install` system.

## Disclosure coordination

Any future disclosure timeline or service-level commitment must be explicitly published by ITECOB Inc. Do not infer an SLA from this policy.
