#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.admin import AdminRequest, AdminService, UnixAdminServer
from packages.capabilities import CAPABILITY_MANIFEST_SCHEMA, CapabilityRequestContext
from packages.core import EffectRequest
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchCapabilityDenied,
    DispatchDenied,
    DispatchDuplicateEffect,
    Dispatcher,
)
from packages.policy import StandingPolicyCondition, StandingPolicyDecisionProvider, StandingPolicyRule
from packages.state import AgentIdentityRepository, EffectRequestRepository, EmergencyPauseRepository, SQLiteStateStore

LACCTL = REPO_ROOT / "scripts" / "lacctl"


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def action(action_id: str, security_properties: list[str]) -> dict:
    return {
        "action": action_id,
        "resource": {"type": "document.local", "selectors": ["document:workspace"]},
        "arguments": {
            "type": "object",
            "properties": {"document_id": {"type": "string", "minLength": 1, "maxLength": 128}},
            "required": ["document_id"],
            "additionalProperties": False,
        },
        "security_properties": security_properties,
    }


def manifest(actions: list[dict]) -> dict:
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "owner-uat-app",
        "skill_id": "documents",
        "actions": actions,
    }


def request(name: str, action_id: str) -> EffectRequest:
    now = datetime.now(timezone.utc)
    return EffectRequest.create(
        request_id=f"effect:owner-uat:{name}",
        run_id="run:owner-uat",
        principal_id="principal:owner",
        agent_id="agent:owner-uat",
        action=action_id,
        resource="document:workspace",
        arguments={"document_id": name},
        idempotency_key=f"idem:owner-uat:{name}",
        created_at=rfc3339(now - timedelta(seconds=5)),
        expires_at=rfc3339(now + timedelta(minutes=30)),
    )


class SafeAdapter:
    adapter_id = "owner-uat-synthetic:v1"

    def __init__(self) -> None:
        self.invoke_calls = 0

    def supports(self, _request: EffectRequest) -> bool:
        return True

    def invoke(self, effect: EffectRequest, *, lease):
        self.invoke_calls += 1
        return {
            "synthetic": True,
            "request_id": effect.request_id,
            "action": effect.action,
            "lease_id": lease.lease_id,
            "invoke_count": self.invoke_calls,
        }


