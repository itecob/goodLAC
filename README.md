# goodLAC

<p align="center">
  <img
    src="[assets/goodLAC-hero.png](https://github.com/itecob/goodLAC/blob/main/assets/goodLAC-hero.png)"
    alt="goodLAC — Local Agent Controller"
    width="100%"
  />
</p>

**goodLAC** is a source-available **Local Agent Controller (LAC)** developed by **ITECOB Inc.**

goodLAC provides a deterministic authority and effect-control boundary for agent systems. An AI model or agent may propose an action; goodLAC decides whether that action is authorized and whether a bounded effect is permitted to occur.

> **Model output is not authorization.**

goodLAC is a source-available product/source-code project of ITECOB Inc. The public product brand is **goodLAC**. `LAC` remains the technical abbreviation and compatibility namespace used by the implementation.

## Current qualified implementation

The current accepted release candidate is **1.0.0-rc.12**.

`1.0.0-rc.12` is the first goodLAC release intended for ordinary public use. Earlier repository history is retained primarily as development/provenance history. Earlier states may be incomplete, cumbersome to operate, or unsuitable for ordinary users even where they were technically executable.

The accepted rc.12 source candidate is:

`f83fcf57a30b85288796f04161c8e1fc2fc28936`

The qualified default Pi path includes:

- a default-governed installed `pi` entrypoint;
- pinned Pi 0.85.1 running inside the qualified Linux sandbox boundary;
- an exact model-facing effect surface of `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, and `lac_shell_exec`;
- capability registration that grants no authority by itself;
- deterministic standing policy with owner permission decisions;
- project-aware permission scope and isolation;
- Pi TUI permission gating for owner decisions;
- bounded GPT-OSS and Qwen model routes for native Pi model selection;
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

After public-release activation:

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

The current technical installation paths intentionally retain the `local-agent-controller` namespace for compatibility. Public branding does not move existing user state or silently migrate protocol identifiers.

See:

- [`docs/V1_PRODUCTIZATION.md`](docs/V1_PRODUCTIZATION.md)
- [`docs/PI_V1_GOVERNED_PROFILE.md`](docs/PI_V1_GOVERNED_PROFILE.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)

## Licensing status

The operative licence is the **[goodLAC Community License v1.0](LICENSE)**.

The Community License launch model is:

- free personal use;
- free research and educational use;
- free internal organizational use regardless of organization size or revenue;
- permitted private modification for those uses;
- permitted noncommercial redistribution and forking under the Community License conditions;
- commercial licensing required for Productized Use and Third-Party Operational Use; and
- commercial licensing handled by separate, individually negotiated agreement with ITECOB Inc.

Commercial licence enquiries: **support@itecob.com**

## Repository history and licence scope

`1.0.0-rc.12` is the first release intended for ordinary public use.

The public Git history is retained to preserve goodLAC's documented development lineage and provenance. It is not a recommendation to deploy historical development states.

The operative Community License applies to original goodLAC material owned or licensable by ITECOB Inc. throughout the publicly released repository history unless a particular version expressly states that different terms apply. Third-party material remains governed by its own applicable licences and notices.

Older goodLAC versions do not become commercially unrestricted merely because they are older.

## Forks and modifications

Permitted forks may use their own primary name and branding, but modified versions must:

- preserve required copyright, licence, and attribution notices;
- remain under the same goodLAC Community License when redistributed;
- provide complete corresponding source code when a modified version is redistributed;
- clearly disclose that they were modified;
- clearly state that they are not an official ITECOB Inc. distribution; and
- not imply ITECOB verification, certification, approval, endorsement, or support.

A recommended copy/paste notice is provided in [`docs/MODIFIED_VERSION_NOTICE.md`](docs/MODIFIED_VERSION_NOTICE.md). Substantially equivalent wording is permitted.

No separate "official/unmodified" status notice is required for ITECOB's own distribution beyond the ordinary copyright, licence, NOTICE, version, and release information.

## Commercial licensing

Commercial licensing is available only by separate agreement with ITECOB Inc.

There is no automatic entitlement, standard public commercial licence, fixed public pricing, or promise that an applicant will receive a licence. Proposed commercial use is reviewed individually and any resulting terms are negotiated separately.

Commercial licence enquiries: **support@itecob.com**

See [`COMMERCIAL-LICENSING.md`](COMMERCIAL-LICENSING.md).

## Contributing

External code and other copyrightable contributions are **not currently being accepted for incorporation into goodLAC**.

Bug reports, feature requests, ideas, technical discussion, and other feedback are welcome. ITECOB Inc. may independently investigate, design, or implement ideas raised through those channels.

The contributor agreement remains a draft and is not a launch dependency while external code contributions are closed.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

Undisclosed vulnerabilities must not be reported through public issues or pull requests.

At public launch, the designated private reporting mechanism is **GitHub Private Vulnerability Reporting** through the repository's Security interface. That feature must be enabled when the repository is made public.

See [`SECURITY.md`](SECURITY.md).

## No support commitment

The Community License does not include technical support, implementation assistance, maintenance, consulting, updates, or a service-level commitment from ITECOB Inc.

Any support or services ITECOB Inc. may separately offer are outside the Community License unless expressly stated otherwise.

ITECOB Inc. has no obligation to support third-party modifications or modified distributions.

## Warranty and responsibility

goodLAC is intended to be provided **as is** and **as available**, without warranties or guarantees to the maximum extent permitted by law.

Users are responsible for determining whether goodLAC, connected models, agents, tools, integrations, configurations, and outputs are suitable for their intended purpose. Users remain responsible for their deployment, decisions, services, actions, and resulting consequences.

The complete warranty, liability, indemnity, patent, termination, and licence-amendment terms are contained in the operative Community License.

## Third-party installation and services

Third parties may charge for installation, configuration, training, migration, auditing, or support for a customer's own internal goodLAC deployment where goodLAC itself is not being sold and the provider does not turn goodLAC into third-party operational functionality.

Charging for goodLAC itself, a modified goodLAC distribution, access to goodLAC functionality, Productized Use, or Third-Party Operational Use requires a separate commercial licence from ITECOB Inc.

Third-party installation, configuration, or support does **not** constitute certification, verification, endorsement, or approval by ITECOB Inc.

There is currently no qualified `goodLAC verify-install` system.

## goodLAC Conformance

A separate **goodLAC Conformance** project is being developed to help users evaluate whether an exact external repository/version satisfies documented goodLAC integration requirements.

It is intended to assess one exact repository/version using evidence contained in that repository. It is not a recommendation system, does not assess the user's full system, does not guarantee security, and does not extend an assessment to unrelated past or future versions.

The written Conformance Specification/matrix is intended for **CC BY-SA 4.0**. The official verifier/evidence tooling is intended to follow the separate goodLAC source-available/commercial-use model.

See [`CONFORMANCE.md`](CONFORMANCE.md).

## Third-party material

Third-party software and upstream projects retain their own licenses and notices. goodLAC's Community License does not relicense third-party material that ITECOB Inc. does not own or have authority to license.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`UPSTREAM_LOCK.json`](UPSTREAM_LOCK.json).
