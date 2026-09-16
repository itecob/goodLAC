import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from packages.admin import AdminRequest, AdminService, UnixAdminServer
from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityRequestContext,
    CapabilityRequestDenied,
    CapabilityRequestValidator,
    PendingPermissionRepository,
)
from packages.core import EffectRequest, PolicyDecision, PolicyDecisionValue
from packages.policy import StandingPolicyDefault, StandingPolicyRule
from packages.state import EffectRequestRepository, PolicyDecisionRepository, SQLiteStateStore

REPO_ROOT = Path(__file__).resolve().parents[2]
LACCTL = REPO_ROOT / "scripts" / "lacctl"


def rfc3339(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def action(action_id, properties):
    return {
        "action": action_id,
        "resource": {"type": "document.local", "selectors": ["document:workspace"]},
        "arguments": {
            "type": "object",
            "properties": {"document_id": {"type": "string", "minLength": 1, "maxLength": 128}},
            "required": ["document_id"],
            "additionalProperties": False,
        },
        "security_properties": properties,
    }


def manifest():
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": [action("document.read", ["read_only"])],
    }


class LacctlAdminApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.state = SQLiteStateStore(self.root / "controller.db")
        self.uid = os.getuid()
        self.service = AdminService(self.state, owner_uid=self.uid)
        self.server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        self.server.start()
        self.registration = self.admin_call("skills.register", {"manifest": manifest()})
        self._seed_pending()
        self._seed_approvals()

    def tearDown(self):
        self.server.close()
        self.state.close()
        self.tmp.cleanup()

    def admin_call(self, operation, arguments):
        request = AdminRequest.create(
            request_id=f"seed:{operation}:{len(json.dumps(arguments, sort_keys=True))}",
            operation=operation,
            arguments=arguments,
        )
        return self.service.execute(request, peer_uid=self.uid)

    def _seed_pending(self):
        now = datetime.now(timezone.utc)
        validator = CapabilityRequestValidator(self.state)
        context = CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=self.registration["revision"],
            manifest_version=1,
            resource_type="document.local",
        )
        for index, unknown_action in enumerate(("document.delete", "document.share"), start=1):
            request = EffectRequest.create(
                request_id=f"effect:p005:pending:{index}",
                run_id="run:p005",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=unknown_action,
                resource="document:workspace",
                arguments={"document_id": f"doc-{index}"},
                idempotency_key=f"idem:p005:pending:{index}",
                created_at=rfc3339(now - timedelta(minutes=1)),
                expires_at=rfc3339(now + timedelta(minutes=20)),
            )
            EffectRequestRepository(self.state).put(request)
            with self.assertRaises(CapabilityRequestDenied):
                validator.validate_or_quarantine(request, context=context, observed_at_utc=rfc3339(now))
        self.pending_ids = [item["pending_id"] for item in PendingPermissionRepository(self.state).list_pending()]

    def _seed_approvals(self):
        now = datetime.now(timezone.utc)
        self.decision_ids = []
        for index in (1, 2):
            request = EffectRequest.create(
                request_id=f"effect:p005:approval:{index}",
                run_id="run:p005",
                principal_id="principal:owner",
                agent_id="agent:test",
                action="document.write",
                resource="document:workspace",
                arguments={"document_id": f"approval-{index}"},
                idempotency_key=f"idem:p005:approval:{index}",
                created_at=rfc3339(now - timedelta(minutes=2)),
                expires_at=rfc3339(now + timedelta(minutes=20)),
            )
            EffectRequestRepository(self.state).put(request)
            decision = PolicyDecision.create(
                decision_id=f"decision:p005:approval:{index}",
                request_id=request.request_id,
                decision=PolicyDecisionValue.REQUIRE_APPROVAL,
                policy_revision="standing-policy:p005",
                reason_codes=("P005_SYNTHETIC_APPROVAL",),
                evaluated_at=rfc3339(now - timedelta(minutes=1)),
                canonical_request_hash=request.canonical_hash,
            )
            PolicyDecisionRepository(self.state).put(decision)
            self.decision_ids.append(decision.decision_id)

    def lacctl(self, *args):
        # Keep UnixAdminServer/AdminService execution on the thread that owns the
        # SQLiteStateStore connection. Only the real CLI client runs out-of-process,
        # matching the accepted P004 transport-test topology.
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
            self.fail(f"lacctl subprocess timed out; stdout={stdout!r} stderr={stderr!r}")
        self.assertTrue(
            served,
            f"admin server did not receive one request; rc={process.returncode} "
            f"stdout={stdout!r} stderr={stderr!r}",
        )
        return subprocess.CompletedProcess(
            process.args, process.returncode, stdout=stdout, stderr=stderr
        )

    def assert_json_success(self, *args):
        result = self.lacctl("--json", *args)
        self.assertEqual(
            result.returncode,
            0,
            f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_skills_list_and_show_use_p004_only(self):
        listed = self.assert_json_success("skills", "list")
        self.assertEqual(len(listed["skills"]), 1)
        shown = self.assert_json_success("skills", "show", "test-app", "documents")
        self.assertEqual(shown["application_id"], "test-app")
        self.assertEqual(shown["skill_id"], "documents")
        human = self.lacctl("skills", "list")
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("APPLICATION_ID\tSKILL_ID\tREVISION", human.stdout)

    def test_permissions_set_list_show_and_revoke_round_trip(self):
        rule = StandingPolicyRule.create(
            rule_id="documents-read",
            application_id="test-app",
            skill_id="documents",
            action="document.read",
            decision="ALLOW",
        )
        default = StandingPolicyDefault.create(
            default_id="documents-default",
            application_id="test-app",
            skill_id="documents",
            decision="REQUIRE_APPROVAL",
        )
        policy_file = self.root / "policy.json"
        policy_file.write_text(
            json.dumps(
                {"rules": [rule.to_material()], "defaults": [default.to_material()]},
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        replaced = self.assert_json_success("permissions", "set", "--file", str(policy_file))
        self.assertEqual(replaced["revision"], 1)
        listed = self.assert_json_success("permissions", "list")
        self.assertEqual(listed["rules"][0]["rule_id"], "documents-read")
        shown = self.assert_json_success("permissions", "show", "--revision", "1")
        self.assertEqual(shown["revision"], 1)
        revoked = self.assert_json_success("permissions", "revoke", "rule", "documents-read")
        self.assertEqual(revoked["revision"], 2)
        self.assertEqual(revoked["rules"], [])

    def test_pending_list_show_resolve_and_dismiss_are_administration_only(self):
        listed = self.assert_json_success("pending", "list")
        self.assertEqual(len(listed["pending"]), 2)
        shown = self.assert_json_success("pending", "show", self.pending_ids[0])
        self.assertEqual(shown["administrative_status"], "PENDING")
        resolved = self.assert_json_success(
            "pending", "resolve", self.pending_ids[0], "NO_CHANGE"
        )
        self.assertEqual(resolved["resolution"]["status"], "RESOLVED")
        dismissed = self.assert_json_success("pending", "dismiss", self.pending_ids[1])
        self.assertEqual(dismissed["resolution"]["status"], "DISMISSED")
        # P002 closure remains durable: administration dispositions do not reopen effects.
        closures = self.state._conn.execute(
            "SELECT COUNT(*) FROM system_state WHERE key LIKE 'capability_denial.request.%'"
        ).fetchone()[0]
        self.assertEqual(int(closures), 2)

    def test_approvals_list_show_approve_and_reject_wrap_exact_approval_repository(self):
        listed = self.assert_json_success("approvals", "list")
        self.assertEqual(len(listed["approvals"]), 2)
        shown = self.assert_json_success("approvals", "show", self.decision_ids[0])
        self.assertIsNone(shown["approval"])
        approved = self.assert_json_success("approvals", "approve", self.decision_ids[0])
        self.assertEqual(approved["approval"]["decision"], "APPROVE")
        rejected = self.assert_json_success("approvals", "reject", self.decision_ids[1])
        self.assertEqual(rejected["approval"]["decision"], "REJECT")
        self.assertEqual(
            int(self.state._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
