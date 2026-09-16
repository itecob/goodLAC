#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

A003_IMPLEMENTATION = "809bb01ec52e6f04d96f22c0195c47961b3efd7a"
A004_IMPLEMENTATION = "94c7db928b3848069d2a7c432316db0d88477871"
A004_REMEDIATION = "c930cacbd1260f24477e8fb16056f463f9a3c306"
A004_UAT_COMMIT = "8aab0f39e84dcb627c394df4811d565fae054002"
PI_PIN = "da840b6216578c2a571d0374ac6a2091a83f9d91"
FREETOKEN_PIN = "af71ba43206e124f5ff6419b47ee36c6e9981078"
MODEL_REVISION = "6cee5e81ee83917806bbde320786a8fb61efebee"
MODEL_ID = "lac-a003-gpt-oss-20b"
EXPECTED_TOOLS = ["lac_fs_read", "lac_fs_create", "lac_fs_replace", "lac_shell_exec"]


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(rel: str) -> dict:
    path = REPO_ROOT / rel
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{rel} must contain a JSON object")
    return value


def sha256_file(rel: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()


def require_ancestor(commit: str, label: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", commit, "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"accepted {label} commit is not in live Git ancestry: {commit}")


def require_all_pass(mapping: object, label: str) -> None:
    if not isinstance(mapping, dict) or not mapping:
        fail(f"{label} must be a non-empty object")
    bad = {str(k): v for k, v in mapping.items() if v != "PASS"}
    if bad:
        fail(f"{label} contains non-PASS values: {bad!r}")


def verify_a003() -> None:
    require_ancestor(A003_IMPLEMENTATION, "A003")
    owner = load_json("qualification/evidence/a003_owner_execution.json")
    if owner.get("schema") != "lac.a003-owner-execution/v2" or owner.get("result") != "PASS":
        fail("A003 owner execution evidence is not accepted PASS material")
    if owner.get("implementation_commit") != A003_IMPLEMENTATION:
        fail("A003 owner evidence implementation commit mismatch")
    require_all_pass(owner.get("acceptance"), "A003 acceptance")

    pi = owner.get("pi")
    freetoken = owner.get("freetoken")
    model = owner.get("model")
    if not isinstance(pi, dict) or pi.get("pin") != PI_PIN:
        fail("A003 accepted Pi pin mismatch")
    if not isinstance(freetoken, dict) or freetoken.get("pin") != FREETOKEN_PIN or freetoken.get("version") != "0.1.2":
        fail("A003 accepted FreeToken pin/version mismatch")
    if not isinstance(model, dict) or model.get("revision") != MODEL_REVISION or model.get("served_model_id") != MODEL_ID:
        fail("A003 accepted model identity mismatch")

    summary_rel = owner.get("evidence_summary")
    sandbox_rel = owner.get("agent_sandbox_evidence")
    if not isinstance(summary_rel, str) or not isinstance(sandbox_rel, str):
        fail("A003 owner evidence paths are malformed")
    if sha256_file(summary_rel) != owner.get("evidence_summary_sha256"):
        fail("A003 evidence summary hash mismatch")
    if sha256_file(sandbox_rel) != owner.get("agent_sandbox_evidence_sha256"):
        fail("A003 sandbox evidence hash mismatch")

    summary = load_json(summary_rel)
    if summary.get("schema") != "lac.a003-evidence-summary/v1" or summary.get("result") != "PASS":
        fail("A003 evidence summary is not PASS")
    if summary.get("tool_surface") != EXPECTED_TOOLS:
        fail("A003 accepted tool surface changed")
    positive = summary.get("positive")
    adversarial = summary.get("adversarial")
    if not isinstance(positive, dict) or positive.get("successful_effects") != 3:
        fail("A003 positive accepted evidence does not prove exactly three successful governed effects")
    receipt_ids = positive.get("receipt_ids")
    if not isinstance(receipt_ids, list) or len(receipt_ids) != 3 or any(not isinstance(x, str) or not x for x in receipt_ids):
        fail("A003 positive accepted receipt evidence is malformed")
    if not isinstance(adversarial, dict):
        fail("A003 adversarial accepted evidence is malformed")
    if adversarial.get("policy_decision") != "ALLOW" or adversarial.get("effect_outcome") != "FAILED":
        fail("A003 adversarial accepted evidence no longer proves OS/effect-boundary failure under ALLOW")
    if adversarial.get("secret_bytes_observed") is not False:
        fail("A003 accepted evidence indicates secret bytes were observed")

    sandbox = load_json(sandbox_rel)
    if sandbox.get("schema") != "lac.a003-agent-sandbox-evidence/v1" or sandbox.get("result") != "PASS":
        fail("A003 accepted sandbox evidence is not PASS")
    if sandbox.get("tool_surface") != EXPECTED_TOOLS:
        fail("A003 accepted sandbox tool surface changed")
    probes = sandbox.get("probes")
    for key in (
        "host_file_readable",
        "workspace_file_readable",
        "workspace_write_effect",
        "synthetic_service_credential_inherited",
        "arbitrary_host_executable_launched",
        "loopback_connected",
        "private_network_connected",
    ):
        if not isinstance(probes, dict) or probes.get(key) is not False:
            fail(f"A003 accepted sandbox evidence fails closed check: {key}")

    runtime = load_json("qualification/evidence/a003_runtime.json")
    runtime_ft = runtime.get("freetoken")
    runtime_model = runtime.get("model")
    runtime_pi = runtime.get("pi")
    if not isinstance(runtime_ft, dict) or runtime_ft.get("git_commit") != FREETOKEN_PIN:
        fail("A003 runtime evidence does not bind the accepted FreeToken commit")
    if not isinstance(runtime_model, dict) or runtime_model.get("revision") != MODEL_REVISION or runtime_model.get("served_model_id") != MODEL_ID:
        fail("A003 runtime evidence does not bind the accepted model snapshot")
    if not isinstance(runtime_pi, dict) or runtime_pi.get("git_commit") != PI_PIN:
        fail("A003 runtime evidence does not bind the accepted Pi commit")
    print("LAC_A003_ACCEPTED_LIVE_EVIDENCE=PASS")


def verify_a004() -> None:
    require_ancestor(A004_IMPLEMENTATION, "A004 implementation")
    require_ancestor(A004_REMEDIATION, "A004 remediation")
    require_ancestor(A004_UAT_COMMIT, "A004 owner UAT")

    owner = load_json("qualification/evidence/a004_owner_execution.json")
    if owner.get("schema") != "lac.a004-owner-execution/v1" or owner.get("result") != "PASS":
        fail("A004 owner execution evidence is not accepted PASS material")
    if owner.get("implementation_commit") != A004_IMPLEMENTATION:
        fail("A004 implementation commit mismatch")
    require_all_pass(owner.get("acceptance"), "A004 acceptance")
    pins = owner.get("pins")
    if not isinstance(pins, dict):
        fail("A004 pin material is malformed")
    expected_pins = {
        "pi_commit": PI_PIN,
        "freetoken_commit": FREETOKEN_PIN,
        "model_revision": MODEL_REVISION,
        "served_model_id": MODEL_ID,
        "sandbox_backend": "bubblewrap",
    }
    for key, expected in expected_pins.items():
        if pins.get(key) != expected:
            fail(f"A004 accepted pin mismatch for {key}")

    revalidation = load_json("qualification/evidence/a004_owner_uat_revalidation.json")
    if revalidation.get("schema") != "lac.a004-owner-uat-revalidation/v1" or revalidation.get("result") != "PASS":
        fail("A004 owner UAT revalidation is not PASS")
    if revalidation.get("owner_acceptance") is not True:
        fail("A004 owner UAT acceptance is not true")
    if revalidation.get("remediation_implementation_commit") != A004_REMEDIATION:
        fail("A004 UAT remediation commit mismatch")
    require_all_pass(revalidation.get("owner_observations"), "A004 owner observations")

    handoff = load_json("qualification/evidence/a004_uat_handoff_execution.json")
    if handoff.get("schema") != "lac.a004-uat-handoff-execution/v1" or handoff.get("result") != "PASS":
        fail("A004 UAT handoff evidence is not PASS")
    if handoff.get("owner_uat_commit") != A004_UAT_COMMIT or handoff.get("remediation_commit") != A004_REMEDIATION:
        fail("A004 UAT handoff commit binding mismatch")
    if handoff.get("blockers") != []:
        fail("A004 UAT handoff contains blockers")
    print("LAC_A004_ACCEPTED_LIVE_EVIDENCE=PASS")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify immutable accepted A003/A004 live evidence for deterministic later-phase regression"
    )
    parser.add_argument("--scope", choices=("a003", "a004", "all"), default="all")
    args = parser.parse_args()
    if args.scope in {"a003", "all"}:
        verify_a003()
    if args.scope in {"a004", "all"}:
        verify_a004()
    print("LAC_ACCEPTED_LIVE_EVIDENCE_VERIFY=PASS")


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        print(f"LAC_ACCEPTED_LIVE_EVIDENCE_VERIFY=FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
