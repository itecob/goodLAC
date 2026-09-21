from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packages.productization import v1
from scripts.pi_native_tui_host import _unwrap_native_effect_result

ROOT = Path(__file__).resolve().parents[2]


class Pi005NativeTuiSourceTests(unittest.TestCase):
    def test_native_frontend_uses_pinned_pi_source_cli(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        self.assertIn('PI_SOURCE_CLI_REL = Path("packages/coding-agent/src/cli.ts")', host)
        self.assertIn('node_modules/tsx/dist/cli.mjs', host)
        self.assertIn('PI_ROOT_TSCONFIG_REL = Path("tsconfig.json")', host)
        self.assertIn('"--tsconfig", "/pi/" + tsconfig_rel.as_posix()', host)
        self.assertNotIn('coding-agent/dist/index.js', host)
        self.assertNotIn('coding-agent/dist/bundle/cli.js', host)
        ext = (ROOT / "scripts/pi_native_tui.mjs").read_text(encoding="utf-8")
        self.assertIn('from "/pi/packages/ai/dist/index.js"', ext)
        self.assertNotIn('@earendil-works/pi-ai', ext)
        self.assertIn('frontend:"PiSourceCLI"', ext)
        self.assertIn('net.createConnection({ path: BROKER_SOCKET })', ext)
        self.assertIn('await connected;', ext)
        self.assertNotIn('LAC_PI005_BROKER_FD', ext)

    def test_resource_and_tool_lockdown_is_explicit(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        for token in (
            '"--no-builtin-tools"', '"--tools", ",".join(EXPECTED_TOOLS)',
            '"--no-extensions", "-e", "/lac/pi_native_tui.mjs"',
            '"--no-skills"', '"--no-prompt-templates"', '"--no-themes"',
            '"--no-context-files"', '"--no-session"',
            'PI005_PROHIBITED_EXTENSION_LOADED', 'PI005_PROHIBITED_SKILL',
            'PI005_PROHIBITED_PROMPT', 'PI005_PROHIBITED_CONTEXT',
        ):
            self.assertIn(token, host)
        ext = (ROOT / "scripts/pi_native_tui.mjs").read_text(encoding="utf-8")
        self.assertIn('createGovernedLacTools', ext)
        self.assertIn('pi.registerTool(tool)', ext)
        self.assertIn('pi.registerProvider("lac-freetoken"', ext)
        self.assertIn('baseUrl:"http://127.0.0.1:1"', ext)
        self.assertIn('api:"openai-completions"', ext)
        self.assertIn('apiKey:"LAC_PI005_LOCAL_BROKER_NONSECRET"', ext)
        self.assertIn('streamSimple:makeRpcStreamFn', ext)
        self.assertIn('if (mode === "probe" && reason !== "toolUse") socket.unref();', ext)
        self.assertIn('makeRpcStreamFn(Number(bootstrap.timeoutSeconds || 300), String(bootstrap.mode))', ext)
        self.assertNotIn('api:"lac-model-provider"', ext)

    def test_native_cli_process_stays_inside_accepted_sandbox(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        self.assertIn("NetworkMode.NONE", host)
        self.assertIn('self.broker_path = rootfs / "lac" / "broker.sock"', host)
        self.assertIn('"LAC_PI005_BROKER_SOCKET": "/lac/broker.sock"', host)
        self.assertIn('self.broker_listener.accept()', host)
        self.assertNotIn("pass_fds=", host)
        self.assertNotIn("socket.socketpair", host)
        self.assertNotIn('"--sync-fd"', host)
        self.assertIn('SandboxMount(source=baseline.PI_CHECKOUT, target=PurePosixPath("/pi"), writable=False)', host)
        self.assertIn('SandboxMount(source=agent_state, target=PurePosixPath("/lac/agent"), writable=True)', host)
        self.assertEqual(host.count("writable=True"), 1)
        self.assertIn('agent_state.mkdir(mode=0o700, parents=True, exist_ok=False)', host)
        self.assertNotIn("SandboxMount(source=self.workspace", host)
        for key in (
            "host_file_readable", "host_workspace_readable", "host_workspace_write_effect",
            "synthetic_service_credential_inherited", "arbitrary_host_executable_launched",
            "loopback_connected", "private_network_connected", "admin_socket_visible",
        ):
            self.assertIn(key, host)

    def test_default_launcher_uses_native_host_and_bypass_remains_separate(self):
        product = (ROOT / "packages/productization/v1.py").read_text(encoding="utf-8")
        wrapper = (ROOT / "scripts/lac-pi").read_text(encoding="utf-8")
        self.assertIn("pi_native_tui_host.py", product)
        self.assertIn("pi_native_tui_host.py", wrapper)
        self.assertIn('DANGEROUS_BYPASS_FLAG = "--dangerously-bypass-lac"', product)
        self.assertIn("_verify_and_launch_pinned_ungoverned_pi", product)
        shell_bridge = (ROOT / "scripts/pi_v1_controller_bridge.py").read_text(encoding="utf-8")
        self.assertNotIn('canonical_binary("node")', shell_bridge)
        self.assertNotIn('canonical_binary("pi")', shell_bridge)

    def test_rc3_upgrade_and_rollback_restore_rc2_install_exactly(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            paths = v1.paths(home)
            prior = paths["releases"] / "1.0.0-rc.2"
            (prior / "bin").mkdir(parents=True)
            for name in v1.BIN_NAMES:
                command = prior / "bin" / name
                command.write_text(f"#!/bin/sh\necho rc2-{name}\n", encoding="utf-8")
                command.chmod(0o755)
            paths["current"].parent.mkdir(parents=True, exist_ok=True)
            paths["current"].symlink_to(prior)
            paths["bin"].mkdir(parents=True, exist_ok=True)
            for name in v1.BIN_NAMES:
                (paths["bin"] / name).symlink_to(paths["current"] / "bin" / name)
            paths["config"].parent.mkdir(parents=True, exist_ok=True)
            config = v1.default_config(home)
            config["runtime"] = "external"
            paths["config"].write_text(json.dumps(config, sort_keys=True) + "\n", encoding="utf-8")
            paths["config"].chmod(0o600)
            paths["install_state"].parent.mkdir(parents=True, exist_ok=True)
            prior_state = b'{"schema":"lac.v1-install-state/v1","sentinel":"rc2-exact"}\n'
            paths["install_state"].write_bytes(prior_state)
            paths["install_state"].chmod(0o600)
            bashrc = home / ".bashrc"
            fragment = home / v1.SHELL_FRAGMENT_REL
            fragment.parent.mkdir(parents=True, exist_ok=True)
            prior_fragment = v1._shell_fragment_bytes("bash", paths["bin"] / "pi")
            fragment.write_bytes(prior_fragment)
            fragment.chmod(0o600)
            prior_bashrc = b"# rc2 owner shell\n" + v1._shell_rc_block(fragment)
            bashrc.write_bytes(prior_bashrc)
            archive = root / "rc3.tar.gz"
            with mock.patch.dict(os.environ, {"SHELL": "/bin/bash", "LAC_PI004_TARGET_SHELL": "bash"}, clear=False):
                v1.build_distribution(ROOT, archive)
                state = v1.install_distribution(archive, home)
                self.assertEqual(state["version"], v1.RELEASE_VERSION)
                v1.rollback(home)
            self.assertEqual(paths["current"].resolve().name, "1.0.0-rc.2")
            self.assertEqual(paths["install_state"].read_bytes(), prior_state)
            self.assertEqual(bashrc.read_bytes(), prior_bashrc)
            self.assertEqual(fragment.read_bytes(), prior_fragment)

    def test_profile_probe_uses_isolated_admin_runtime_namespace(self):
        integration = (ROOT / "tests/integration/test_pi005_native_tui_profile.py").read_text(encoding="utf-8")
        self.assertIn('runtime_dir = root / "runtime"', integration)
        self.assertIn('runtime_dir.mkdir(mode=0o700)', integration)
        self.assertIn('env["XDG_RUNTIME_DIR"] = str(runtime_dir)', integration)
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        self.assertIn('def _start_admin_server(state: Path)', host)
        self.assertIn('admin server exited before ready rc=', host)
        self.assertIn('admin = _start_admin_server(state)', host)
        self.assertIn('native Pi stderr tail:', host)
        self.assertIn('stderr=subprocess.PIPE if self.mode == "probe" else None', host)
        self.assertIn('receive_timeout = 45.0 if self.mode == "probe" else 3600.0', host)
        self.assertIn('broker_phase=', host)
        self.assertIn('PI005 profile probe exceeded 90 seconds; partial output follows:', integration)

    def test_profile_probe_counts_unique_permission_workflow_not_callbacks(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        self.assertIn('configured_workflow: tuple[str, str] | None = None', host)
        self.assertIn('elif workflow != configured_workflow:', host)
        self.assertIn('native Pi duplicate probe entered a second permission workflow', host)
        self.assertIn('unique_workflows != {configured_workflow}', host)
        self.assertNotIn('if len(observed_waits) != 1:', host)
        self.assertIn('first_receipt.get("receipt_id") != second_receipt.get("receipt_id")', host)
        self.assertIn('LAC_PI005_PERMISSION_WORKFLOW_UNIQUE=PASS', host)
        self.assertIn('LAC_PI005_DUPLICATE_RECEIPT_REPLAY=PASS', host)

    def test_profile_probe_unwraps_broker_effect_envelope_before_native_validation(self):
        native = {
            "authority_outcome": "ALLOW",
            "execution_state": "SUCCEEDED",
            "request_id": "effect:fresh",
            "replayed": False,
            "receipt": {"receipt_id": "receipt:stable"},
            "workflow_continuation": {
                "original_request_id": "effect:original",
                "fresh_request_id": "effect:fresh",
            },
        }
        envelope = {"ok": True, "request_id": "effect:fresh", "result": native}
        self.assertEqual(_unwrap_native_effect_result(envelope), native)
        self.assertEqual(_unwrap_native_effect_result(native), native)
        with self.assertRaisesRegex(RuntimeError, "lacks native result"):
            _unwrap_native_effect_result({"ok": True, "request_id": "effect:fresh"})

    def test_authority_core_files_are_not_pi005_payload_targets(self):
        test_script = (ROOT / "scripts/test-pi005").read_text(encoding="utf-8")
        self.assertIn("LAC_PI005_AUTHORITY_CORE_MODIFIED=NO", test_script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
