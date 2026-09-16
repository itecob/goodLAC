import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

import packages.adapters
from packages.admin import ADMIN_REQUEST_SCHEMA, AdminRequest, AdminService, UnixAdminServer
from packages.capabilities import CAPABILITY_MANIFEST_SCHEMA, CapabilityRequestContext
from packages.core import EffectRequest
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchCapabilityDenied,
    DispatchDenied,
    DispatchDuplicateEffect,
    Dispatcher,
)
from packages.effects.shell.adapter import _copy_binary_and_libraries
from packages.policy import StandingPolicyDecisionProvider, StandingPolicyRule
from packages.sandbox import NetworkMode, SandboxSpec, get_selected_backend
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    SQLiteStateStore,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LACCTL = REPO_ROOT / "scripts" / "lacctl"


def rfc3339(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def action_fixture(action_id, security_properties):
    return {
        "action": action_id,
        "resource": {"type": "document.local", "selectors": ["document:workspace"]},
        "arguments": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "minLength": 1, "maxLength": 128}
            },
            "required": ["document_id"],
            "additionalProperties": False,
        },
        "security_properties": security_properties,
    }


def manifest_fixture(actions):
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": actions,
    }


def request_fixture(name, action_id):
    now = datetime.now(timezone.utc)
    return EffectRequest.create(
        request_id=f"effect:p006:{name}",
        run_id="run:p006",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action_id,
        resource="document:workspace",
        arguments={"document_id": name},
        idempotency_key=f"idem:p006:{name}",
        created_at=rfc3339(now - timedelta(minutes=1)),
        expires_at=rfc3339(now + timedelta(minutes=30)),
    )


class CountingAdapter:
    adapter_id = "p006-test:v1"

    def __init__(self):
        self.support_calls = 0
        self.invoke_calls = 0

    def supports(self, request):
        self.support_calls += 1
        return True

    def invoke(self, request, *, lease):
        self.invoke_calls += 1
        return {"ok": True, "request_id": request.request_id}


class WrongUIDServer(UnixAdminServer):
    @staticmethod
    def _peer_identity(connection):
        return (os.getpid(), os.getuid() + 1, os.getgid())


