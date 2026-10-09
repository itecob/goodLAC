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

The full managed local-model path additionally requires the exact qualified Pi and FreeToken checkouts plus the accepted local model/runtime assets. The accepted FreeToken runtime path requires an NVIDIA CUDA 13 toolkit with `nvcc` available and was qualified against the pinned FreeToken source described below.

goodLAC fails closed rather than silently downloading, upgrading, or substituting qualification-sensitive runtime dependencies.

`lac-doctor --static` validates the installed product and system-level prerequisites. Full `lac-doctor` additionally validates the pinned upstream checkouts, the pinned Pi source dependency needed by the launcher, and—in managed mode—the FreeToken CLI, `ninja`, exact model snapshot and CUDA 13 toolkit. A managed endpoint does not have to be running before doctor succeeds because goodLAC can start the exact qualified endpoint on demand.

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

Install the pinned checkout's JavaScript dependencies using the upstream instruction for that exact revision:

```bash
npm --prefix ~/.cache/local-agent-controller/phase0/upstream/pi \
  install --ignore-scripts
```

Then verify that Node itself satisfies Pi's requirement:

```bash
node --version
```

The version must be **22.19.0 or newer**. Do not substitute a different Pi revision.

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

### Provision the accepted managed FreeToken environment

The managed launcher expects its FreeToken virtual environment at this exact compatibility path:

```text
~/.cache/local-agent-controller/a003/freetoken-af71ba43206e124f5ff6419b47ee36c6e9981078
```

After the pinned checkout above has been verified, create that environment from the pinned source:

```bash
FT_PIN="af71ba43206e124f5ff6419b47ee36c6e9981078"
FT_CHECKOUT="$HOME/.cache/local-agent-controller/phase0/upstream/freetoken"
FT_VENV="$HOME/.cache/local-agent-controller/a003/freetoken-$FT_PIN"

python3 -m venv "$FT_VENV"
"$FT_VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$FT_VENV/bin/python" -m pip install -e "$FT_CHECKOUT[accel]"
"$FT_VENV/bin/python" -m pip install ninja

"$FT_VENV/bin/ft" --version
"$FT_VENV/bin/ninja" --version
```

The pinned FreeToken source declares Linux x86_64, an NVIDIA GPU, driver support for CUDA 13, Python `>=3.10`, and CUDA 13 `nvcc` for JIT-compiled kernels. Install the NVIDIA driver/CUDA toolkit through the supported mechanism for your Linux distribution; goodLAC does not install or modify GPU drivers or the system CUDA toolkit.

Verify:

```bash
nvcc --version
```

The reported toolkit release must be CUDA **13.x**.

### Provision the exact qualified GPT-OSS model snapshot

The default rc.12 managed route is qualified against:

```text
repository: openai/gpt-oss-20b
revision:   6cee5e81ee83917806bbde320786a8fb61efebee
served id:  lac-a003-gpt-oss-20b
endpoint:   http://127.0.0.1:19203
```

This is a large model download. Start it only when you intend to provision the managed reference runtime:

```bash
FT_PIN="af71ba43206e124f5ff6419b47ee36c6e9981078"
FT_VENV="$HOME/.cache/local-agent-controller/a003/freetoken-$FT_PIN"

HF_HOME="$HOME/.cache/huggingface" \
"$FT_VENV/bin/python" - <<'PY'
from huggingface_hub import snapshot_download

path = snapshot_download(
    repo_id="openai/gpt-oss-20b",
    revision="6cee5e81ee83917806bbde320786a8fb61efebee",
)
print(path)
PY
```

The managed launcher will not download or substitute a different model at launch time.

The qualified snapshot must therefore exist at:

```text
~/.cache/huggingface/hub/models--openai--gpt-oss-20b/snapshots/6cee5e81ee83917806bbde320786a8fb61efebee
```

and contain `config.json`.

### Qwen route status in rc.12

rc.12 also contains the bounded Qwen comparison route used during qualification, including the model selector route around `127.0.0.1:19360`. It is evidence that the route was tested; it is **not** the default managed public bootstrap and this installation guide does not claim to provision its model assets automatically.

The reproducible public reference path for this release is the GPT-OSS managed route above. Future removal of model/runtime/harness coupling is a post-rc.12 architecture item and is not implemented by these installation instructions.

### Important runtime boundary

The controller does not silently substitute a model, FreeToken revision, CUDA environment, or runtime dependency when qualification-sensitive assets are missing. Missing or inconsistent managed assets fail closed.

You can still install and inspect goodLAC, run the permission demo, run static product checks, or configure `runtime=external` when you deliberately operate a separately managed compatible endpoint.

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
