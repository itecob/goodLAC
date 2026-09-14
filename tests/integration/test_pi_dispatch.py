import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from packages.adapters.pi import (
    PI_FS_CREATE_TOOL,
    PI_FS_READ_TOOL,
    PI_FS_REPLACE_TOOL,
    PI_SHELL_EXEC_TOOL,
    PiAgentAdapter,
    PiAgentAdapterError,
    PiRunContext,
)
from packages.core import Approval, PolicyDecision
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchDuplicateEffect,
    DispatchPaused,
    Dispatcher,
)
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    EffectReceiptRepository,
    EmergencyPauseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
)


REQUEST_NOW = datetime.fromisoformat("2026-09-14T10:00:00+00:00")
DISPATCH_NOW = datetime.fromisoformat("2026-09-14T10:00:05+00:00")


def dispatch_clock():
    return DISPATCH_NOW


def system_binary(name):
    found = shutil.which(name)
    if not found:
        raise AssertionError(f"required executable missing: {name}")
    return Path(found).resolve(strict=True)


def provider():
    actions = {"filesystem.read", "filesystem.create", "filesystem.replace", "shell.exec"}
    resources = {"filesystem:workspace", "shell:workspace"}
    rules = []
    for action in sorted(actions):
        resource = "shell:workspace" if action == "shell.exec" else "filesystem:workspace"
        decision = "REQUIRE_APPROVAL" if action == "filesystem.replace" else "ALLOW"
        rules.append(
            PolicyRule.create(
                rule_id=f"rule:a001:int:{action}",
                principal_id="principal:owner",
                agent_id="agent:pi",
                action=action,
                resource=resource,
                decision=decision,
            )
        )
    return LocalPolicyDecisionProvider(
        revision="policy:a001:integration:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:pi"},
        known_actions=actions,
        known_resources=resources,
        rules=tuple(rules),
    )


def exact_approval(store, request):
    decision = PolicyDecision.create(
        decision_id=f"decision:a001:foundation:{request.request_id}",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:a001:foundation:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-14T10:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )
    approval = Approval.create(
        approval_id=f"approval:a001:{request.request_id}",
        request_id=request.request_id,
        policy_decision_id=decision.decision_id,
        canonical_request_hash=request.canonical_hash,
        approver="principal:owner",
        decision="APPROVE",
        scope="ONCE",
        created_at="2026-09-14T10:00:02Z",
        expires_at="2026-09-14T10:05:00Z",
    )
    PolicyDecisionRepository(store).put(decision)
    ApprovalRepository(store).put(approval)
    return approval


class PiDispatcherIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.workspace = base / "workspace"
        self.workspace.mkdir()
        (self.workspace / "existing.txt").write_text("old\n", encoding="utf-8")
        self.store = SQLiteStateStore(base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:pi", "principal:owner")
        self.printf = system_binary("printf")
        self.fs = FilesystemEffectAdapter(self.workspace)
        self.shell = ShellEffectAdapter(self.workspace, allowed_executables=(self.printf,))
        self.dispatcher = Dispatcher(
            store=self.store,
            policy_provider=provider(),
            clock=dispatch_clock,
            lease_seconds=20,
        )
        self.counter = 0

        def next_id():
            self.counter += 1
            return f"id-{self.counter}"

        self.request_now = REQUEST_NOW
        self.pi = PiAgentAdapter(
            store=self.store,
            dispatcher=self.dispatcher,
            filesystem_adapter=self.fs,
            shell_adapter=self.shell,
            context=PiRunContext(
                run_id="run:a001:int",
                principal_id="principal:owner",
                agent_id="agent:pi",
                executor_id="executor:pi",
            ),
            clock=lambda: self.request_now,
            id_factory=next_id,
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_filesystem_and_shell_enter_existing_dispatcher_and_receipt_path(self):
        read = self.pi.execute_message({
            "toolCallId": "read-1",
            "toolName": PI_FS_READ_TOOL,
            "arguments": {"path": "existing.txt"},
        })
        self.assertEqual(read["content"], "old\n")
        read_receipt = EffectReceiptRepository(self.store).get_receipt_for_request(read["request_id"])
        self.assertEqual(read_receipt.adapter_id, "filesystem:v1")

        created = self.pi.execute_message({
            "toolCallId": "create-1",
            "toolName": PI_FS_CREATE_TOOL,
            "arguments": {"path": "created.txt", "content": "created\n"},
        })
        self.assertEqual((self.workspace / "created.txt").read_text(encoding="utf-8"), "created\n")
        created_receipt = EffectReceiptRepository(self.store).get_receipt_for_request(created["request_id"])
        self.assertEqual(created_receipt.adapter_id, "filesystem:v1")

        shell = self.pi.execute_message({
            "toolCallId": "shell-1",
            "toolName": PI_SHELL_EXEC_TOOL,
            "arguments": {"executable": str(self.printf), "argv": ["%s", "pi-a001"], "cwd": ".", "environment": {}},
        })
        self.assertEqual(shell["stdout"], "pi-a001")
        shell_receipt = EffectReceiptRepository(self.store).get_receipt_for_request(shell["request_id"])
        self.assertEqual(shell_receipt.adapter_id, "shell:v1")

    def test_existing_approval_binding_remains_controller_side(self):
        request = self.pi.build_request(
            tool_name=PI_FS_REPLACE_TOOL,
            arguments={"path": "existing.txt", "content": "new\n"},
            tool_call_id="replace-1",
        )
        with self.assertRaises(DispatchApprovalRequired):
            self.pi.execute_tool(
                tool_name=PI_FS_REPLACE_TOOL,
                arguments={"path": "existing.txt", "content": "new\n"},
                tool_call_id="replace-1",
            )
        self.assertEqual((self.workspace / "existing.txt").read_text(encoding="utf-8"), "old\n")
        approval = exact_approval(self.store, request)
        self.request_now = REQUEST_NOW + timedelta(minutes=1)
        result = self.pi.execute_tool(
            tool_name=PI_FS_REPLACE_TOOL,
            arguments={"path": "existing.txt", "content": "new\n"},
            tool_call_id="replace-1",
            approval_id=approval.approval_id,
        )
        self.assertEqual(result.path, "existing.txt")
        self.assertEqual((self.workspace / "existing.txt").read_text(encoding="utf-8"), "new\n")

    def test_existing_idempotency_and_emergency_pause_remain_authoritative(self):
        self.pi.execute_tool(
            tool_name=PI_FS_CREATE_TOOL,
            arguments={"path": "once.txt", "content": "once\n"},
            tool_call_id="once-1",
        )
        with self.assertRaises(DispatchDuplicateEffect):
            self.pi.execute_tool(
                tool_name=PI_FS_CREATE_TOOL,
                arguments={"path": "once.txt", "content": "once\n"},
                tool_call_id="once-1",
            )

        EmergencyPauseRepository(self.store).pause()
        with self.assertRaises(DispatchPaused):
            self.pi.execute_tool(
                tool_name=PI_FS_READ_TOOL,
                arguments={"path": "existing.txt"},
                tool_call_id="paused-read",
            )

    def test_model_cannot_name_an_ungoverned_tool_or_smuggle_authority(self):
        with self.assertRaises(PiAgentAdapterError):
            self.pi.execute_tool(tool_name="bash", arguments={"command": "touch bypass"}, tool_call_id="bypass")
        with self.assertRaises(PiAgentAdapterError):
            self.pi.execute_tool(
                tool_name=PI_FS_READ_TOOL,
                arguments={"path": "existing.txt", "lease_id": "model-selected"},
                tool_call_id="smuggle",
            )
        with self.assertRaises(PiAgentAdapterError):
            self.pi.execute_message({
                "toolCallId": "smuggle-message",
                "toolName": PI_FS_READ_TOOL,
                "arguments": {"path": "existing.txt"},
                "approval_id": "model-selected",
            })


if __name__ == "__main__":
    unittest.main()
