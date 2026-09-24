# goodLAC

**goodLAC** is a source-available **Local Agent Controller (LAC)** developed by **ITECOB Inc.**

goodLAC provides a deterministic authority and effect-control boundary for agent systems. An AI model or agent may propose an action; goodLAC decides whether that action is authorized and whether a bounded effect is permitted to occur.

> **Model output is not authorization.**

goodLAC is a source-available product/source-code project of ITECOB Inc. The public product brand is **goodLAC**. `LAC` remains the technical abbreviation and compatibility namespace used by the implementation.

## Current qualified implementation

The repository's accepted authority/runtime baseline is **1.0.0-rc.11**. Phase 7 completed independent re-review with no remaining security blocker in the accepted scope.

The qualified default Pi path includes:

- a default-governed installed `pi` entrypoint;
- pinned Pi 0.85.1 running inside the qualified Linux sandbox boundary;
- an exact model-facing effect surface of `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, and `lac_shell_exec`;
- capability registration that grants no authority by itself;
- deterministic standing policy with `ALLOW`, `REQUIRE_APPROVAL`, and `DENY`;
- exact one-time approval binding;
- policy re-evaluation immediately before dispatch;
- durable execution leases, idempotency, receipts, and effect state;
- credential separation from the governed model context;
- an owner-only administration surface;
- durable emergency pause;
- fail-closed handling for unknown, stale, malformed, expired, or inconsistent authority state; and
- explicit, fresh-request-only workflow continuation after permission configuration.

The repository also contains generic Gmail and Google Calendar adapters. They are platform capabilities, not part of the default four-tool Pi model surface, and they require separate credentials, configuration, permissions, and integration work before consequential use.

## Why goodLAC exists

Agent systems can be useful without giving the model the same authority as the human or organization operating the machine.

goodLAC separates **proposal** from **authorization and effect**. The model can express intent. Deterministic controller code owns capability validation, policy, approvals, identity binding, leases, dispatch, receipts, emergency state, and other authority-relevant decisions.

This is broader than an "AI firewall." It is an authority/effect control boundary intended to make consequential agent behavior explicit, bounded, inspectable, and interruptible.

## Core trust principles

The current architecture is built around these principles:

- no implicit authority;
- model output is never authorization;
- capability registration does not automatically grant permission;
- least privilege;
- exact approval binding;
- current-policy re-evaluation before dispatch;
- credential separation;
- deny precedence;
- durable effect truth and receipts;
- idempotency and duplicate-effect prevention;
- fail-closed behavior;
- deterministic authority decisions;
- owner interruptibility and emergency pause;
- auditability without treating audit records as authority; and
- modular/composable trust boundaries.

These statements describe the documented and qualified implementation boundaries. They are not a guarantee that every deployment, modification, integration, operating system, dependency, or future version is vulnerability-free.

## What goodLAC does — and does not do

goodLAC is an independent authority/effect-control product. It is not itself an AI model, general-purpose agent, cognition system, memory system, workflow engine, AI operating system, or general-purpose secret manager.

A process is not "goodLAC-governed" merely because it can call goodLAC. The qualified governed path also constrains alternate effect routes, ambient filesystem/process/network authority, credential exposure, and administrator access.

Technical identifiers such as `lac.*` schemas, `LAC_*` environment variables, `lacctl`, `lac-pi`, `/lac-resume`, and the existing `local-agent-controller` state/configuration paths are compatibility identifiers. Public branding does not imply that those interfaces have been renamed.

## Quick start

The self-contained permission walkthrough requires Linux, Git, and Python 3.10 or newer.

After the GitHub repository has been renamed to `goodLAC`:

```bash
git clone https://github.com/itecob/goodLAC.git
cd goodLAC
python3 scripts/p006_owner_permission_demo.py --auto
```

The walkthrough uses temporary local state and synthetic effects. It demonstrates capability registration, denied requests, permission changes, conditional permissions, explicit approval, and duplicate prevention.

Run the repository's Python unit, integration, and acceptance suites with:

```bash
scripts/test-c010
```

Later integration/profile gates have additional Linux sandbox and pinned-runtime prerequisites documented under `docs/`.

## Installation and governed Pi

The v1 productization code provides versioned user-level installation, rollback, configuration, `lac-doctor`, owner administration commands, and the default-governed `pi` entrypoint.

The current technical installation paths intentionally retain the `local-agent-controller` namespace for compatibility. Public rebranding does not move existing user state or silently migrate protocol identifiers.

See:

- [`docs/V1_PRODUCTIZATION.md`](docs/V1_PRODUCTIZATION.md)
- [`docs/PI_V1_GOVERNED_PROFILE.md`](docs/PI_V1_GOVERNED_PROFILE.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)

## Licensing status

**No operative goodLAC project license has yet been activated.**

The repository previously had no project license, and this transition intentionally does not convert an unreviewed custom draft into an operative license. [`LICENSE-DRAFT.md`](LICENSE-DRAFT.md) is marked **DRAFT — LEGAL REVIEW REQUIRED BEFORE PUBLIC RELEASE** and does not itself grant permission.

Until a reviewed license is formally activated, do not infer permission to use, modify, or redistribute goodLAC merely from repository visibility.

### Intended community licensing model — pending legal review and activation

The approved product-policy intent is:

> The goodLAC core is intended to be provided as source-available software so individuals and organizations can understand, inspect, modify, and build their own agent systems around a transparent authority boundary. Once an operative public license is activated, the complete functionality represented as part of this repository will be governed by that public license. Other products, modules, services, or applications developed by ITECOB Inc. may be released under separate source-available, commercial, or other licenses.

> **Once the reviewed goodLAC Community License is activated, goodLAC is intended to be free for personal, research, educational, and internal organizational use. Commercial licensing is intended to be required when goodLAC is incorporated into, resold as, or used to provide a commercial product, SaaS, hosted service, or managed service to third parties.**

The controlling intended distinction is **whose systems, accounts, resources, or service functionality goodLAC is operating**:

- use by a person or organization to operate its own systems and workflows is intended to be free internal use, including when resulting work is delivered to paying customers;
- paid installation, configuration, migration, auditing, training, or support for a customer's own internal deployment is intended to be permitted when control is handed to the customer; and
- using goodLAC itself to operate, control, authorize, administer, or provide functionality for third-party systems, accounts, users, or customers is intended to require a commercial license from ITECOB Inc.

Entity type and organization size are not intended to determine the licensing boundary.

See [`COMMERCIAL-LICENSING.md`](COMMERCIAL-LICENSING.md) and the draft license for the complete intended policy.

## Forks and attribution

Under the intended Community License, permitted noncommercial forks may use their own name and branding but must preserve required notices and clearly disclose derivation, substantively equivalent to:

> Based on goodLAC by ITECOB Inc.

Attribution in project documentation is intended to be sufficient; goodLAC branding is not intended to be required inside a fork's running user interface.

See [`BRAND.md`](BRAND.md).

## Third-party installation and services

Third parties may provide installation, configuration, training, migration, auditing, or support for a customer's own internal goodLAC deployment under the intended licensing model. Ongoing operational use of goodLAC on behalf of customers is intended to require a commercial license.

Third-party installation, configuration, or support does **not** constitute certification, verification, endorsement, or approval by ITECOB Inc.

There is currently no qualified `goodLAC verify-install` system. Do not infer installation certification from this repository.

## goodLAC Conformance

A separate **goodLAC Conformance** project is being developed to help users evaluate whether an exact external repository/version satisfies documented goodLAC integration requirements.

It is intended to assess one exact repository/version using evidence contained in that repository. It is not a recommendation system, does not assess the user's full system, does not guarantee security, and does not extend an assessment to unrelated past or future versions.

The written Conformance Specification/matrix is intended for **CC BY-SA 4.0**. The official verifier/evidence tooling is intended to follow the separate goodLAC source-available/commercial-use model. These are separate licensing surfaces.

See [`CONFORMANCE.md`](CONFORMANCE.md).

## Commercial licensing

Commercial licensing is intended to be available only by individual agreement with ITECOB Inc. It is not automatic, and no fixed pricing, entitlement, or automatic future relicensing is promised.

**Owner action required:** add the approved commercial-licensing contact channel before activating the commercial licensing program.

See [`COMMERCIAL-LICENSING.md`](COMMERCIAL-LICENSING.md).

## Contributing

Contributor terms are being formalized. ITECOB Inc. may require completion of a reviewed contributor agreement before accepting external code contributions.

The intended model is that contributors retain copyright while granting ITECOB Inc. sufficient rights to distribute accepted contributions under both the public goodLAC license and separate commercial licenses.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CLA-DRAFT.md`](CLA-DRAFT.md).

## Security

See [`SECURITY.md`](SECURITY.md) for reporting guidance and current support statements.

**Owner action required:** ensure an appropriate private vulnerability-reporting channel is configured before public release if one is not already available through the repository host.

## Warranty and no guarantees

goodLAC is intended to be provided without warranties and without any promise that it is error-free, vulnerability-free, secure in every environment, or suitable for every use. Deployment and configuration choices remain the user's responsibility, and modified versions or third-party installations may not preserve the qualified security properties.

Any final warranty disclaimer and limitation of liability will be governed by the reviewed operative license and applicable law.

## Third-party material

Third-party software and upstream projects retain their own licenses and notices. Public goodLAC branding does not alter those obligations.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`UPSTREAM_LOCK.json`](UPSTREAM_LOCK.json).
