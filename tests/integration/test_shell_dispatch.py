import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from packages.core import Approval, EffectRequest, PolicyDecision
from packages.dispatcher import DispatchApprovalRequired, DispatchDuplicateEffect, Dispatcher
from packages.effects.shell import SHELL_EXEC_ACTION, ShellEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
)


NOW = "2026-09-13T12:00:05+00:00"


def fixed_clock():
    observed = datetime.fromisoformat(NOW)
    return lambda: observed


def system_binary(name):
    found = shutil.which(name)
    if not found:
        raise AssertionError(f"required test executable is unavailable: {name}")
    return Path(found).resolve(strict=True)


def make_request(*, suffix, executable, argv, cwd=".", environment=None):
    return EffectRequest.create(
        request_id=f"effect:h003-int:{suffix}",
        run_id="run:h003-int",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=SHELL_EXEC_ACTION,
        resource="shell:workspace",
        arguments={
            "executable": str(executable),
            "argv": argv,
            "cwd": cwd,
            "environment": {} if environment is None else environment,
        },
        idempotency_key=f"idem:h003-int:{suffix}",
        created_at="2026-09-13T12:00:00Z",
        expires_at="2026-09-13T12:10:00Z",
    )


def provider(decision):
    return LocalPolicyDecisionProvider(
        revision=f"policy:h003:{decision}:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={SHELL_EXEC_ACTION},
        known_resources={"shell:workspace"},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:h003:{decision}",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=SHELL_EXEC_ACTION,
                resource="shell:workspace",
                decision=decision,
            ),
        ),
    )


def approval_foundation(store, request):
    decision = PolicyDecision.create(
        decision_id=f"decision:h003:foundation:{request.request_id}",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:h003:foundation:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-13T12:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )
    approval = Approval.create(
        approval_id=f"approval:h003:{request.request_id}",
        request_id=request.request_id,
        policy_decision_id=decision.decision_id,
        canonical_request_hash=request.canonical_hash,
        approver="principal:owner",
        decision="APPROVE",
        scope="ONCE",
        created_at="2026-09-13T12:00:02Z",
        expires_at="2026-09-13T12:05:00Z",
    )
    PolicyDecisionRepository(store).put(decision)
    ApprovalRepository(store).put(approval)
    return approval


class ShellDispatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.workspace = base / "workspace"
        self.workspace.mkdir()
        (self.workspace / "subdir").mkdir()
        self.printf = system_binary("printf")
        self.touch = system_binary("touch")
        self.store = SQLiteStateStore(base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        self.adapter = ShellEffectAdapter(
            self.workspace,
            allowed_executables=(self.printf, self.touch),
            allowed_environment=("LAC_H003_ALLOWED",),
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatch(self, request, decision, *, suffix, approval_id=None):
        EffectRequestRepository(self.store).put(request)
        return Dispatcher(
            store=self.store,
            policy_provider=provider(decision),
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(
            request,
            adapter=self.adapter,
            decision_id=f"decision:h003:current:{suffix}",
            lease_id=f"lease:h003:{suffix}",
            executor_id="executor:h003",
            approval_id=approval_id,
        )

    def test_allowed_exact_argv_and_cwd_execute_through_dispatcher_with_receipt(self):
        request = make_request(
            suffix="printf",
            executable=self.printf,
            argv=["%s", "hello-h003"],
            cwd="subdir",
            environment={"LAC_H003_ALLOWED": "bound"},
        )
        result = self.dispatch(request, "ALLOW", suffix="printf")
        self.assertEqual(result.executable, str(self.printf))
        self.assertEqual(result.argv, ("%s", "hello-h003"))
        self.assertEqual(result.cwd, "subdir")
        self.assertEqual(result.environment_keys, ("LAC_H003_ALLOWED",))
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "hello-h003")
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(request.request_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.outcome.value, "SUCCEEDED")
        self.assertEqual(receipt.adapter_id, "shell:v1")

    def test_workspace_mutation_requires_exact_approval_and_duplicate_does_not_repeat(self):
        request = make_request(
            suffix="approved-touch",
            executable=self.touch,
            argv=["approved.txt"],
        )
        EffectRequestRepository(self.store).put(request)
        with self.assertRaises(DispatchApprovalRequired):
            Dispatcher(
                store=self.store,
                policy_provider=provider("REQUIRE_APPROVAL"),
                clock=fixed_clock(),
                lease_seconds=20,
            ).dispatch(
                request,
                adapter=self.adapter,
                decision_id="decision:h003:noapproval",
                lease_id="lease:h003:noapproval",
                executor_id="executor:h003",
            )
        self.assertFalse((self.workspace / "approved.txt").exists())

        approval = approval_foundation(self.store, request)
        result = Dispatcher(
            store=self.store,
            policy_provider=provider("REQUIRE_APPROVAL"),
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(
            request,
            adapter=self.adapter,
            decision_id="decision:h003:approved",
            lease_id="lease:h003:approved",
            executor_id="executor:h003",
            approval_id=approval.approval_id,
        )
        self.assertEqual(result.return_code, 0)
        self.assertTrue((self.workspace / "approved.txt").is_file())

        with self.assertRaises(DispatchDuplicateEffect):
            Dispatcher(
                store=self.store,
                policy_provider=provider("REQUIRE_APPROVAL"),
                clock=fixed_clock(),
                lease_seconds=20,
            ).dispatch(
                request,
                adapter=self.adapter,
                decision_id="decision:h003:duplicate",
                lease_id="lease:h003:duplicate",
                executor_id="executor:h003",
                approval_id=approval.approval_id,
            )
        self.assertTrue((self.workspace / "approved.txt").is_file())

    def test_security_relevant_shell_material_participates_in_canonical_request_hash(self):
        common = dict(
            request_id="effect:h003-int:hash-binding",
            run_id="run:h003-int",
            principal_id="principal:owner",
            agent_id="agent:test",
            action=SHELL_EXEC_ACTION,
            resource="shell:workspace",
            idempotency_key="idem:h003-int:hash-binding",
            created_at="2026-09-13T12:00:00Z",
            expires_at="2026-09-13T12:10:00Z",
        )
        base_arguments = {
            "executable": str(self.printf),
            "argv": ["%s", "x"],
            "cwd": ".",
            "environment": {},
        }
        base = EffectRequest.create(arguments=base_arguments, **common)
        variants = (
            {**base_arguments, "argv": ["%s", "y"]},
            {**base_arguments, "cwd": "subdir"},
            {**base_arguments, "environment": {"LAC_H003_ALLOWED": "1"}},
            {**base_arguments, "executable": str(self.touch)},
        )
        for arguments in variants:
            variant = EffectRequest.create(arguments=arguments, **common)
            self.assertNotEqual(base.canonical_hash, variant.canonical_hash)


if __name__ == "__main__":
    unittest.main()
