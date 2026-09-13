import os
import shutil
import socket
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path, PurePosixPath

from packages.core import EffectRequest
from packages.dispatcher import DispatchAdapterError, Dispatcher
from packages.effects.shell import SHELL_EXEC_ACTION, ShellEffectAdapter
from packages.effects.shell.adapter import _copy_binary_and_libraries
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.sandbox import NetworkMode, SandboxMount, SandboxSpec, get_selected_backend
from packages.state import AgentIdentityRepository, EffectRequestRepository, EmergencyPauseRepository, SQLiteStateStore


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
        request_id=f"effect:h003-adv:{suffix}",
        run_id="run:h003-adv",
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
        idempotency_key=f"idem:h003-adv:{suffix}",
        created_at="2026-09-13T12:00:00Z",
        expires_at="2026-09-13T12:10:00Z",
    )


def provider():
    return LocalPolicyDecisionProvider(
        revision="policy:h003-adv:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={SHELL_EXEC_ACTION},
        known_resources={"shell:workspace"},
        rules=(
            PolicyRule.create(
                rule_id="rule:h003-adv:allow",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=SHELL_EXEC_ACTION,
                resource="shell:workspace",
                decision="ALLOW",
            ),
        ),
    )


class H003ShellBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.workspace = self.base / "workspace"
        self.outside = self.base / "outside"
        self.workspace.mkdir()
        self.outside.mkdir()
        self.printf = system_binary("printf")
        self.touch = system_binary("touch")
        self.printenv = system_binary("printenv")
        self.store = SQLiteStateStore(self.base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def adapter(self, *executables, allowed_environment=()):
        return ShellEffectAdapter(
            self.workspace,
            allowed_executables=executables,
            allowed_environment=allowed_environment,
        )

    def dispatch(self, req, adapter, suffix):
        EffectRequestRepository(self.store).put(req)
        return Dispatcher(
            store=self.store,
            policy_provider=provider(),
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(
            req,
            adapter=adapter,
            decision_id=f"decision:h003-adv:{suffix}",
            lease_id=f"lease:h003-adv:{suffix}",
            executor_id="executor:h003-adv",
        )

    def test_arbitrary_host_cwd_and_symlink_cwd_cannot_write_outside_workspace(self):
        adapter = self.adapter(self.touch)
        absolute = make_request(
            suffix="absolute-cwd",
            executable=self.touch,
            argv=["escaped.txt"],
            cwd=str(self.outside),
        )
        self.assertFalse(adapter.supports(absolute))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(absolute, adapter, "absolute-cwd")
        self.assertFalse((self.outside / "escaped.txt").exists())

        link = self.workspace / "outside-link"
        link.symlink_to(self.outside, target_is_directory=True)
        symlinked = make_request(
            suffix="symlink-cwd",
            executable=self.touch,
            argv=["escaped.txt"],
            cwd="outside-link",
        )
        self.assertTrue(adapter.supports(symlinked))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(symlinked, adapter, "symlink-cwd")
        self.assertFalse((self.outside / "escaped.txt").exists())

    def test_inherited_service_secret_is_absent_from_actual_process_environment(self):
        adapter = self.adapter(self.printenv)
        previous = os.environ.get("AWS_SECRET_ACCESS_KEY")
        os.environ["AWS_SECRET_ACCESS_KEY"] = "H003-MUST-NOT-LEAK"
        try:
            req = make_request(
                suffix="secret-env",
                executable=self.printenv,
                argv=["AWS_SECRET_ACCESS_KEY"],
            )
            result = self.dispatch(req, adapter, "secret-env")
        finally:
            if previous is None:
                os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            else:
                os.environ["AWS_SECRET_ACCESS_KEY"] = previous
        self.assertNotEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("H003-MUST-NOT-LEAK", result.stderr)

    def test_explicit_allowed_environment_is_constructed_not_inherited(self):
        adapter = self.adapter(self.printenv, allowed_environment=("LAC_H003_ALLOWED",))
        previous = os.environ.get("LAC_H003_ALLOWED")
        os.environ["LAC_H003_ALLOWED"] = "host-value-must-not-win"
        try:
            req = make_request(
                suffix="explicit-env",
                executable=self.printenv,
                argv=["LAC_H003_ALLOWED"],
                environment={"LAC_H003_ALLOWED": "request-bound"},
            )
            result = self.dispatch(req, adapter, "explicit-env")
        finally:
            if previous is None:
                os.environ.pop("LAC_H003_ALLOWED", None)
            else:
                os.environ["LAC_H003_ALLOWED"] = previous
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout.strip(), "request-bound")

    def test_shell_expansion_and_command_separator_shapes_remain_literal_argv(self):
        adapter = self.adapter(self.printf)
        marker = self.workspace / "pwned"
        payload = "$(touch pwned); touch pwned; > pwned"
        req = make_request(
            suffix="literal-metacharacters",
            executable=self.printf,
            argv=["%s", payload],
        )
        result = self.dispatch(req, adapter, "literal-metacharacters")
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, payload)
        self.assertFalse(marker.exists())

    def test_sudo_shell_and_unsupported_executable_shapes_fail_before_host_effect(self):
        adapter = self.adapter(self.touch)
        marker = self.workspace / "privileged-marker"
        attempts = (
            ("sudo", "/usr/bin/sudo", [str(self.touch), "privileged-marker"]),
            ("shell", "/usr/bin/bash", ["-c", "touch privileged-marker"]),
            ("unknown", "/usr/bin/definitely-not-authorized", ["privileged-marker"]),
        )
        for suffix, executable, argv in attempts:
            req = make_request(suffix=suffix, executable=executable, argv=argv)
            self.assertFalse(adapter.supports(req), executable)
            with self.assertRaises(DispatchAdapterError):
                self.dispatch(req, adapter, suffix)
            self.assertFalse(marker.exists())

    def test_selected_sandbox_network_none_blocks_actual_host_loopback_connection(self):
        # This is an H003-specific actual-effect challenge of the same selected backend
        # the shell adapter uses. Bash is copied into the test-only runtime solely to
        # exercise /dev/tcp; ShellEffectAdapter itself refuses shell interpreters.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(1.0)
        port = listener.getsockname()[1]
        accepted = []

        def accept_once():
            try:
                conn, _ = listener.accept()
            except (OSError, socket.timeout):
                return
            else:
                accepted.append(True)
                conn.close()

        thread = threading.Thread(target=accept_once, daemon=True)
        thread.start()
        bash = system_binary("bash")
        with tempfile.TemporaryDirectory(prefix="lac-h003-net-") as tmp_name:
            rootfs = Path(tmp_name) / "rootfs"
            for name in ("proc", "dev", "tmp", "workspace"):
                (rootfs / name).mkdir(parents=True, exist_ok=True)
            _copy_binary_and_libraries(bash, rootfs)
            spec = SandboxSpec(
                runtime_root=rootfs,
                instance_id="h003-network-none",
                mounts=(
                    SandboxMount(
                        source=self.workspace,
                        target=PurePosixPath("/workspace"),
                        writable=True,
                    ),
                ),
                environment={"PATH": "/usr/bin", "HOME": "/nonexistent", "LC_ALL": "C"},
                cwd=PurePosixPath("/workspace"),
                network=NetworkMode.NONE,
            )
            proc = get_selected_backend().run(
                spec,
                [str(bash), "-c", f"exec 3<>/dev/tcp/127.0.0.1/{port}"],
                timeout=3.0,
                check=False,
            )
        thread.join(timeout=2.0)
        listener.close()
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(accepted)


if __name__ == "__main__":
    unittest.main()
