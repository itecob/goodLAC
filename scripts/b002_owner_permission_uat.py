#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from packages.admin import AdminRequest, AdminService, UnixAdminServer
from packages.capabilities import CapabilityRequestContext
from packages.core import EffectRequest
from packages.dispatcher import DispatchApprovalRequired, DispatchCapabilityDenied, DispatchDenied, Dispatcher
from packages.effects.calendar import (
    CALENDAR_CREATE_ACTION,
    CALENDAR_RESOURCE_TYPE,
    CalendarEffectAdapter,
    calendar_capability_manifest,
)
from packages.effects.shell.adapter import _copy_binary_and_libraries
from packages.policy import StandingPolicyDecisionProvider, StandingPolicyRule
from packages.sandbox import NetworkMode, SandboxSpec, get_selected_backend
from packages.state import AgentIdentityRepository, EffectRequestRepository, EmergencyPauseRepository, SQLiteStateStore

LACCTL = REPO / "scripts" / "lacctl"
APP = "b002-owner-uat"
RESOURCE = "calendar:primary"
PRINCIPAL = "principal:owner"
AGENT = "agent:b002-calendar-uat"
CANARY = "SYNTHETIC_B002_OWNER_UAT_NOT_A_REAL_CREDENTIAL"
FIRST_USE_CHOICES = {
    "1": "ALWAYS_ALLOW",
    "2": "ASK_EACH_TIME",
    "3": "NOT_NOW",
    "4": "ALWAYS_DENY",
}
EXACT_CHOICES = {"1": "ALLOW_ONCE", "2": "DENY_ONCE"}


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def event_material(number: int) -> dict:
    return {
        "title": f"B002 owner UAT synthetic event {number}",
        "start": "2026-10-01T13:00:00-04:00",
        "end": "2026-10-01T14:00:00-04:00",
        "timezone": "America/Toronto",
        "attendees": ["owner@example.com"],
        "location": "Synthetic local fixture only",
        "recurrence": [],
        "conference_settings": {"enabled": False, "solution_type": "hangoutsMeet"},
        "send_updates": "none",
    }


def effect(skill: str, number: int, label: str) -> EffectRequest:
    now = datetime.now(timezone.utc)
    return EffectRequest.create(
        request_id=f"effect:b002-owner:{skill}:{label}",
        run_id="run:b002-owner-uat",
        principal_id=PRINCIPAL,
        agent_id=AGENT,
        action=CALENDAR_CREATE_ACTION,
        resource=RESOURCE,
        arguments=event_material(number),
        idempotency_key=f"idem:b002-owner:{skill}:{label}",
        created_at=rfc3339(now - timedelta(seconds=2)),
        expires_at=rfc3339(now + timedelta(hours=2)),
    )


class SyntheticSecrets:
    def __init__(self): self.calls = []
    def resolve(self, ref):
        self.calls.append(ref)
        return CANARY


class SyntheticTransport:
    def __init__(self):
        self.invoke_count = 0
        self.mutations = {}
    def search(self, **kwargs): return {"events": []}
    def read(self, *, event_id): return {"event": {"id": event_id}}
    def create(self, *, event, request_id, idempotency_key):
        key = (CALENDAR_CREATE_ACTION, request_id, idempotency_key)
        if key in self.mutations: raise RuntimeError("duplicate synthetic Calendar create")
        self.invoke_count += 1
        result = {
            "event": {"id": f"owner-uat-{self.invoke_count}", "title": event["title"]},
            "upstream_reference": f"synthetic-calendar:event:{self.invoke_count}",
        }
        self.mutations[key] = result
        return result
    def modify(self, **kwargs): raise RuntimeError("not used in owner UAT")
    def cancel(self, **kwargs): raise RuntimeError("not used in owner UAT")
    def reconcile(self, *, action, request_id, idempotency_key, operation):
        return self.mutations.get((action, request_id, idempotency_key))


