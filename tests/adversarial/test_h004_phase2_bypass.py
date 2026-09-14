import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path, PurePosixPath

from packages.core import EffectRequest
from packages.dispatcher import DispatchAdapterError, DispatchDenied, Dispatcher
from packages.effects.filesystem import (
    FILESYSTEM_CREATE_ACTION,
    FILESYSTEM_DELETE_ACTION,
    FILESYSTEM_READ_ACTION,
    FilesystemEffectAdapter,
)
from packages.effects.shell import SHELL_EXEC_ACTION, ShellEffectAdapter, ShellEffectError
from packages.effects.shell.adapter import _copy_binary_and_libraries
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.sandbox import NetworkMode, SandboxMount, SandboxSpec, get_selected_backend
from packages.state import AgentIdentityRepository, EffectRequestRepository, EmergencyPauseRepository, SQLiteStateStore


NOW = "2026-09-13T13:00:05+00:00"


def fixed_clock():
    observed = datetime.fromisoformat(NOW)
    return lambda: observed


def system_binary(name):
    found = shutil.which(name)
    if not found:
        raise AssertionError(f"required H004 test executable is unavailable: {name}")
    return Path(found).resolve(strict=True)


def effect_request(*, suffix, action, resource, arguments):
    return EffectRequest.create(
        request_id=f"effect:h004:{suffix}",
        run_id="run:h004",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource=resource,
        arguments=arguments,
        idempotency_key=f"idem:h004:{suffix}",
        created_at="2026-09-13T13:00:00Z",
        expires_at="2026-09-13T13:10:00Z",
    )


def policy_provider(*, action, resource, decision, suffix):
    return LocalPolicyDecisionProvider(
        revision=f"policy:h004:{suffix}:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={action},
        known_resources={resource},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:h004:{suffix}",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=action,
                resource=resource,
                decision=decision,
            ),
        ),
    )


def ldd_paths(binary):
    proc = subprocess.run(["ldd", str(binary)], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"ldd failed for H004 fixture: {binary}: {proc.stderr}")
    paths = []
    for line in proc.stdout.splitlines():
        for raw in re.findall(r"(?:=>\s*)?(/[^\s(]+)", line):
            candidate = Path(raw)
            if candidate.is_file():
                paths.append(candidate)
    return paths


def stage_bash_bundle(workspace, launcher):
    attack = workspace / "h004-launcher-bundle"
    libdir = attack / "lib"
    attack.mkdir()
    libdir.mkdir()
    bash = system_binary("bash")
    bash_copy = attack / "bash"
    shutil.copy2(bash, bash_copy)
    for library in ldd_paths(bash):
        if library.name.startswith("ld-linux") or library.name.startswith("ld-musl"):
            continue
        shutil.copy2(library, libdir / library.name)
    loader = None
    for candidate in ldd_paths(launcher):
        if candidate.name.startswith("ld-linux") or candidate.name.startswith("ld-musl"):
            loader = candidate
            break
    if loader is None:
        raise AssertionError("could not identify the dynamic loader required by the H004 launcher canary")
    return str(loader), "/workspace/h004-launcher-bundle/bash", "/workspace/h004-launcher-bundle/lib"


