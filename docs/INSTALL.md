# Installing goodLAC 1.0.0-rc.12

This guide describes the public source-install path for **goodLAC 1.0.0-rc.12**, the first release intended for ordinary public use.

goodLAC is a local-first authority/effect controller. The installation code is versioned and supports rollback, but rc.12 deliberately does **not** download or silently substitute unqualified model/runtime assets.

## Fastest way to evaluate the control model

If you want to understand goodLAC before provisioning the full governed Pi runtime:

```bash
git clone https://github.com/itecob/goodLAC.git
cd goodLAC
python3 scripts/p006_owner_permission_demo.py --auto
```

The demo uses temporary local state and synthetic effects. It exercises permission discovery, standing policy, explicit approval, deny behavior, and duplicate-effect prevention without requiring the full model runtime.

## Supported public baseline

The accepted rc.12 productization path is for Linux and requires:

- Python 3.10 or newer;
- Git;
- Node.js compatible with the pinned Pi requirement (`>=22.19.0`);
- Bubblewrap (`bwrap`);
- `fd`;
- `rg` / ripgrep.

The full managed local-model path additionally expects the exact qualified Pi and FreeToken checkouts plus the accepted local model/runtime assets. The accepted FreeToken runtime path was qualified with a CUDA 13 toolkit.

goodLAC fails closed rather than silently downloading, upgrading, or substituting authority-relevant runtime dependencies.

## 1. Clone goodLAC

```bash
git clone https://github.com/itecob/goodLAC.git
cd goodLAC
```

## 2. Provision the exact pinned Pi checkout

The rc.12 verifier expects Pi at:

```text
~/.cache/local-agent-controller/phase0/upstream/pi
```

Pinned commit:

```text
da840b6216578c2a571d0374ac6a2091a83f9d91
```

```bash
mkdir -p ~/.cache/local-agent-controller/phase0/upstream
git clone https://github.com/earendil-works/pi.git \
  ~/.cache/local-agent-controller/phase0/upstream/pi
git -C ~/.cache/local-agent-controller/phase0/upstream/pi \
  checkout --detach da840b6216578c2a571d0374ac6a2091a83f9d91
python3 scripts/verify_pi_pin.py
```

The governed native Pi path also requires the pinned checkout's JavaScript dependencies to be installed locally. Use the upstream Pi repository's package-manager instructions for that exact checkout; do not substitute a different Pi revision.

## 3. Provision the exact pinned FreeToken checkout

The rc.12 verifier expects FreeToken at:

```text
~/.cache/local-agent-controller/phase0/upstream/freetoken
```

Pinned commit:

```text
af71ba43206e124f5ff6419b47ee36c6e9981078
```

```bash
git clone https://github.com/FlashML-org/FreeToken.git \
  ~/.cache/local-agent-controller/phase0/upstream/freetoken
git -C ~/.cache/local-agent-controller/phase0/upstream/freetoken \
  checkout --detach af71ba43206e124f5ff6419b47ee36c6e9981078
python3 scripts/verify_freetoken_pin.py
```

### Important runtime note

The accepted managed-runtime launcher expects the already-provisioned FreeToken environment and accepted model assets at the qualified local paths. rc.12 does not yet provide a one-command public bootstrap for those heavyweight runtime assets.

That is intentional: the controller will not silently substitute a model, FreeToken revision, CUDA environment, or runtime dependency when qualification-sensitive assets are missing.

You can still install and inspect goodLAC, run the permission demo, run static product checks, and use an externally managed qualified runtime where appropriate.

## 4. Build the deterministic rc.12 distribution

```bash
mkdir -p dist
python3 scripts/lac-v1 build \
  --output dist/local-agent-controller-1.0.0-rc.12.tar.gz
```

The distribution is built from the Git index, not arbitrary unstaged worktree bytes.

## 5. Install

```bash
python3 scripts/lac-v1 install \
  --archive dist/local-agent-controller-1.0.0-rc.12.tar.gz
```

The installer creates versioned user-level state under the `local-agent-controller` compatibility namespace and installs:

- `pi` - default-governed Pi entrypoint;
- `lac-pi` - compatibility alias;
- `lacctl` - owner administration client;
- `lac-owner` - bounded owner administration UX;
- `lac-config` - non-authoritative path/runtime configuration;
- `lac-doctor` - installation/prerequisite verifier.

## 6. Verify the installation

```bash
~/.local/bin/lac-doctor --static
```

After the qualified Pi, FreeToken and local-model runtime assets are provisioned:

```bash
~/.local/bin/lac-doctor
```

A complete managed-runtime installation should report `"ok": true`.

## 7. Launch governed Pi

From the project directory you want governed:

```bash
pi
```

The default rc.12 configuration uses launch-directory project identity unless the owner explicitly configures fixed workspace mode.

## Explicit dangerous bypass

rc.12 includes an owner/debug escape hatch:

```bash
pi --dangerously-bypass-lac ...
```

That path is explicitly **not governed by goodLAC**.

## Rollback

```bash
python3 ~/.local/share/local-agent-controller/current/app/scripts/lac-v1 rollback
```

## Security reporting

Do not post undisclosed vulnerabilities in a public issue or pull request.

Use GitHub Private Vulnerability Reporting through the repository Security interface:

https://github.com/itecob/goodLAC/security

See [`../SECURITY.md`](../SECURITY.md).

## More technical detail

- [`V1_PRODUCTIZATION.md`](V1_PRODUCTIZATION.md)
- [`PI_V1_GOVERNED_PROFILE.md`](PI_V1_GOVERNED_PROFILE.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`THREAT_MODEL.md`](THREAT_MODEL.md)