class Factory:
    def __init__(self, transport): self.transport = transport
    def create(self, *, calendar_resource, secret):
        if calendar_resource != RESOURCE or secret != CANARY:
            raise RuntimeError("unexpected synthetic Calendar credential capability")
        return self.transport


class UAT:
    def __init__(self, evidence_file: Path):
        self.evidence_file = evidence_file
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-b002-owner-uat-")
        self.root = Path(self.tmp.name).resolve()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.db = self.root / "controller.db"
        self.uid = os.getuid()
        self.store = None
        self.service = None
        self.server = None
        self.rules: list[StandingPolicyRule] = []
        self.secrets = SyntheticSecrets()
        self.transport = SyntheticTransport()
        self.adapter = CalendarEffectAdapter(secret_provider=self.secrets, transport_factory=Factory(self.transport))
        self.first_use_coverage: set[str] = set()
        self.exact_coverage: set[str] = set()
        self.first_use_records: list[dict[str, str]] = []
        self.exact_records: list[dict[str, str]] = []
        self.restart_checks = 0
        self.open_runtime()

    def open_runtime(self):
        self.store = SQLiteStateStore(self.db)
        EmergencyPauseRepository(self.store).resume()
        identities = AgentIdentityRepository(self.store)
        if identities.get(AGENT) is None:
            identities.register_active(AGENT, PRINCIPAL)
        self.service = AdminService(self.store, owner_uid=self.uid)
        self.server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        self.server.start()

    def close_runtime(self):
        if self.server is not None:
            self.server.close(); self.server = None
        if self.store is not None:
            self.store.close(); self.store = None
        self.service = None

    def restart(self):
        self.close_runtime()
        self.open_runtime()
        self.restart_checks += 1

    def close(self):
        self.close_runtime()
        self.tmp.cleanup()

    def admin(self, operation: str, arguments: dict) -> dict:
        req = AdminRequest.create(
            request_id=f"admin:b002-owner:{operation}:{datetime.now(timezone.utc).timestamp()}",
            operation=operation,
            arguments=arguments,
        )
        payload = (json.dumps(req.to_material(), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        result: dict[str, object] = {}
        errors: list[BaseException] = []

        def client():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                    conn.connect(str(self.server.socket_path))
                    conn.sendall(payload)
                    chunks = []
                    while True:
                        part = conn.recv(65536)
                        if not part:
                            break
                        chunks.append(part)
                        if b"\n" in part:
                            break
                    result["payload"] = b"".join(chunks)
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=client)
        thread.start()
        served = self.server.serve_once(timeout=5)
        thread.join(timeout=5)
        if thread.is_alive() or not served or errors:
            raise RuntimeError(f"P004 admin transport failed: served={served} errors={errors}")
        response = json.loads(bytes(result.get("payload", b"")).decode("utf-8"))
        if response.get("ok") is not True:
            raise RuntimeError("P004 admin request was rejected: " + json.dumps(response, sort_keys=True))
        return response["result"]

    def lacctl(self, *args: str) -> dict:
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(self.runtime)
        proc = subprocess.Popen(
            [sys.executable, str(LACCTL), "--json", *args], cwd=REPO, env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        served = self.server.serve_once(timeout=5)
        stdout, stderr = proc.communicate(timeout=8)
        if not served or proc.returncode != 0 or stderr:
            raise RuntimeError(f"lacctl failed: served={served} rc={proc.returncode} stdout={stdout!r} stderr={stderr!r}")
        payload = json.loads(stdout)
        if isinstance(payload, dict) and payload.get("ok") is False:
            raise RuntimeError("lacctl returned an error: " + stdout)
        return payload

    def set_policy(self):
        policy = self.root / "policy.json"
        policy.write_text(
            json.dumps({"rules": [r.to_material() for r in self.rules], "defaults": []}, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        self.lacctl("permissions", "set", "--file", str(policy))

    def context(self, revision: int, skill: str) -> CapabilityRequestContext:
        return CapabilityRequestContext(
            application_id=APP, skill_id=skill, capability_revision=revision,
            manifest_version=1, resource_type=CALENDAR_RESOURCE_TYPE,
        )

    def dispatcher(self):
        return Dispatcher(store=self.store, policy_provider=StandingPolicyDecisionProvider(self.store), clock=lambda: datetime.now(timezone.utc))

    def dispatch(self, req: EffectRequest, context: CapabilityRequestContext, label: str, approval_id: str | None = None):
        EffectRequestRepository(self.store).put(req)
        kwargs = {} if approval_id is None else {"approval_id": approval_id}
        return self.dispatcher().dispatch_capability(
            req, capability_context=context, adapter=self.adapter,
            decision_id=f"decision:b002-owner:{label}", lease_id=f"lease:b002-owner:{label}",
            executor_id="executor:b002-owner-uat", **kwargs,
        )

    def find_pending(self, skill: str):
        rows = self.lacctl("pending", "list")["pending"]
        matches = [x for x in rows if x.get("application_id") == APP and x.get("skill_id") == skill and x.get("action") == CALENDAR_CREATE_ACTION and x.get("reason") == "NO_CONFIGURED_STANDING_PERMISSION"]
        if len(matches) != 1:
            raise RuntimeError(f"expected one Calendar first-use review item for {skill}; found {len(matches)}")
        return matches[0]

    def first_use(self, skill: str, number: int, context: CapabilityRequestContext):
        original = effect(skill, number, "original")
        before = self.transport.invoke_count
        secret_before = len(self.secrets.calls)
        try:
            self.dispatch(original, context, f"{skill}:original")
            raise RuntimeError("unconfigured Calendar request unexpectedly executed")
        except DispatchDenied:
            pass
        if self.transport.invoke_count != before or len(self.secrets.calls) != secret_before:
            raise RuntimeError("unconfigured request reached Calendar adapter credentials/effect")
        lease_count = int(self.store._conn.execute("SELECT COUNT(*) FROM execution_leases WHERE request_id=?", (original.request_id,)).fetchone()[0])
        if lease_count != 0:
            raise RuntimeError("unconfigured request acquired an execution lease")
        pending = self.find_pending(skill)
        return original, pending

    def assert_original_closed(self, original: EffectRequest, context: CapabilityRequestContext, label: str):
        before = self.transport.invoke_count
        try:
            self.dispatch(original, context, label)
            raise RuntimeError("original first-use request resumed after administration")
        except DispatchCapabilityDenied:
            pass
        if self.transport.invoke_count != before:
            raise RuntimeError("closed original request reached Calendar adapter")

    def prompt_first_use(self, skill: str, pending: dict) -> str:
        remaining = {k: v for k, v in FIRST_USE_CHOICES.items() if v not in self.first_use_coverage}
        print("\nFIRST-USE POLICY PROMPT")
        print(f"  application: {APP}")
        print(f"  skill:       {skill}")
        print(f"  action:      {CALENDAR_CREATE_ACTION}")
        print(f"  resource:    {RESOURCE}")
        print("  properties:  credential_sensitive, external_communication, external_mutation, network_egress")
        print("  request:     canonical synthetic event fields are bound; raw credential material is absent")
        print(f"  review item: {pending['pending_id']}")
        print("\nChoose a permission outcome yourself. This harness does not select it for you.")
        labels = {
            "ALWAYS_ALLOW":"Always allow",
            "ASK_EACH_TIME":"Ask me each time",
            "NOT_NOW":"Not now",
            "ALWAYS_DENY":"Always deny",
        }
        for key, value in remaining.items():
            print(f"  {key}. {labels[value]}")
        while True:
            answer = input("Selection: ").strip()
            if answer in remaining:
                choice = remaining[answer]
                self.first_use_coverage.add(choice)
                self.first_use_records.append({"skill_id": skill, "choice": choice})
                return choice
            print("Enter one of the displayed numbers.")

    def policy_rule(self, skill: str, decision: str) -> StandingPolicyRule:
        return StandingPolicyRule.create(
            rule_id=f"b002-owner-{skill}-{decision.lower()}", application_id=APP, skill_id=skill,
            action=CALENDAR_CREATE_ACTION, resource_selector=RESOURCE, decision=decision,
        )

    def handle_allow(self, skill, number, context, original, pending):
        self.rules.append(self.policy_rule(skill, "ALLOW")); self.set_policy()
        self.lacctl("pending", "resolve", pending["pending_id"], "POLICY_UPDATED")
        self.assert_original_closed(original, context, f"{skill}:closed-after-allow")
        fresh = effect(skill, number, "allow-fresh")
        before = self.transport.invoke_count
        self.dispatch(fresh, context, f"{skill}:allow-fresh")
        if self.transport.invoke_count != before + 1: raise RuntimeError("Always allow fresh request did not execute once")
        self.restart()
        durable = effect(skill, number, "allow-after-restart")
        before = self.transport.invoke_count
        self.dispatch(durable, context, f"{skill}:allow-after-restart")
        if self.transport.invoke_count != before + 1: raise RuntimeError("Always allow was not durable across restart")
        print("ALWAYS_ALLOW=PASS")

    def handle_deny(self, skill, number, context, original, pending):
        self.rules.append(self.policy_rule(skill, "DENY")); self.set_policy()
        self.lacctl("pending", "resolve", pending["pending_id"], "POLICY_UPDATED")
        self.assert_original_closed(original, context, f"{skill}:closed-after-deny")
        count_before = self.lacctl("pending", "show", pending["pending_id"])["count"]
        fresh = effect(skill, number, "deny-fresh")
        before = self.transport.invoke_count
        try: self.dispatch(fresh, context, f"{skill}:deny-fresh"); raise RuntimeError("Always deny fresh request executed")
        except DispatchDenied: pass
        if self.transport.invoke_count != before: raise RuntimeError("Always deny reached adapter")
        count_after = self.lacctl("pending", "show", pending["pending_id"])["count"]
        if count_after != count_before: raise RuntimeError("configured DENY generated recurring discovery noise")
        self.restart()
        another = effect(skill, number, "deny-after-restart")
        try: self.dispatch(another, context, f"{skill}:deny-after-restart"); raise RuntimeError("Always deny was not durable")
        except DispatchDenied: pass
        print("ALWAYS_DENY=PASS")

    def handle_not_now(self, skill, number, context, original, pending):
        self.assert_original_closed(original, context, f"{skill}:closed-not-now")
        count_before = pending["count"]
        self.restart()
        fresh = effect(skill, number, "not-now-fresh")
        before = self.transport.invoke_count
        try: self.dispatch(fresh, context, f"{skill}:not-now-fresh"); raise RuntimeError("Not now fresh request executed")
        except DispatchDenied: pass
        if self.transport.invoke_count != before: raise RuntimeError("Not now reached adapter")
        after = self.find_pending(skill)
        if after["count"] <= count_before: raise RuntimeError("Not now did not leave future unconfigured request reviewable")
        print("NOT_NOW=PASS")

    def prompt_exact(self, req: EffectRequest) -> str:
        remaining = {k: v for k, v in EXACT_CHOICES.items() if v not in self.exact_coverage}
        print("\nEXACT EFFECT PROMPT")
        print(f"  request_id: {req.request_id}")
        print(f"  action:     {req.action}")
        print(f"  resource:   {req.resource}")
        print(f"  hash:       {req.canonical_hash}")
        print("  exact arguments:")
        print(json.dumps(req.arguments, sort_keys=True, indent=2))
        labels = {"ALLOW_ONCE":"Allow once", "DENY_ONCE":"Deny once"}
        for key, value in remaining.items(): print(f"  {key}. {labels[value]}")
        while True:
            answer = input("Selection: ").strip()
            if answer in remaining:
                choice = remaining[answer]
                self.exact_coverage.add(choice)
                self.exact_records.append({"request_id": req.request_id, "canonical_hash": req.canonical_hash, "choice": choice})
                return choice
            print("Enter one of the displayed numbers.")

    def ask_once(self, skill: str, number: int, context: CapabilityRequestContext, sub: int):
        req = effect(skill, number, f"ask-{sub}")
        decision_id = f"decision:b002-owner:{skill}:ask-{sub}"
        before = self.transport.invoke_count
        try:
            self.dispatch(req, context, f"{skill}:ask-{sub}")
            raise RuntimeError("Ask me each time executed without exact approval")
        except DispatchApprovalRequired:
            pass
        if self.transport.invoke_count != before: raise RuntimeError("approval candidate executed an effect")
        shown = self.lacctl("approvals", "show", decision_id)
        if shown["request"]["canonical_hash"] != req.canonical_hash:
            raise RuntimeError("exact approval candidate does not bind displayed Calendar request")
        choice = self.prompt_exact(req)
        if choice == "ALLOW_ONCE":
            approved = self.lacctl("approvals", "approve", decision_id)
            approval_id = approved["approval"]["approval_id"]
            if self.transport.invoke_count != before: raise RuntimeError("approval itself executed Calendar effect")
            self.restart()
            durable = self.lacctl("approvals", "show", decision_id)
            if durable["approval"]["decision"] != "APPROVE": raise RuntimeError("Allow once was not durable")
            self.dispatch(req, context, f"{skill}:allow-once-dispatch-{sub}", approval_id=approval_id)
            if self.transport.invoke_count != before + 1: raise RuntimeError("Allow once did not execute exact request once")
            print("ALLOW_ONCE=PASS")
        else:
            rejected = self.lacctl("approvals", "reject", decision_id)
            if rejected["approval"]["decision"] != "REJECT": raise RuntimeError("Deny once did not persist rejection")
            self.restart()
            durable = self.lacctl("approvals", "show", decision_id)
            if durable["approval"]["decision"] != "REJECT": raise RuntimeError("Deny once was not durable")
            if self.transport.invoke_count != before: raise RuntimeError("Deny once executed an effect")
            print("DENY_ONCE=PASS")
        follow = effect(skill, number, f"ask-follow-{sub}")
        before_follow = self.transport.invoke_count
        try:
            self.dispatch(follow, context, f"{skill}:ask-follow-{sub}")
            raise RuntimeError("Ask me each time did not ask again for a fresh request")
        except DispatchApprovalRequired:
            pass
        if self.transport.invoke_count != before_follow: raise RuntimeError("fresh Ask request executed before approval")
        print("ASK_AGAIN_FOR_FRESH_REQUEST=PASS")

    def handle_ask(self, skill, number, context, original, pending):
        self.rules.append(self.policy_rule(skill, "REQUIRE_APPROVAL")); self.set_policy()
        self.lacctl("pending", "resolve", pending["pending_id"], "POLICY_UPDATED")
        self.assert_original_closed(original, context, f"{skill}:closed-after-ask")
        self.restart()
        sub = 1
        while self.exact_coverage != set(EXACT_CHOICES.values()):
            self.ask_once(skill, number, context, sub)
            sub += 1
        print("ASK_EACH_TIME=PASS")

    def verify_credential_canary_absent_from_durable_state(self):
        needle = CANARY.encode("utf-8")
        for candidate in (self.db, Path(str(self.db) + "-wal"), Path(str(self.db) + "-shm")):
            if candidate.exists() and needle in candidate.read_bytes():
                raise RuntimeError(f"synthetic credential canary leaked into durable controller state: {candidate.name}")
        print("CREDENTIAL_CANARY_IN_DURABLE_STATE=ABSENT")

    def verify_admin_socket_isolation(self):
        if not self.server.socket_path.is_socket(): raise RuntimeError("owner admin socket is unavailable")
        rootfs = self.root / "sandbox-root"
        for rel in ("proc", "dev", "tmp"): (rootfs / rel).mkdir(parents=True, exist_ok=True)
        test_binary = Path("/usr/bin/test").resolve(strict=True)
        _copy_binary_and_libraries(test_binary, rootfs)
        backend = get_selected_backend()
        spec = SandboxSpec(
            runtime_root=rootfs, instance_id="b002-owner-admin-isolation", mounts=(),
            environment={"HOME":"/nonexistent","LC_ALL":"C","PATH":"/usr/bin"},
            cwd=PurePosixPath("/"), network=NetworkMode.NONE,
        )
        completed = backend.run(spec, [str(test_binary), "-S", str(self.server.socket_path)], timeout=5, check=False)
        if completed.returncode == 0: raise RuntimeError("governed sandbox can see owner admin socket")
        print("GOVERNED_CONSUMER_ADMIN_SOCKET_VISIBILITY=ABSENT")

    def run(self):
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise RuntimeError("B002 owner UAT requires an interactive terminal; choices may not be piped or auto-selected")
        print("B002 CALENDAR OWNER PERMISSION UAT")
        print("This uses isolated local SQLite state, synthetic Calendar transport, and a synthetic credential canary.")
        print("No production Google credential or consequential external Calendar effect is used.")
        print("You must personally exercise all four first-use permission choices and both exact-effect choices.\n")

        round_no = 1
        while self.first_use_coverage != set(FIRST_USE_CHOICES.values()):
            skill = f"calendar-uat-{round_no}"
            registration = self.admin("skills.register", {"manifest": calendar_capability_manifest(application_id=APP, skill_id=skill)})
            context = self.context(registration["revision"], skill)
            original, pending = self.first_use(skill, round_no, context)
            choice = self.prompt_first_use(skill, pending)
            if choice == "ALWAYS_ALLOW": self.handle_allow(skill, round_no, context, original, pending)
            elif choice == "ASK_EACH_TIME": self.handle_ask(skill, round_no, context, original, pending)
            elif choice == "NOT_NOW": self.handle_not_now(skill, round_no, context, original, pending)
            elif choice == "ALWAYS_DENY": self.handle_deny(skill, round_no, context, original, pending)
            else: raise RuntimeError("unknown owner choice")
            round_no += 1

        if self.exact_coverage != set(EXACT_CHOICES.values()):
            raise RuntimeError("Ask me each time was not exercised with both Allow once and Deny once")
        self.verify_credential_canary_absent_from_durable_state()
        self.verify_admin_socket_isolation()
        self.restart()
        policy = self.lacctl("permissions", "list")
        if policy.get("revision", 0) < 3:
            raise RuntimeError("standing permission decisions were not durably revisioned")

        evidence = {
            "schema":"lac.b002-owner-uat/v1",
            "result":"PASS",
            "completed_at_utc":rfc3339(datetime.now(timezone.utc)),
            "first_use_choices":sorted(self.first_use_coverage),
            "exact_effect_choices":sorted(self.exact_coverage),
            "first_use_records":self.first_use_records,
            "exact_effect_records":self.exact_records,
            "first_use_unconfigured_enforcement":"DENY",
            "original_first_use_non_resumable":True,
            "explicit_configured_deny_discovery_noise":"NONE",
            "permission_choices_durable_across_restart":True,
            "restart_checks":self.restart_checks,
            "governed_consumer_admin_socket_visibility":"ABSENT",
            "calendar_transport":"SYNTHETIC_LOCAL_ONLY",
            "production_calendar_credentials":"NONE",
            "credential_canary_in_durable_state":"ABSENT",
            "external_effects":"NONE_SYNTHETIC_LOCAL_FIXTURES_ONLY",
            "adapter_mutation_count":self.transport.invoke_count,
        }
        self.evidence_file.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_file.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print("\nB002_OWNER_PERMISSION_UAT=PASS")
        print("EVIDENCE=" + str(self.evidence_file))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-file", required=True)
    args = parser.parse_args()
    uat = UAT(Path(args.evidence_file).resolve())
    try:
        uat.run()
        return 0
    finally:
        uat.close()

if __name__ == "__main__":
    raise SystemExit(main())