class Harness:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.db_path = self.root / "controller.db"
        self.uid = os.getuid()
        self.store = None
        self.service = None
        self.server = None
        self.open()

    def open(self):
        self.store = SQLiteStateStore(self.db_path)
        EmergencyPauseRepository(self.store).resume()
        identities = AgentIdentityRepository(self.store)
        if identities.get("agent:test") is None:
            identities.register_active("agent:test", "principal:owner")
        self.service = AdminService(self.store, owner_uid=self.uid)
        self.server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        self.server.start()

    def close_runtime(self):
        if self.server is not None:
            self.server.close()
            self.server = None
        if self.store is not None:
            self.store.close()
            self.store = None
        self.service = None

    def restart(self):
        self.close_runtime()
        self.open()

    def cleanup(self):
        self.close_runtime()
        self.tmp.cleanup()

    def admin_call(self, operation, arguments):
        request = AdminRequest.create(
            request_id=f"admin:p006:{operation}:{len(json.dumps(arguments, sort_keys=True))}",
            operation=operation,
            arguments=arguments,
        )
        return self.service.execute(request, peer_uid=self.uid)

    def register(self, actions):
        return self.admin_call("skills.register", {"manifest": manifest_fixture(actions)})

    def context(self, revision):
        return CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=revision,
            manifest_version=1,
            resource_type="document.local",
        )

    def persist(self, request):
        return EffectRequestRepository(self.store).put(request)

    def dispatcher(self):
        return Dispatcher(
            store=self.store,
            policy_provider=StandingPolicyDecisionProvider(self.store),
            clock=lambda: datetime.now(timezone.utc),
        )

    def lacctl(self, *args):
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(self.runtime)
        process = subprocess.Popen(
            [sys.executable, str(LACCTL), *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        served = self.server.serve_once(timeout=4)
        try:
            stdout, stderr = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=2)
            raise AssertionError(
                f"lacctl subprocess timed out; stdout={stdout!r} stderr={stderr!r}"
            )
        if not served:
            raise AssertionError(
                f"admin server did not receive request; rc={process.returncode} "
                f"stdout={stdout!r} stderr={stderr!r}"
            )
        return subprocess.CompletedProcess(
            process.args, process.returncode, stdout=stdout, stderr=stderr
        )

    def lacctl_json(self, *args):
        result = self.lacctl("--json", *args)
        if result.returncode != 0:
            raise AssertionError(
                f"lacctl failed rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        if result.stderr:
            raise AssertionError(f"lacctl unexpected stderr={result.stderr!r}")
        return json.loads(result.stdout)

    def set_policy(self, *, rules):
        policy_file = self.root / "policy.json"
        policy_file.write_text(
            json.dumps(
                {"rules": [rule.to_material() for rule in rules], "defaults": []},
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        return self.lacctl_json("permissions", "set", "--file", str(policy_file))

    def table_counts(self):
        rows = self.store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        result = {}
        for row in rows:
            name = str(row["name"])
            quoted = '"' + name.replace('"', '""') + '"'
            result[name] = int(self.store._conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])
        return result

    def raw_transact(self, payload, *, server=None, tolerate_client_error=False):
        server = self.server if server is None else server
        result = {}
        errors = []

        def client():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                    conn.connect(str(server.socket_path))
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
            except OSError as exc:
                if tolerate_client_error:
                    result["client_errno"] = exc.errno
                else:
                    errors.append(exc)

        thread = threading.Thread(target=client)
        thread.start()
        served = server.serve_once(timeout=2.0)
        thread.join(timeout=2.0)
        if thread.is_alive():
            raise AssertionError("administrator client thread did not terminate")
        if errors:
            raise errors[0]
        if not served:
            raise AssertionError("administrator server did not receive raw request")
        return result.get("payload", b"")


class P006PermissionManagementE2ETests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.cleanup()

    def test_registration_zero_authority_and_deterministic_policy_precedence(self):
        registration = self.h.register(
            [
                action_fixture("document.read", ["read_only"]),
                action_fixture("document.write", ["local_mutation"]),
            ]
        )
        context = self.h.context(registration["revision"])

        skills = self.h.lacctl_json("skills", "list")
        self.assertEqual(len(skills["skills"]), 1)
        shown = self.h.lacctl_json("skills", "show", "test-app", "documents")
        self.assertEqual(shown["revision"], registration["revision"])

        zero_authority = request_fixture("zero-authority", "document.read")
        self.h.persist(zero_authority)
        adapter = CountingAdapter()
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                zero_authority,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006:zero-authority",
                lease_id="lease:p006:zero-authority",
                executor_id="executor:p006",
            )
        self.assertEqual(adapter.invoke_calls, 0)
        self.assertEqual(
            int(self.h.store._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]),
            0,
        )

        rules = [
            StandingPolicyRule.create(
                rule_id="broad-deny",
                application_id="test-app",
                decision="DENY",
            ),
            StandingPolicyRule.create(
                rule_id="specific-read-allow",
                application_id="test-app",
                skill_id="documents",
                action="document.read",
                decision="ALLOW",
            ),
            StandingPolicyRule.create(
                rule_id="write-allow",
                application_id="test-app",
                skill_id="documents",
                action="document.write",
                decision="ALLOW",
            ),
            StandingPolicyRule.create(
                rule_id="write-ask",
                application_id="test-app",
                skill_id="documents",
                action="document.write",
                decision="REQUIRE_APPROVAL",
            ),
            StandingPolicyRule.create(
                rule_id="write-deny",
                application_id="test-app",
                skill_id="documents",
                action="document.write",
                decision="DENY",
            ),
        ]
        replaced = self.h.set_policy(rules=rules)
        self.assertEqual(replaced["revision"], 1)
        listed = self.h.lacctl_json("permissions", "list")
        shown_policy = self.h.lacctl_json("permissions", "show", "--revision", "1")
        self.assertEqual(listed["policy_hash"], shown_policy["policy_hash"])

        allowed = request_fixture("specific-read", "document.read")
        self.h.persist(allowed)
        result = self.h.dispatcher().dispatch_capability(
            allowed,
            capability_context=context,
            adapter=adapter,
            decision_id="decision:p006:specific-read",
            lease_id="lease:p006:specific-read",
            executor_id="executor:p006",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(adapter.invoke_calls, 1)

        denied = request_fixture("equal-specificity-deny", "document.write")
        self.h.persist(denied)
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                denied,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006:write-conflict",
                lease_id="lease:p006:write-conflict",
                executor_id="executor:p006",
            )
        self.assertEqual(adapter.invoke_calls, 1)

    def test_closed_unknown_effect_never_revives_after_admin_changes_and_restart(self):
        registration = self.h.register([action_fixture("document.read", ["read_only"])])
        context1 = self.h.context(registration["revision"])
        closed = request_fixture("closed-delete", "document.delete")
        self.h.persist(closed)
        adapter = CountingAdapter()
        with self.assertRaises(DispatchCapabilityDenied):
            self.h.dispatcher().dispatch_capability(
                closed,
                capability_context=context1,
                adapter=adapter,
                decision_id="decision:p006:closed-initial",
                lease_id="lease:p006:closed-initial",
                executor_id="executor:p006",
            )
        self.assertEqual(adapter.invoke_calls, 0)
        pending = self.h.lacctl_json("pending", "list")["pending"]
        self.assertEqual(len(pending), 1)
        pending_id = pending[0]["pending_id"]

        newer = self.h.register(
            [
                action_fixture("document.read", ["read_only"]),
                action_fixture("document.delete", ["destructive", "local_mutation"]),
            ]
        )
        policy = self.h.set_policy(
            rules=[
                StandingPolicyRule.create(
                    rule_id="delete-allow",
                    application_id="test-app",
                    skill_id="documents",
                    action="document.delete",
                    decision="ALLOW",
                )
            ]
        )
        self.assertEqual(policy["revision"], 1)
        resolved = self.h.lacctl_json("pending", "resolve", pending_id, "POLICY_AND_CAPABILITY_UPDATED")
        self.assertEqual(resolved["resolution"]["status"], "RESOLVED")

        self.h.restart()
        shown_skill = self.h.lacctl_json("skills", "show", "test-app", "documents")
        self.assertEqual(shown_skill["revision"], newer["revision"])
        self.assertEqual(self.h.lacctl_json("permissions", "list")["revision"], 1)
        shown_pending = self.h.lacctl_json("pending", "show", pending_id)
        self.assertEqual(shown_pending["administrative_status"], "RESOLVED")

        context2 = self.h.context(newer["revision"])
        after_restart = CountingAdapter()
        with self.assertRaises(DispatchCapabilityDenied):
            self.h.dispatcher().dispatch_capability(
                closed,
                capability_context=context2,
                adapter=after_restart,
                decision_id="decision:p006:closed-later",
                lease_id="lease:p006:closed-later",
                executor_id="executor:p006",
            )
        self.assertEqual(after_restart.invoke_calls, 0)
        self.assertEqual(
            int(
                self.h.store._conn.execute(
                    "SELECT COUNT(*) FROM execution_leases WHERE request_id = ?",
                    (closed.request_id,),
                ).fetchone()[0]
            ),
            0,
        )

        fresh = request_fixture("fresh-delete", "document.delete")
        self.h.persist(fresh)
        result = self.h.dispatcher().dispatch_capability(
            fresh,
            capability_context=context2,
            adapter=after_restart,
            decision_id="decision:p006:fresh-delete",
            lease_id="lease:p006:fresh-delete",
            executor_id="executor:p006",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(after_restart.invoke_calls, 1)

    def test_exact_approval_is_admin_only_durable_rechecked_and_single_use(self):
        registration = self.h.register(
            [action_fixture("document.write", ["local_mutation"])]
        )
        context = self.h.context(registration["revision"])
        ask_rule = StandingPolicyRule.create(
            rule_id="write-ask",
            application_id="test-app",
            skill_id="documents",
            action="document.write",
            decision="REQUIRE_APPROVAL",
        )
        self.h.set_policy(rules=[ask_rule])

        request = request_fixture("approval-write", "document.write")
        self.h.persist(request)
        adapter = CountingAdapter()
        initial_decision = "decision:p006:approval-initial"
        with self.assertRaises(DispatchApprovalRequired):
            self.h.dispatcher().dispatch_capability(
                request,
                capability_context=context,
                adapter=adapter,
                decision_id=initial_decision,
                lease_id="lease:p006:approval-initial",
                executor_id="executor:p006",
            )
        self.assertEqual(adapter.invoke_calls, 0)
        self.assertEqual(
            int(
                self.h.store._conn.execute(
                    "SELECT COUNT(*) FROM execution_leases WHERE request_id = ?",
                    (request.request_id,),
                ).fetchone()[0]
            ),
            0,
        )

        candidate = self.h.lacctl_json("approvals", "show", initial_decision)
        self.assertIsNone(candidate["approval"])
        approved = self.h.lacctl_json("approvals", "approve", initial_decision)
        approval_id = approved["approval"]["approval_id"]
        self.assertEqual(approved["approval"]["decision"], "APPROVE")
        self.assertEqual(adapter.invoke_calls, 0)
        self.assertEqual(
            int(
                self.h.store._conn.execute(
                    "SELECT COUNT(*) FROM execution_leases WHERE request_id = ?",
                    (request.request_id,),
                ).fetchone()[0]
            ),
            0,
        )

        self.h.restart()
        durable = self.h.lacctl_json("approvals", "show", initial_decision)
        self.assertEqual(durable["approval"]["approval_id"], approval_id)

        deny_rule = StandingPolicyRule.create(
            rule_id="write-deny",
            application_id="test-app",
            skill_id="documents",
            action="document.write",
            decision="DENY",
        )
        self.h.set_policy(rules=[deny_rule])
        denied_adapter = CountingAdapter()
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                request,
                capability_context=context,
                adapter=denied_adapter,
                decision_id="decision:p006:approval-deny-recheck",
                lease_id="lease:p006:approval-deny-recheck",
                executor_id="executor:p006",
                approval_id=approval_id,
            )
        self.assertEqual(denied_adapter.invoke_calls, 0)
        self.assertIsNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)

        self.h.set_policy(rules=[ask_rule])
        result = self.h.dispatcher().dispatch_capability(
            request,
            capability_context=context,
            adapter=denied_adapter,
            decision_id="decision:p006:approval-current-ask",
            lease_id="lease:p006:approval-current-ask",
            executor_id="executor:p006",
            approval_id=approval_id,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(denied_adapter.invoke_calls, 1)
        self.assertIsNotNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)

        with self.assertRaises(DispatchDuplicateEffect):
            self.h.dispatcher().dispatch_capability(
                request,
                capability_context=context,
                adapter=denied_adapter,
                decision_id="decision:p006:approval-second",
                lease_id="lease:p006:approval-second",
                executor_id="executor:p006",
                approval_id=approval_id,
            )
        self.assertEqual(denied_adapter.invoke_calls, 1)

    def test_rejected_unavailable_and_malformed_admin_paths_do_not_mutate_state(self):
        self.assertEqual(stat.S_IMODE(self.h.server.socket_path.stat().st_mode), 0o600)
        self.assertEqual(self.h.server.socket_path.stat().st_uid, os.getuid())
        before = self.h.table_counts()

        malformed = b'{"schema":"lac.admin-request/v1","schema":"lac.admin-request/v1"}\n'
        response = self.h.raw_transact(malformed)
        self.assertIn(b"ADMIN_PROTOCOL_ERROR", response)
        self.assertEqual(self.h.table_counts(), before)

        unknown = (
            json.dumps(
                {
                    "schema": ADMIN_REQUEST_SCHEMA,
                    "request_id": "admin:p006:unsupported",
                    "operation": "unsupported.operation",
                    "arguments": {},
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        response = self.h.raw_transact(unknown)
        self.assertIn(b"ADMIN_PROTOCOL_ERROR", response)
        self.assertEqual(self.h.table_counts(), before)

        self.h.server.close()
        self.h.server = None
        policy_file = self.h.root / "unavailable-policy.json"
        policy_file.write_text('{"defaults":[],"rules":[]}', encoding="utf-8")
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(self.h.runtime)
        unavailable = subprocess.run(
            [sys.executable, str(LACCTL), "--json", "permissions", "set", "--file", str(policy_file)],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=6,
            check=False,
        )
        self.assertEqual(unavailable.returncode, 4, unavailable.stdout + unavailable.stderr)
        self.assertEqual(self.h.table_counts(), before)

        wrong = WrongUIDServer(self.h.service, runtime_dir=self.h.runtime)
        wrong.start()
        try:
            payload = (
                json.dumps(
                    {
                        "schema": ADMIN_REQUEST_SCHEMA,
                        "request_id": "admin:p006:wrong-uid",
                        "operation": "skills.register",
                        "arguments": {
                            "manifest": manifest_fixture(
                                [action_fixture("document.read", ["read_only"])]
                            )
                        },
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            )
            self.h.raw_transact(payload, server=wrong, tolerate_client_error=True)
            self.assertEqual(self.h.table_counts(), before)
        finally:
            wrong.close()

        self.h.server = UnixAdminServer(self.h.service, runtime_dir=self.h.runtime)
        self.h.server.start()

    def test_governed_runtime_and_sandbox_cannot_reach_admin_surface(self):
        self.assertFalse(hasattr(packages.adapters, "AdminService"))
        self.assertFalse(hasattr(Dispatcher, "admin"))
        self.assertFalse(hasattr(Dispatcher, "replace_policy_admin"))
        worker = (REPO_ROOT / "scripts" / "a003_agent_sandbox.py").read_text(encoding="utf-8")
        self.assertNotIn("admin-v1.sock", worker)
        self.assertNotIn("packages.admin", worker)

        self.assertTrue(self.h.server.socket_path.is_socket())
        rootfs = self.h.root / "sandbox-root"
        for rel in ("proc", "dev", "tmp"):
            (rootfs / rel).mkdir(parents=True, exist_ok=True)
        test_binary = Path("/usr/bin/test").resolve(strict=True)
        _copy_binary_and_libraries(test_binary, rootfs)
        backend = get_selected_backend()
        spec = SandboxSpec(
            runtime_root=rootfs,
            instance_id="p006-admin-boundary",
            mounts=(),
            environment={"HOME": "/nonexistent", "LC_ALL": "C", "PATH": "/usr/bin"},
            cwd=PurePosixPath("/"),
            network=NetworkMode.NONE,
        )
        completed = backend.run(
            spec,
            [str(test_binary), "-S", str(self.h.server.socket_path)],
            timeout=5,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(self.h.server.socket_path.is_socket())


if __name__ == "__main__":
    unittest.main()