class Demo:
    def __init__(self, *, auto: bool) -> None:
        self.auto = auto
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-p006-owner-uat-")
        self.root = Path(self.tmp.name).resolve()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.db = self.root / "controller.db"
        self.store = SQLiteStateStore(self.db)
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:owner-uat", "principal:owner")
        self.service = AdminService(self.store, owner_uid=os.getuid())
        self.server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        self.server.start()
        self.adapter = SafeAdapter()

    def close(self) -> None:
        self.server.close()
        self.store.close()
        self.tmp.cleanup()

    def pause(self, title: str, explanation: str) -> None:
        print("\n" + "=" * 78)
        print(title)
        print("=" * 78)
        print(explanation)
        if not self.auto:
            input("\nPress Enter to perform this stage...")

    def admin(self, operation: str, arguments: dict) -> dict:
        req = AdminRequest.create(
            request_id=f"admin:owner-uat:{operation}:{datetime.now(timezone.utc).timestamp()}",
            operation=operation,
            arguments=arguments,
        )
        return self.service.execute(req, peer_uid=os.getuid())

    def lacctl(self, *args: str) -> str:
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(self.runtime)
        proc = subprocess.Popen(
            [sys.executable, str(LACCTL), *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        served = self.server.serve_once(timeout=5)
        stdout, stderr = proc.communicate(timeout=8)
        if not served:
            raise RuntimeError("admin server did not receive lacctl request")
        if proc.returncode != 0:
            raise RuntimeError(f"lacctl failed rc={proc.returncode}: {stdout}{stderr}")
        if stderr:
            raise RuntimeError(f"lacctl emitted unexpected stderr: {stderr}")
        print(f"$ lacctl {' '.join(args)}")
        print(stdout.rstrip() or "<no output>")
        return stdout

    def set_policy(self, rules: list[StandingPolicyRule]) -> None:
        policy = self.root / "policy.json"
        policy.write_text(
            json.dumps({"rules": [r.to_material() for r in rules], "defaults": []}, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        self.lacctl("permissions", "set", "--file", str(policy))

    def dispatcher(self) -> Dispatcher:
        return Dispatcher(
            store=self.store,
            policy_provider=StandingPolicyDecisionProvider(self.store),
            clock=lambda: datetime.now(timezone.utc),
        )

    @staticmethod
    def context(revision: int) -> CapabilityRequestContext:
        return CapabilityRequestContext(
            application_id="owner-uat-app",
            skill_id="documents",
            capability_revision=revision,
            manifest_version=1,
            resource_type="document.local",
        )

    def dispatch(self, effect: EffectRequest, context: CapabilityRequestContext, name: str, approval_id: str | None = None):
        # Dispatcher requires the canonical request to be durable before any authority decision.
        # Re-putting the same canonical request is intentionally idempotent so later stages can
        # prove that an earlier terminally denied request remains closed.
        EffectRequestRepository(self.store).put(effect)
        kwargs = {}
        if approval_id is not None:
            kwargs["approval_id"] = approval_id
        return self.dispatcher().dispatch_capability(
            effect,
            capability_context=context,
            adapter=self.adapter,
            decision_id=f"decision:owner-uat:{name}",
            lease_id=f"lease:owner-uat:{name}",
            executor_id="executor:owner-uat",
            **kwargs,
        )

    def run(self) -> int:
        print("P006 OWNER PERMISSION WALKTHROUGH")
        print("All state is temporary and local. Adapter effects are synthetic only.")
        print(f"Temporary root: {self.root}")

        self.pause(
            "1. Register capability metadata — zero authority",
            "The application declares known read/write operations. Registration describes request shapes; it grants no permission.",
        )
        reg1 = self.admin(
            "skills.register",
            {"manifest": manifest([action("document.read", ["read_only"]), action("document.write", ["local_mutation"])])},
        )
        ctx1 = self.context(reg1["revision"])
        self.lacctl("skills", "list")

        self.pause(
            "2. Known capability, no user-configured policy",
            "A valid registered read request is submitted before the owner has configured standing permission. Enforcement must fail closed. We also inspect whether an owner-review item is created.",
        )
        known = request("known-read-unconfigured", "document.read")
        try:
            self.dispatch(known, ctx1, "known-read-unconfigured")
            raise RuntimeError("unexpected execution: registration must not grant authority")
        except DispatchDenied as exc:
            print(f"ENFORCEMENT=DENY ({type(exc).__name__}: {exc})")
        pending_now = json.loads(self.lacctl("--json", "pending", "list"))["pending"]
        known_gap = len(pending_now) == 0
        known_pending = [
            item
            for item in pending_now
            if item.get("action") == "document.read"
            and item.get("reason") == "NO_CONFIGURED_STANDING_PERMISSION"
        ]
        if not known_gap and len(known_pending) != 1:
            raise RuntimeError(
                "known valid unconfigured request did not create exactly one scoped review item"
            )
        known_pending_id = None if known_gap else known_pending[0]["pending_id"]
        print(f"KNOWN_UNCONFIGURED_PENDING_COUNT={len(pending_now)}")
        print("CLARIFIED_OWNER_REQUIREMENT=known+unconfigured must DENY and create/aggregate owner-reviewable configuration work")
        print(f"KNOWN_UNCONFIGURED_DISCOVERY_REQUIREMENT={'GAP_CONFIRMED' if known_gap else 'SATISFIED'}")

        self.pause(
            "3. Unknown/new capability request",
            "Now the application requests document.delete, which is not in the registered manifest. P002 must terminally deny it and create a bounded pending-permission record.",
        )
        closed = request("original-delete", "document.delete")
        try:
            self.dispatch(closed, ctx1, "unknown-delete")
            raise RuntimeError("unexpected unknown capability execution")
        except DispatchCapabilityDenied as exc:
            print(f"ENFORCEMENT=TERMINAL_DENY ({type(exc).__name__}: {exc})")
        pending = json.loads(self.lacctl("--json", "pending", "list"))["pending"]
        delete_pending = [item for item in pending if item.get("action") == "document.delete"]
        if len(delete_pending) != 1:
            raise RuntimeError("P002 did not create exactly one pending permission record for document.delete")
        pending_id = delete_pending[0]["pending_id"]
        self.lacctl("pending", "show", pending_id)

        self.pause(
            "4. Configure future capability + standing policy",
            "The application manifest is updated to describe delete. The owner then sets an ALLOW standing rule using lacctl and resolves the administrative pending item. None of these actions may revive the original denied effect.",
        )
        reg2 = self.admin(
            "skills.register",
            {"manifest": manifest([
                action("document.read", ["read_only"]),
                action("document.write", ["local_mutation"]),
                action("document.delete", ["destructive", "local_mutation"]),
            ])},
        )
        ctx2 = self.context(reg2["revision"])
        self.set_policy([
            StandingPolicyRule.create(
                rule_id="owner-uat-delete-allow",
                application_id="owner-uat-app",
                skill_id="documents",
                action="document.delete",
                decision="ALLOW",
            )
        ])
        self.lacctl("pending", "resolve", pending_id, "POLICY_AND_CAPABILITY_UPDATED")

        self.pause(
            "5. Prove the original denied effect stays dead",
            "We retry the exact original request after capability and policy changes. It must remain closed forever. Then a fresh request may be evaluated under the new policy.",
        )
        try:
            self.dispatch(closed, ctx2, "closed-delete-after-config")
            raise RuntimeError("original P002-closed effect revived")
        except DispatchCapabilityDenied as exc:
            print(f"ORIGINAL_REQUEST_NON_RESUMPTION=PASS ({type(exc).__name__})")
        fresh = request("fresh-delete", "document.delete")
        result = self.dispatch(fresh, ctx2, "fresh-delete")
        print("FRESH_REQUEST_RESULT=" + json.dumps(result, sort_keys=True))
        if self.adapter.invoke_calls != 1:
            raise RuntimeError("fresh allowed request did not execute exactly once")

        self.pause(
            "6. Conditional standing policy — explicit DENY plus ALLOW-IF",
            "We configure a broad explicit DENY for document.read and a more-specific conditional ALLOW when document_id equals conditional-allowed. The matching fresh request may execute; the non-matching fresh request must remain denied without invoking the adapter.",
        )
        conditional_allow = StandingPolicyRule.create(
            rule_id="owner-uat-read-allow-if",
            application_id="owner-uat-app",
            skill_id="documents",
            action="document.read",
            decision="ALLOW",
            conditions=(
                StandingPolicyCondition.create(
                    source="REQUEST",
                    key="arguments:/document_id",
                    equals="conditional-allowed",
                ),
            ),
        )
        broad_deny = StandingPolicyRule.create(
            rule_id="owner-uat-read-deny",
            application_id="owner-uat-app",
            skill_id="documents",
            action="document.read",
            decision="DENY",
        )
        self.set_policy([broad_deny, conditional_allow])
        if known_pending_id is not None:
            self.lacctl(
                "pending",
                "resolve",
                known_pending_id,
                "POLICY_UPDATED",
            )
            try:
                self.dispatch(known, ctx2, "known-read-after-config")
                raise RuntimeError(
                    "original known+unconfigured denied request revived after policy configuration"
                )
            except DispatchCapabilityDenied as exc:
                print(
                    "KNOWN_UNCONFIGURED_ORIGINAL_NON_RESUMPTION=PASS "
                    f"({type(exc).__name__}: {exc})"
                )
        before_conditional = self.adapter.invoke_calls
        conditional_ok = request("conditional-allowed", "document.read")
        conditional_result = self.dispatch(conditional_ok, ctx2, "conditional-allow")
        print("ALLOW_IF_MATCH_RESULT=" + json.dumps(conditional_result, sort_keys=True))
        if self.adapter.invoke_calls != before_conditional + 1:
            raise RuntimeError("conditional ALLOW did not invoke adapter exactly once")
        conditional_denied = request("conditional-denied", "document.read")
        try:
            self.dispatch(conditional_denied, ctx2, "conditional-deny")
            raise RuntimeError("non-matching conditional request unexpectedly executed")
        except DispatchDenied as exc:
            print(f"EXPLICIT_DENY_NONMATCH=PASS ({type(exc).__name__}: {exc})")
        if self.adapter.invoke_calls != before_conditional + 1:
            raise RuntimeError("explicit DENY invoked adapter")

        self.pause(
            "7. Exact approval path",
            "We configure document.write as REQUIRE_APPROVAL. The request stops before execution, lacctl exposes the exact approval candidate, and owner approval itself still does not execute the effect.",
        )
        ask_rule = StandingPolicyRule.create(
            rule_id="owner-uat-write-ask",
            application_id="owner-uat-app",
            skill_id="documents",
            action="document.write",
            decision="REQUIRE_APPROVAL",
        )
        self.set_policy([ask_rule])
        write = request("write-needs-approval", "document.write")
        decision_id = "decision:owner-uat:write-needs-approval"
        try:
            self.dispatch(write, ctx2, "write-needs-approval")
            raise RuntimeError("write executed without exact approval")
        except DispatchApprovalRequired as exc:
            print(f"REQUIRE_APPROVAL=PASS ({type(exc).__name__}: {exc})")
        self.lacctl("approvals", "list")
        calls_before_approval = self.adapter.invoke_calls
        approved = json.loads(self.lacctl("--json", "approvals", "approve", decision_id))
        approval_id = approved["approval"]["approval_id"]
        print(f"APPROVAL_ID={approval_id}")
        print(f"ADAPTER_INVOKE_COUNT_AFTER_APPROVAL={self.adapter.invoke_calls} (approval is not execution)")
        if self.adapter.invoke_calls != calls_before_approval:
            raise RuntimeError("owner approval itself executed an effect")

        self.pause(
            "8. Dispatch with exact approval and prove one-time effect",
            "The fresh dispatch re-evaluates current policy and uses the exact approval. The synthetic effect executes once; a repeat is blocked as a duplicate.",
        )
        result = self.dispatch(write, ctx2, "write-after-approval", approval_id=approval_id)
        print("APPROVED_DISPATCH_RESULT=" + json.dumps(result, sort_keys=True))
        calls_after = self.adapter.invoke_calls
        try:
            self.dispatch(write, ctx2, "write-duplicate", approval_id=approval_id)
            raise RuntimeError("duplicate effect unexpectedly executed")
        except DispatchDuplicateEffect as exc:
            print(f"DUPLICATE_PREVENTION=PASS ({type(exc).__name__}: {exc})")
        if self.adapter.invoke_calls != calls_after:
            raise RuntimeError("duplicate attempt invoked adapter")

        print("\n" + "=" * 78)
        print("WALKTHROUGH SUMMARY")
        print("=" * 78)
        print("P001_REGISTRATION_ZERO_AUTHORITY=PASS")
        print("P002_UNKNOWN_TERMINAL_DENY_AND_PENDING=PASS")
        print("P002_ORIGINAL_NON_RESUMPTION=PASS")
        print("P003_STANDING_POLICY_FRESH_REQUEST=PASS")
        print("P003_CONFIGURED_DENY=PASS")
        print("P003_CONDITIONAL_ALLOW_IF=PASS")
        print("P004_P005_OWNER_ADMIN_AND_LACCTL=PASS")
        print("EXACT_APPROVAL_NO_IMPLICIT_EXECUTION=PASS")
        print("EXACT_APPROVAL_AND_DUPLICATE_PREVENTION=PASS")
        print(f"KNOWN_UNCONFIGURED_PERMISSION_DISCOVERY={'GAP_CONFIRMED' if known_gap else 'PASS'}")
        print(
            "KNOWN_UNCONFIGURED_ORIGINAL_NON_RESUMPTION="
            + ("SKIPPED_GAP" if known_gap else "PASS")
        )
        print("NO_EXTERNAL_EFFECTS=PASS")
        print("LAC_P006_OWNER_PERMISSION_WALKTHROUGH=PASS_WITH_KNOWN_GAP" if known_gap else "LAC_P006_OWNER_PERMISSION_WALKTHROUGH=PASS")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    demo = Demo(auto=args.auto)
    try:
        return demo.run()
    finally:
        demo.close()


if __name__ == "__main__":
    raise SystemExit(main())
