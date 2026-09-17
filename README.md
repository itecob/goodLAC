# Local Agent Controller

Local Agent Controller (LAC) is a local-first control layer for AI agents. It receives proposed actions, checks them against registered capabilities and owner-configured permissions, and only then allows a bounded effect to run.

The central idea is simple: an AI agent may propose an action, but deterministic software decides whether that action is allowed to have an effect.

## Current status

LAC is experimental software under active development. The repository currently contains:

- a durable local controller state store;
- capability and permission management;
- explicit approval for actions that require confirmation;
- bounded local filesystem and shell effect adapters;
- duplicate-prevention, receipts, emergency-pause, and fail-closed behavior; and
- an integration profile for a locally running agent harness.

The project is not production-ready, and its interfaces may change. The quick start below exercises the local controller with synthetic effects only. It does not contact Gmail, Google Calendar, or any other external service.

## What LAC is—and is not

LAC is an authority and effect-control layer. It is not an AI model, chat application, agent by itself, workflow engine, or general-purpose secret manager.

The controller is designed to keep decisions and durable state on the local machine. External integrations are separate adapters and are not configured by the quick start.

## Quick start

The self-contained walkthrough requires Linux, Git, and Python 3.10 or newer. No Python package installation is required for this demonstration.

1. Install Git and Python 3.10+ using your operating system’s normal package manager.

2. Download the repository:

   ```bash
   git clone https://github.com/itecob/local-agent-controller.git
   cd local-agent-controller
   ```

3. Run the automatic local walkthrough:

   ```bash
   python3 scripts/p006_owner_permission_demo.py --auto
   ```

   The walkthrough uses temporary local state and synthetic effects. It demonstrates capability registration, denied requests, permission changes, conditional permissions, explicit approval, and duplicate prevention. A successful run ends with a pass summary.

4. To step through the same walkthrough interactively, omit `--auto`:

   ```bash
   python3 scripts/p006_owner_permission_demo.py
   ```

5. Run the repository’s local Python test suites:

   ```bash
   scripts/test-c010
   ```

   The advanced integration and sandbox checks require a normal Linux environment with permission to create local Unix sockets and process sandboxes. Some later-stage checks also depend on separately prepared runtime assets.

## Advanced agent profile

The repository includes an optional LAC-governed profile for a local agent harness. It is not a one-command installation yet. Running that profile requires separately prepared, pinned agent and model-runtime assets, a compatible local model, CUDA support, and the Linux sandbox tools used by the project.

Those assets are intentionally not bundled with this repository or downloaded automatically. A fresh clone can run the self-contained controller walkthrough above, but cannot be assumed to run the full local-model profile without that additional environment.

## Safety and scope

The project is intended for local experimentation and development. Do not connect production accounts, credentials, or consequential external actions until the relevant integration has been independently reviewed for your intended environment.

The repository contains technical design and test material for development. Those materials describe implementation boundaries and are not a substitute for a security review or a production deployment guide.

## License

No license has been selected for this project yet. Until one is added, the repository should not be treated as granting permission to use, modify, or redistribute the code.
