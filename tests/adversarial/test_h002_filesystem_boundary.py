import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from packages.core import EffectRequest
from packages.dispatcher import DispatchAdapterError, Dispatcher
from packages.effects.filesystem import (
    FILESYSTEM_CREATE_ACTION,
    FILESYSTEM_READ_ACTION,
    FilesystemEffectAdapter,
)
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import AgentIdentityRepository, EffectRequestRepository, EmergencyPauseRepository, SQLiteStateStore


def clock():
    observed = datetime.fromisoformat("2026-09-13T08:00:05+00:00")
    return lambda: observed


def request(*, suffix, action, arguments):
    return EffectRequest.create(
        request_id=f"effect:h002-adv:{suffix}",
        run_id="run:h002-adv",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource="filesystem:workspace",
        arguments=arguments,
        idempotency_key=f"idem:h002-adv:{suffix}",
        created_at="2026-09-13T08:00:00Z",
        expires_at="2026-09-13T08:10:00Z",
    )


def provider(action):
    return LocalPolicyDecisionProvider(
        revision=f"policy:h002-adv:{action}:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={action},
        known_resources={"filesystem:workspace"},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:h002-adv:{action}",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=action,
                resource="filesystem:workspace",
                decision="ALLOW",
            ),
        ),
    )


class H002FilesystemBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.workspace = self.base / "workspace"
        self.outside = self.base / "outside"
        self.workspace.mkdir()
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text("HOST-SECRET\n", encoding="utf-8")
        self.store = SQLiteStateStore(self.base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        self.adapter = FilesystemEffectAdapter(self.workspace)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatch(self, req, suffix):
        EffectRequestRepository(self.store).put(req)
        return Dispatcher(
            store=self.store,
            policy_provider=provider(req.action),
            clock=clock(),
            lease_seconds=20,
        ).dispatch(
            req,
            adapter=self.adapter,
            decision_id=f"decision:h002-adv:{suffix}",
            lease_id=f"lease:h002-adv:{suffix}",
            executor_id="executor:h002-adv",
        )

    def test_absolute_and_parent_traversal_are_rejected_before_host_effect(self):
        absolute = request(suffix="absolute", action=FILESYSTEM_READ_ACTION, arguments={"path": str(self.outside / "secret.txt")})
        traversal = request(suffix="traversal", action=FILESYSTEM_CREATE_ACTION, arguments={"path": "../outside/pwned.txt", "content": "pwned"})
        self.assertFalse(self.adapter.supports(absolute))
        self.assertFalse(self.adapter.supports(traversal))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(absolute, "absolute")
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(traversal, "traversal")
        self.assertFalse((self.outside / "pwned.txt").exists())
        self.assertEqual((self.outside / "secret.txt").read_text(encoding="utf-8"), "HOST-SECRET\n")

    def test_symlink_read_escape_fails_as_actual_sandbox_effect(self):
        link = self.workspace / "secret-link"
        link.symlink_to(self.outside / "secret.txt")
        req = request(suffix="symlink-read", action=FILESYSTEM_READ_ACTION, arguments={"path": "secret-link"})
        self.assertTrue(self.adapter.supports(req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(req, "symlink-read")
        self.assertEqual((self.outside / "secret.txt").read_text(encoding="utf-8"), "HOST-SECRET\n")

    def test_symlink_directory_write_escape_cannot_create_outside_file(self):
        link = self.workspace / "outside-link"
        link.symlink_to(self.outside, target_is_directory=True)
        req = request(
            suffix="symlink-write",
            action=FILESYSTEM_CREATE_ACTION,
            arguments={"path": "outside-link/pwned.txt", "content": "pwned\n"},
        )
        self.assertTrue(self.adapter.supports(req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(req, "symlink-write")
        self.assertFalse((self.outside / "pwned.txt").exists())

    def test_sandbox_still_blocks_symlink_escape_if_host_precheck_is_bypassed(self):
        link = self.workspace / "outside-race"
        link.symlink_to(self.outside, target_is_directory=True)
        req = request(
            suffix="sandbox-last-line",
            action=FILESYSTEM_CREATE_ACTION,
            arguments={"path": "outside-race/escaped.txt", "content": "escaped\n"},
        )
        # H002 normally rejects this at host-shape validation. Bypass only that
        # defense in the test to prove the H001 sandbox/fixed helper is also an
        # effect boundary and the outside host path remains unreachable.
        self.adapter._validate_host_shape = lambda operation: None
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(req, "sandbox-last-line")
        self.assertFalse((self.outside / "escaped.txt").exists())

    def test_workspace_read_mount_is_not_writable(self):
        (self.workspace / "read.txt").write_text("read-only\n", encoding="utf-8")
        req = request(suffix="read-ro", action=FILESYSTEM_READ_ACTION, arguments={"path": "read.txt"})
        result = self.dispatch(req, "read-ro")
        self.assertEqual(result.content, "read-only\n")
        self.assertEqual((self.workspace / "read.txt").read_text(encoding="utf-8"), "read-only\n")


if __name__ == "__main__":
    unittest.main()
