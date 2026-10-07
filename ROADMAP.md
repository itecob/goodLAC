# goodLAC Roadmap

This roadmap describes planned architectural direction. It is not a claim that an item is already implemented and does not change current-release behavior.

## Current release

The current accepted release candidate is **1.0.0-rc.12**.

Pi is the currently qualified reference agent harness. The rc.12 reference environment includes specific local model-routing work used during qualification. Those choices describe what was tested; they are not the long-term authority boundary of goodLAC.

## Architectural direction

goodLAC is intended to remain a standalone authority and effect-control plane independent of the particular model, inference layer, agent harness/application, and user interface.

### Model and inference-layer independence

Model selection and inference compatibility belong to the agent harness and inference layer. Future goodLAC integrations should not require product-level model-family allowlists merely because a model differs from the qualified reference models.

### Agent-harness independence

Pi is the current reference harness, not the only architecture in which goodLAC can be useful. Future integrations may target other harnesses/applications, CLIs, TUIs, web/desktop applications, or custom systems while preserving the same authority semantics.

### Authority-path completeness

A deployment is goodLAC-governed only when consequential effects are forced through the goodLAC authority boundary.

Installing goodLAC or making it callable does not, by itself, make an agent governed. If an agent retains an alternate way to perform the same consequential effect without goodLAC, that path is a bypass and the integration is incomplete.

### Trusted integration context

Authorization-relevant identity and context must come from trusted system/controller binding rather than model assertions.

## Compatibility: tested is not certified

goodLAC may publish configurations that the project has tested. That is evidence about those configurations, not a certification program or permanent allowlist.

- **Tested configuration:** exercised by the project.
- **Expected compatibility:** should be possible when the goodLAC integration contract is satisfied.
- **Untested/unverified:** not independently exercised by the project.

Untested does not mean prohibited. Tested does not mean guaranteed, certified, or officially approved for every environment.

## Documentation and integration usability

A documentation goal is that a competent coding agent can inspect the repository, map an unfamiliar agent architecture, identify required trust boundaries, and produce a correct integration and verification plan without inventing missing security assumptions.

See [`docs/INTEGRATING_GOODLAC.md`](docs/INTEGRATING_GOODLAC.md).

## Release discipline

Roadmap items requiring runtime or authority changes will go through a future qualified release process. This roadmap does not silently change `1.0.0-rc.12`.