class H004Phase2BypassTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-h004-")
        self.base = Path(self.tmp.name).resolve()
        self.workspace = self.base / "workspace"
        self.outside = self.base / "outside"
        self.fake_home = self.base / "home" / "owner"
        self.workspace.mkdir()
        self.outside.mkdir()
        (self.fake_home / ".ssh").mkdir(parents=True)
        (self.fake_home / ".ssh" / "id_h004").write_text("H004-SSH-CANARY\n", encoding="utf-8")
        (self.outside / ".env").write_text("H004_ENV_SECRET=must-not-read\n", encoding="utf-8")
        (self.outside / "secret.txt").write_text("H004-OUTSIDE-CANARY\n", encoding="utf-8")
        self.store = SQLiteStateStore(self.base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatch(self, request, adapter, *, decision="ALLOW", suffix):
        EffectRequestRepository(self.store).put(request)
        return Dispatcher(
            store=self.store,
            policy_provider=policy_provider(
                action=request.action,
                resource=request.resource,
                decision=decision,
                suffix=suffix,
            ),
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(
            request,
            adapter=adapter,
            decision_id=f"decision:h004:{suffix}",
            lease_id=f"lease:h004:{suffix}",
            executor_id="executor:h004",
        )

    def test_parent_traversal_cannot_create_outside_workspace(self):
        adapter = FilesystemEffectAdapter(self.workspace)
        marker = self.outside / "traversal-created.txt"
        req = effect_request(
            suffix="traversal",
            action=FILESYSTEM_CREATE_ACTION,
            resource="filesystem:workspace",
            arguments={"path": "../outside/traversal-created.txt", "content": "escaped\n"},
        )
        self.assertFalse(adapter.supports(req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(req, adapter, suffix="traversal")
        self.assertFalse(marker.exists())

    def test_symlink_escape_cannot_read_or_write_outside_workspace(self):
        adapter = FilesystemEffectAdapter(self.workspace)
        read_link = self.workspace / "secret-link"
        read_link.symlink_to(self.outside / "secret.txt")
        read_req = effect_request(
            suffix="symlink-read",
            action=FILESYSTEM_READ_ACTION,
            resource="filesystem:workspace",
            arguments={"path": "secret-link"},
        )
        self.assertTrue(adapter.supports(read_req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(read_req, adapter, suffix="symlink-read")

        dir_link = self.workspace / "outside-link"
        dir_link.symlink_to(self.outside, target_is_directory=True)
        marker = self.outside / "symlink-created.txt"
        write_req = effect_request(
            suffix="symlink-write",
            action=FILESYSTEM_CREATE_ACTION,
            resource="filesystem:workspace",
            arguments={"path": "outside-link/symlink-created.txt", "content": "escaped\n"},
        )
        self.assertTrue(adapter.supports(write_req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(write_req, adapter, suffix="symlink-write")
        self.assertFalse(marker.exists())
        self.assertEqual((self.outside / "secret.txt").read_text(encoding="utf-8"), "H004-OUTSIDE-CANARY\n")

    def test_shell_cannot_read_ssh_or_outside_dotenv(self):
        cat = system_binary("cat")
        adapter = ShellEffectAdapter(self.workspace, allowed_executables=(cat,))
        for suffix, target, canary in (
            ("ssh-read", self.fake_home / ".ssh" / "id_h004", "H004-SSH-CANARY"),
            ("dotenv-read", self.outside / ".env", "H004_ENV_SECRET"),
        ):
            req = effect_request(
                suffix=suffix,
                action=SHELL_EXEC_ACTION,
                resource="shell:workspace",
                arguments={"executable": str(cat), "argv": [str(target)], "cwd": ".", "environment": {}},
            )
            result = self.dispatch(req, adapter, suffix=suffix)
            self.assertNotEqual(result.return_code, 0)
            self.assertNotIn(canary, result.stdout)
            self.assertNotIn(canary, result.stderr)

    def test_shell_cannot_write_outside_workspace(self):
        touch = system_binary("touch")
        adapter = ShellEffectAdapter(self.workspace, allowed_executables=(touch,))
        marker = self.outside / "shell-outside-created"
        req = effect_request(
            suffix="outside-write",
            action=SHELL_EXEC_ACTION,
            resource="shell:workspace",
            arguments={"executable": str(touch), "argv": [str(marker)], "cwd": ".", "environment": {}},
        )
        result = self.dispatch(req, adapter, suffix="outside-write")
        self.assertNotEqual(result.return_code, 0)
        self.assertFalse(marker.exists())

    def test_denied_file_deletion_cannot_delete_actual_file(self):
        victim = self.workspace / "must-survive.txt"
        victim.write_text("survive\n", encoding="utf-8")
        adapter = FilesystemEffectAdapter(self.workspace)
        req = effect_request(
            suffix="delete-deny",
            action=FILESYSTEM_DELETE_ACTION,
            resource="filesystem:workspace",
            arguments={"path": "must-survive.txt"},
        )
        self.assertTrue(adapter.supports(req))
        with self.assertRaises(DispatchDenied):
            self.dispatch(req, adapter, decision="DENY", suffix="delete-deny")
        self.assertEqual(victim.read_text(encoding="utf-8"), "survive\n")

    def test_unauthorized_binary_cannot_execute(self):
        printf = system_binary("printf")
        touch = system_binary("touch")
        adapter = ShellEffectAdapter(self.workspace, allowed_executables=(printf,))
        marker = self.workspace / "unauthorized-binary-marker"
        req = effect_request(
            suffix="unauthorized-binary",
            action=SHELL_EXEC_ACTION,
            resource="shell:workspace",
            arguments={"executable": str(touch), "argv": [marker.name], "cwd": ".", "environment": {}},
        )
        self.assertFalse(adapter.supports(req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(req, adapter, suffix="unauthorized-binary")
        self.assertFalse(marker.exists())

    def test_command_launcher_cannot_spawn_nested_shell(self):
        launcher = system_binary("timeout")
        marker = self.workspace / "launcher-shell-escape"
        try:
            adapter = ShellEffectAdapter(self.workspace, allowed_executables=(launcher,))
        except ShellEffectError:
            self.assertFalse(marker.exists())
            return

        # Regression canary for the pre-H004 defect. If a generic command launcher
        # becomes allowlistable again, use it to run the system dynamic loader, load
        # a staged bash plus its libraries from the writable workspace, and create a
        # marker with a shell builtin. The test then fails on the actual effect.
        loader, staged_bash, staged_libs = stage_bash_bundle(self.workspace, launcher)
        req = effect_request(
            suffix="launcher-shell",
            action=SHELL_EXEC_ACTION,
            resource="shell:workspace",
            arguments={
                "executable": str(launcher),
                "argv": [
                    "3",
                    loader,
                    "--library-path",
                    staged_libs,
                    staged_bash,
                    "-c",
                    "printf escaped > /workspace/launcher-shell-escape",
                ],
                "cwd": ".",
                "environment": {},
            },
        )
        try:
            self.dispatch(req, adapter, suffix="launcher-shell")
        except DispatchAdapterError:
            pass
        self.assertFalse(marker.exists(), "command-launching wrapper produced a nested shell effect")
        self.fail("H004 requires command-launching wrappers such as timeout to fail closed at adapter construction")

    def test_interpreter_escape_cannot_create_workspace_effect(self):
        printf = system_binary("printf")
        python = system_binary("python3")
        adapter = ShellEffectAdapter(self.workspace, allowed_executables=(printf,))
        marker = self.workspace / "interpreter-escape"
        req = effect_request(
            suffix="interpreter",
            action=SHELL_EXEC_ACTION,
            resource="shell:workspace",
            arguments={
                "executable": str(python),
                "argv": ["-c", "from pathlib import Path; Path('/workspace/interpreter-escape').write_text('escaped')"],
                "cwd": ".",
                "environment": {},
            },
        )
        self.assertFalse(adapter.supports(req))
        with self.assertRaises(DispatchAdapterError):
            self.dispatch(req, adapter, suffix="interpreter")
        self.assertFalse(marker.exists())

    def test_runtime_configuration_cannot_admit_gnu_sort_external_program_launcher(self):
        sort = system_binary("sort")
        with self.assertRaises(ShellEffectError):
            ShellEffectAdapter(self.workspace, allowed_executables=(sort,))

    def test_subprocess_network_access_is_actually_unavailable(self):
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
        with tempfile.TemporaryDirectory(prefix="lac-h004-net-") as tmp_name:
            rootfs = Path(tmp_name) / "rootfs"
            for name in ("proc", "dev", "tmp", "workspace"):
                (rootfs / name).mkdir(parents=True, exist_ok=True)
            _copy_binary_and_libraries(bash, rootfs)
            spec = SandboxSpec(
                runtime_root=rootfs,
                instance_id="h004-network-none",
                mounts=(SandboxMount(source=self.workspace, target=PurePosixPath("/workspace"), writable=True),),
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

    def test_inherited_secret_environment_is_absent_from_actual_process(self):
        printenv = system_binary("printenv")
        adapter = ShellEffectAdapter(self.workspace, allowed_executables=(printenv,))
        previous = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "H004-MUST-NOT-LEAK"
        try:
            req = effect_request(
                suffix="secret-env",
                action=SHELL_EXEC_ACTION,
                resource="shell:workspace",
                arguments={
                    "executable": str(printenv),
                    "argv": ["OPENAI_API_KEY"],
                    "cwd": ".",
                    "environment": {},
                },
            )
            result = self.dispatch(req, adapter, suffix="secret-env")
        finally:
            if previous is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous
        self.assertNotEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("H004-MUST-NOT-LEAK", result.stderr)

    def test_child_process_cannot_outlive_sandbox(self):
        marker = self.workspace / "outlived-sandbox"
        bash = system_binary("bash")
        sleep_bin = system_binary("sleep")
        with tempfile.TemporaryDirectory(prefix="lac-h004-child-") as tmp_name:
            rootfs = Path(tmp_name) / "rootfs"
            for name in ("proc", "dev", "tmp", "workspace"):
                (rootfs / name).mkdir(parents=True, exist_ok=True)
            _copy_binary_and_libraries(bash, rootfs)
            _copy_binary_and_libraries(sleep_bin, rootfs)
            spec = SandboxSpec(
                runtime_root=rootfs,
                instance_id="h004-child-containment",
                mounts=(SandboxMount(source=self.workspace, target=PurePosixPath("/workspace"), writable=True),),
                environment={"PATH": "/usr/bin", "HOME": "/nonexistent", "LC_ALL": "C"},
                cwd=PurePosixPath("/workspace"),
                network=NetworkMode.NONE,
            )
            proc = get_selected_backend().run(
                spec,
                [
                    str(bash),
                    "-c",
                    f"({str(sleep_bin)} 1; printf escaped > /workspace/outlived-sandbox) & exit 0",
                ],
                timeout=3.0,
                check=False,
            )
        self.assertEqual(proc.returncode, 0)
        time.sleep(1.5)
        self.assertFalse(marker.exists())

    def test_allowed_bounded_workspace_effects_remain_functional(self):
        fs = FilesystemEffectAdapter(self.workspace)
        create = effect_request(
            suffix="positive-create",
            action=FILESYSTEM_CREATE_ACTION,
            resource="filesystem:workspace",
            arguments={"path": "allowed.txt", "content": "allowed-h004\n"},
        )
        created = self.dispatch(create, fs, suffix="positive-create")
        self.assertEqual(created.byte_count, len("allowed-h004\n".encode("utf-8")))
        self.assertEqual((self.workspace / "allowed.txt").read_text(encoding="utf-8"), "allowed-h004\n")

        printf = system_binary("printf")
        shell = ShellEffectAdapter(self.workspace, allowed_executables=(printf,))
        req = effect_request(
            suffix="positive-shell",
            action=SHELL_EXEC_ACTION,
            resource="shell:workspace",
            arguments={"executable": str(printf), "argv": ["%s", "h004-ok"], "cwd": ".", "environment": {}},
        )
        result = self.dispatch(req, shell, suffix="positive-shell")
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "h004-ok")


if __name__ == "__main__":
    unittest.main()
