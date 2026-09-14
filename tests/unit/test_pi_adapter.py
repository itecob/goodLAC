import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from packages.adapters.pi import (
    PI_FS_CREATE_TOOL,
    PI_FS_READ_TOOL,
    PI_FS_REPLACE_TOOL,
    PI_GOVERNED_TOOL_NAMES,
    PI_SHELL_EXEC_TOOL,
    PiAgentAdapter,
    PiAgentAdapterError,
    PiRunContext,
)
from packages.dispatcher import Dispatcher
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import SQLiteStateStore


NOW = datetime.fromisoformat("2026-09-14T09:00:05+00:00")


def fixed_clock():
    return NOW


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
        rules.append(
            PolicyRule.create(
                rule_id=f"rule:a001:{action}",
                principal_id="principal:owner",
                agent_id="agent:pi",
                action=action,
                resource=resource,
                decision="ALLOW",
            )
        )
    return LocalPolicyDecisionProvider(
        revision="policy:a001:unit:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:pi"},
        known_actions=actions,
        known_resources=resources,
        rules=tuple(rules),
    )


class PiAgentAdapterUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.workspace = base / "workspace"
        self.workspace.mkdir()
        self.store = SQLiteStateStore(base / "controller.db")
        self.fs = FilesystemEffectAdapter(self.workspace)
        self.printf = system_binary("printf")
        self.shell = ShellEffectAdapter(self.workspace, allowed_executables=(self.printf,))
        self.dispatcher = Dispatcher(store=self.store, policy_provider=provider(), clock=fixed_clock)
        self.adapter = PiAgentAdapter(
            store=self.store,
            dispatcher=self.dispatcher,
            filesystem_adapter=self.fs,
            shell_adapter=self.shell,
            context=PiRunContext(
                run_id="run:a001",
                principal_id="principal:owner",
                agent_id="agent:pi",
                executor_id="executor:pi",
            ),
            clock=fixed_clock,
            id_factory=iter(["one", "two", "three", "four"]).__next__,
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_exposes_only_governed_lac_tool_names(self):
        self.assertEqual(self.adapter.tool_names, PI_GOVERNED_TOOL_NAMES)
        self.assertEqual(
            set(self.adapter.tool_names),
            {PI_FS_READ_TOOL, PI_FS_CREATE_TOOL, PI_FS_REPLACE_TOOL, PI_SHELL_EXEC_TOOL},
        )
        self.assertTrue({"bash", "read", "write", "edit"}.isdisjoint(self.adapter.tool_names))

    def test_exact_translation_to_canonical_effect_requests(self):
        cases = (
            (PI_FS_READ_TOOL, {"path": "a.txt"}, "filesystem.read", "filesystem:workspace"),
            (
                PI_FS_CREATE_TOOL,
                {"path": "a.txt", "content": "x"},
                "filesystem.create",
                "filesystem:workspace",
            ),
            (
                PI_FS_REPLACE_TOOL,
                {"path": "a.txt", "content": "y"},
                "filesystem.replace",
                "filesystem:workspace",
            ),
            (
                PI_SHELL_EXEC_TOOL,
                {"executable": str(self.printf), "argv": ["%s", "x"], "cwd": ".", "environment": {}},
                "shell.exec",
                "shell:workspace",
            ),
        )
        for index, (tool, arguments, action, resource) in enumerate(cases):
            request = self.adapter.build_request(
                tool_name=tool,
                arguments=arguments,
                tool_call_id=f"call-{index}",
            )
            self.assertEqual(request.action, action)
            self.assertEqual(request.resource, resource)
            self.assertEqual(request.arguments, arguments)
            self.assertEqual(request.run_id, "run:a001")
            self.assertEqual(request.principal_id, "principal:owner")
            self.assertEqual(request.agent_id, "agent:pi")
            self.assertTrue(request.canonical_hash.startswith("sha256:"))

    def test_request_and_idempotency_identity_bind_tool_call_not_model_authority_fields(self):
        first = self.adapter.build_request(
            tool_name=PI_FS_READ_TOOL,
            arguments={"path": "a.txt"},
            tool_call_id="same-call",
        )
        second = self.adapter.build_request(
            tool_name=PI_FS_READ_TOOL,
            arguments={"path": "a.txt"},
            tool_call_id="same-call",
        )
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(first.canonical_hash, second.canonical_hash)

    def test_unknown_malformed_and_authority_shaped_tool_arguments_fail_closed(self):
        with self.assertRaises(PiAgentAdapterError):
            self.adapter.build_request(tool_name="bash", arguments={"command": "id"}, tool_call_id="bad")
        with self.assertRaises(PiAgentAdapterError):
            self.adapter.build_request(
                tool_name=PI_FS_READ_TOOL,
                arguments={"path": "a.txt", "approval_id": "model-chosen"},
                tool_call_id="bad-auth",
            )
        with self.assertRaises(PiAgentAdapterError):
            self.adapter.build_request(
                tool_name=PI_SHELL_EXEC_TOOL,
                arguments={"executable": str(self.printf), "argv": "not-an-array", "cwd": ".", "environment": {}},
                tool_call_id="bad-shape",
            )


if __name__ == "__main__":
    unittest.main()
