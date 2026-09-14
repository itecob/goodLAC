#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

PIN = "af71ba43206e124f5ff6419b47ee36c6e9981078"
VERSION = "0.1.2"
LICENSE = "Apache-2.0"
REPO = "FlashML-org/FreeToken"
LICENSE_SHA256 = "1d28009bf66a66c90fa9c5561d9a73b7460ab611eeb3e90169d22a3b5a2a2326"
DEFAULT = Path.home() / ".cache/local-agent-controller/phase0/upstream/freetoken"
REPO_ROOT = Path(os.environ.get("LAC_REPO_ROOT", Path(__file__).resolve().parents[1])).expanduser().resolve()
checkout = Path(os.environ.get("LAC_FREETOKEN_CHECKOUT", str(DEFAULT))).expanduser().resolve()


def fail(message: str) -> None:
    raise SystemExit(f"LAC_A002_FREETOKEN_PIN_VERIFY=FAIL: {message}")


lock_path = REPO_ROOT / "UPSTREAM_LOCK.json"
if not lock_path.is_file():
    fail(f"missing upstream lock: {lock_path}")
try:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"cannot parse UPSTREAM_LOCK.json: {exc}")
upstreams = lock.get("upstreams")
if not isinstance(upstreams, list):
    fail("UPSTREAM_LOCK.json upstreams must be an array")
matches = [entry for entry in upstreams if isinstance(entry, dict) and entry.get("key") == "freetoken"]
if len(matches) != 1:
    fail(f"expected exactly one freetoken lock entry; observed {len(matches)}")
entry = matches[0]
expected = {
    "repo": REPO,
    "sha": PIN,
    "checkout_sha": PIN,
    "expected_license": LICENSE,
    "license_family": LICENSE,
    "observed_version": VERSION,
    "observed_stable_tag": "v0.1.2",
    "qualification_status": "PASS",
    "phase0_disposition": "PHASE3_MODEL_RUNTIME",
}
drift = {key: (expected_value, entry.get(key)) for key, expected_value in expected.items() if entry.get(key) != expected_value}
if drift:
    fail(f"FreeToken lock drift: {drift!r}")
if entry.get("license_sha256") != LICENSE_SHA256:
    fail("FreeToken license digest drift in lock")

if not (checkout / ".git").exists():
    fail(f"qualified FreeToken checkout missing: {checkout}")
try:
    head = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
    ).strip()
except subprocess.CalledProcessError as exc:
    fail(f"cannot read FreeToken checkout HEAD: {exc.output.strip()}")
if head != PIN:
    fail(f"FreeToken checkout drift: expected {PIN}, observed {head}")
tracked = subprocess.run(
    ["git", "-C", str(checkout), "diff", "--quiet", "HEAD", "--"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
if tracked.returncode != 0:
    fail("qualified FreeToken checkout has tracked-file modifications")

license_path = checkout / "LICENSE"
api_models_path = checkout / "python/freetoken/server/api_models.py"
openai_api_path = checkout / "python/freetoken/server/openai_api.py"
pyproject_path = checkout / "pyproject.toml"
version_path = checkout / "python/freetoken/version.py"
for path in (license_path, api_models_path, openai_api_path, pyproject_path, version_path):
    if not path.is_file():
        fail(f"required pinned FreeToken source missing: {path.relative_to(checkout)}")

digest = hashlib.sha256(license_path.read_bytes()).hexdigest()
if digest != LICENSE_SHA256:
    fail(f"FreeToken LICENSE digest drift: expected {LICENSE_SHA256}, observed {digest}")

pyproject = pyproject_path.read_text(encoding="utf-8")
version_source = version_path.read_text(encoding="utf-8")
if 'dynamic = ["version"]' not in pyproject or f'__version__ = "{VERSION}"' not in version_source:
    fail("FreeToken dynamic version source no longer matches qualified version")

api_models = api_models_path.read_text(encoding="utf-8")
openai_api = openai_api_path.read_text(encoding="utf-8")
required_model_contract = (
    "class ChatCompletionRequest(BaseModel):",
    "model: str",
    "messages: list[Message]",
    "max_tokens: int | None = None",
    "temperature: float | None = None",
    "top_k: int | None = None",
    "top_p: float | None = None",
    "stream: bool = False",
    "stream_options: StreamOptions | None = None",
    "reasoning_effort: str | None = None",
    "tools: list[Tool] | None = None",
    "tool_choice:",
    "response_format: dict[str, Any] | None = None",
)
missing = [needle for needle in required_model_contract if needle not in api_models]
if missing:
    fail(f"pinned ChatCompletionRequest interface drift: {missing!r}")
if "seed:" in api_models:
    fail("pinned interface unexpectedly gained seed; re-qualify instead of silently changing capability")
required_routes = (
    '@app.post("/v1/chat/completions")',
    '@app.get("/v1/models")',
    'media_type="text/event-stream"',
    'yield b"data: [DONE]\\n\\n"',
    "response_format json_object/json_schema is not supported",
)
missing_routes = [needle for needle in required_routes if needle not in openai_api]
if missing_routes:
    fail(f"pinned FreeToken endpoint interface drift: {missing_routes!r}")

print(f"LAC_A002_FREETOKEN_PIN={PIN}")
print(f"LAC_A002_FREETOKEN_VERSION={VERSION}")
print(f"LAC_A002_FREETOKEN_LICENSE={LICENSE}")
print("LAC_A002_FREETOKEN_SEED_CAPABILITY=UNSUPPORTED_FAIL_CLOSED")
print("LAC_A002_FREETOKEN_STRUCTURED_OUTPUT=UNSUPPORTED_FAIL_CLOSED")
print("LAC_A002_FREETOKEN_PIN_VERIFY=PASS")
