from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminRequest, AdminService
from packages.capabilities import PendingPermissionRepository
from packages.policy import StandingPolicyRule
from packages.runtime import (
    NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA,
    NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA,
    ExternalConsumerDeclaration,
    ExternalConsumerProtocolError,
    ExternalConsumerRuntime,
    NativeLocalConsumerContractError,
    NativeLocalConsumerRuntime,
    parse_native_resume_request,
)
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "pi003_native_consumer_fixture.py"


class CountingAdapter:
    adapter_id = "pi003-notes:v1"

    def __init__(self):
        self.invoke_calls = 0

    def supports(self, request):
        return request.action == "notes.write" and request.resource == "notes:workspace"

    def invoke(self, request, *, lease):
        self.invoke_calls += 1
        return {
            "schema": "pi003.notes-result/v1",
            "request_id": request.request_id,
            "note_id": request.arguments["note_id"],
            "content": request.arguments["content"],
            "synthetic": True,
        }


class Harness:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-pi003-")
        self.root = Path(self.tmp.name)
        self.store = SQLiteStateStore(self.root / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:pi003", "principal:owner")
        self.admin = AdminService(self.store, owner_uid=os.getuid())
        self.adapter = CountingAdapter()
        self.manifest = self.fixture_json("declare")
        self.declaration = ExternalConsumerDeclaration.create(self.manifest)
        self.authority = ExternalConsumerRuntime(
            store=self.store,
            declaration=self.declaration,
            principal_id="principal:owner",
            agent_id="agent:pi003",
            application_id="pi003-native-fixture",
            skill_id="notes",
            adapter=self.adapter,
        )
        self.consumer = NativeLocalConsumerRuntime(
            store=self.store,
            authority_runtime=self.authority,
        )

    def close(self):
        self.store.close()
        self.tmp.cleanup()

    def fixture_json(self, *args, input_value=None):
        proc = subprocess.run(
            [sys.executable, str(FIXTURE), *args],
            cwd=REPO_ROOT,
            input=None if input_value is None else json.dumps(input_value),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=True,
        )
        return json.loads(proc.stdout)

    def request(self, name, *, content=None):
        return self.fixture_json(
            "request",
            "--request-id", f"effect:pi003:{name}",
            "--note-id", name,
            "--content", content if content is not None else name,
            "--idempotency-key", f"idem:pi003:{name}",
        )

    def admin_call(self, operation, arguments):
        req = AdminRequest.create(
            request_id=f"admin:pi003:{operation}:{os.urandom(6).hex()}",
            operation=operation,
            arguments=arguments,
        )
        return self.admin.execute(req, peer_uid=os.getuid())

    def register(self, manifest=None):
        return self.admin_call("skills.register", {"manifest": manifest or self.manifest})

    def set_policy(self, decision, *, application_id="pi003-native-fixture", skill_id="notes"):
        rule = StandingPolicyRule.create(
            rule_id=f"pi003-{application_id}-{skill_id}-{decision.lower()}",
            application_id=application_id,
            skill_id=skill_id,
            action="notes.write",
            resource_selector="notes:workspace",
            decision=decision,
        )
        return self.admin_call(
            "permissions.replace", {"rules": [rule.to_material()], "defaults": []}
        )

    def resolve(self, pending_id, resolution="POLICY_UPDATED"):
        return self.admin_call(
            "pending.resolve", {"pending_id": pending_id, "resolution": resolution}
        )


class NativeConsumerContractTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.h.register()

    def tearDown(self):
        self.h.close()

    def test_stdlib_fixture_exercises_neutral_result_status_and_one_fresh_request(self):
        source = FIXTURE.read_text(encoding="utf-8")
        self.assertNotIn("from packages", source)
        self.assertNotIn("import packages", source)
        self.assertNotIn("lacctl", source.lower())

        request = self.h.request("fresh", content="captured")
        first = self.h.consumer.submit(request)
        self.assertEqual(first["schema"], NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA)
        self.assertEqual(first["authority_outcome"], "DENY")
        self.assertTrue(first["permission_configuration"]["required"])
        status = first["workflow_continuation"]
        self.assertEqual(status["schema"], NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA)
        self.assertEqual(status["state"], "WAITING_PERMISSION")
        self.assertEqual(status["resume_budget_used"], 0)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        for command, material, marker in (
            ("consume-result", first, "PI003_NATIVE_FIXTURE_RESULT=PASS"),
            ("consume-status", status, "PI003_NATIVE_FIXTURE_STATUS=PASS"),
        ):
            proc = subprocess.run(
                [sys.executable, str(FIXTURE), command],
                cwd=REPO_ROOT,
                input=json.dumps(material),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=True,
            )
            self.assertIn(marker, proc.stdout)

        original_request_id = first["request_id"]
        self.h.set_policy("ALLOW")
        self.h.resolve(status["pending_id"])
        resume_wire = self.h.fixture_json(
            "resume", "--continuation-id", status["continuation_id"], input_value=request
        )
        parsed = parse_native_resume_request(resume_wire)
        resumed = self.h.consumer.resume(
            parsed["continuation_id"], expected_material=parsed["expected_request"]
        )
        result = resumed["result"]
        self.assertEqual((result["authority_outcome"], result["execution_state"]), ("ALLOW", "SUCCEEDED"))
        self.assertNotEqual(result["request_id"], original_request_id)
        self.assertEqual(resumed["workflow_continuation"]["resume_budget_used"], 1)
        self.assertEqual(self.h.adapter.invoke_calls, 1)
        self.assertIsNotNone(PendingPermissionRepository(self.h.store).get_closure(original_request_id))

        replay = self.h.consumer.resume(
            parsed["continuation_id"], expected_material=parsed["expected_request"]
        )["result"]
        self.assertEqual(replay["request_id"], result["request_id"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"]["receipt_id"], result["receipt"]["receipt_id"])
        self.assertEqual(self.h.adapter.invoke_calls, 1)

    def test_nonauthorizing_owner_outcome_has_no_fresh_request_or_effect(self):
        request = self.h.request("no-change", content="never")
        blocked = self.h.consumer.submit(request)
        status = blocked["workflow_continuation"]
        self.h.resolve(status["pending_id"], "NO_CHANGE")
        outcome = self.h.consumer.resume(
            status["continuation_id"], expected_material=request
        )
        self.assertEqual(outcome["kind"], "CLOSED_NONAUTH")
        self.assertEqual(outcome["result"]["authority_outcome"], "DENY")
        self.assertEqual(outcome["result"]["execution_state"], "NOT_EXECUTED")
        self.assertEqual(outcome["workflow_continuation"]["resume_budget_used"], 0)
        self.assertIsNone(outcome["workflow_continuation"]["fresh_request_id"])
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_malformed_authority_admin_credential_mutation_and_unsupported_schema_fail_closed(self):
        request = self.h.request("boundary", content="original")
        blocked = self.h.consumer.submit(request)
        status = blocked["workflow_continuation"]
        self.h.set_policy("ALLOW")
        self.h.resolve(status["pending_id"])

        for field, value in (
            ("principal_id", "principal:forged"),
            ("agent_id", "agent:forged"),
            ("application_id", "forged-app"),
            ("skill_id", "forged-skill"),
            ("approval_id", "approval:forged"),
            ("admin_operation", "permissions.replace"),
            ("credential_ref", "secret:forged"),
        ):
            attempted = dict(request)
            attempted[field] = value
            with self.subTest(field=field), self.assertRaises(ExternalConsumerProtocolError):
                self.h.consumer.submit(attempted)
        unsupported = dict(request)
        unsupported["schema"] = "lac.external-consumer-request/v999"
        with self.assertRaises(ExternalConsumerProtocolError):
            self.h.consumer.submit(unsupported)

        mutated = json.loads(json.dumps(request))
        mutated["arguments"]["content"] = "mutated"
        with self.assertRaises(Exception):
            self.h.consumer.resume(status["continuation_id"], expected_material=mutated)
        unchanged = self.h.consumer.continuation_status(status["continuation_id"])
        self.assertEqual(unchanged["state"], "WAITING_PERMISSION")
        self.assertEqual(unchanged["resume_budget_used"], 0)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        malformed_resume = {
            "schema": "lac.native-local-consumer-resume/v1",
            "continuation_id": status["continuation_id"],
            "expected_request": request,
            "admin_operation": "permissions.replace",
        }
        with self.assertRaises(NativeLocalConsumerContractError):
            parse_native_resume_request(malformed_resume)

    def test_four_dimensional_request_binding_prevents_cross_consumer_reuse(self):
        request = self.h.request("cross-boundary")
        self.h.consumer.submit(request)

        manifest = json.loads(json.dumps(self.h.manifest))
        manifest["application_id"] = "pi003-second-app"
        manifest["skill_id"] = "second-notes"
        self.h.register(manifest)
        second = NativeLocalConsumerRuntime(
            store=self.h.store,
            authority_runtime=ExternalConsumerRuntime(
                store=self.h.store,
                declaration=ExternalConsumerDeclaration.create(manifest),
                principal_id="principal:owner",
                agent_id="agent:pi003",
                application_id="pi003-second-app",
                skill_id="second-notes",
                adapter=self.h.adapter,
            ),
        )
        with self.assertRaisesRegex(ExternalConsumerProtocolError, "outside this consumer binding"):
            second.submit(request)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_prior_pending_resolution_is_stale_for_later_continuation(self):
        first = self.h.consumer.submit(self.h.request("stale-a"))
        first_status = first["workflow_continuation"]
        self.h.resolve(first_status["pending_id"], "NO_CHANGE")
        second_request = self.h.request("stale-b")
        second = self.h.consumer.submit(second_request)
        second_status = second["workflow_continuation"]
        self.assertEqual(first_status["pending_id"], second_status["pending_id"])
        self.assertEqual(second_status["resolution_baseline_revision"], 1)
        waiting = self.h.consumer.resume(
            second_status["continuation_id"], expected_material=second_request
        )
        self.assertEqual(waiting["kind"], "WAITING_PERMISSION")
        self.assertEqual(self.h.adapter.invoke_calls, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
