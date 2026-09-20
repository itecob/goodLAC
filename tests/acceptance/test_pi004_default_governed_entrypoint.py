from __future__ import annotations
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packages.productization import v1

ROOT = Path(__file__).resolve().parents[2]


class Pi004DefaultGovernedEntrypointTests(unittest.TestCase):
    def _archive(self, td: Path) -> Path:
        archive = td / "lac-rc2.tar.gz"
        v1.build_distribution(ROOT, archive)
        return archive

    def _prior_rc1(self, home: Path, *, external_pi_kind: str = "file") -> tuple[dict, bytes, int, object]:
        p = v1.paths(home)
        legacy = tuple(name for name in v1.BIN_NAMES if name != "pi")
        old = p["releases"] / "1.0.0-rc.1"
        (old / "bin").mkdir(parents=True)
        for name in legacy:
            f = old / "bin" / name
            f.write_text("legacy\n", encoding="utf-8")
            f.chmod(0o755)
        p["current"].symlink_to(old)
        p["bin"].mkdir(parents=True, exist_ok=True)
        for name in legacy:
            (p["bin"] / name).symlink_to(p["current"] / "bin" / name)
        p["config"].parent.mkdir(parents=True)
        cfg = v1.default_config(home)
        cfg["runtime"] = "external"
        p["config"].write_text(json.dumps(cfg, sort_keys=True) + "\n", encoding="utf-8")
        p["config"].chmod(0o600)
        p["install_state"].parent.mkdir(parents=True, exist_ok=True)
        prior_state = b'{"schema":"lac.v1-install-state/v1","sentinel":"rc1-exact"}\n'
        p["install_state"].write_bytes(prior_state)
        p["install_state"].chmod(0o600)
        external = p["bin"] / "pi"
        if external_pi_kind == "file":
            external.write_text("#!/bin/sh\necho original-pi\n", encoding="utf-8")
            external.chmod(0o751)
            external_material = ("file", external.read_bytes(), stat.S_IMODE(external.stat().st_mode))
        else:
            external.symlink_to("/opt/original/pi")
            external_material = ("symlink", os.readlink(external))
        return p, prior_state, 0o600, external_material

    def _assert_external(self, path: Path, material: object) -> None:
        if material[0] == "file":
            self.assertTrue(path.is_file() and not path.is_symlink())
            self.assertEqual(path.read_bytes(), material[1])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), material[2])
        else:
            self.assertTrue(path.is_symlink())
            self.assertEqual(os.readlink(path), material[1])

    def test_rc2_upgrade_and_rollback_restore_prior_install_state_and_external_pi_exactly(self):
        for kind in ("file", "symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                td = Path(raw); home = td / "home"; home.mkdir()
                p, prior_state, prior_mode, external_material = self._prior_rc1(home, external_pi_kind=kind)
                archive = self._archive(td)
                state = v1.install_distribution(archive, home)
                self.assertEqual(state["version"], v1.RELEASE_VERSION)
                self.assertTrue((p["bin"] / "pi").is_symlink())
                self.assertEqual((p["bin"] / "pi").resolve(), (p["current"] / "bin" / "pi").resolve())
                self.assertNotEqual(p["install_state"].read_bytes(), prior_state)
                v1.rollback(home)
                self.assertEqual(p["install_state"].read_bytes(), prior_state)
                self.assertEqual(stat.S_IMODE(p["install_state"].stat().st_mode), prior_mode)
                self._assert_external(p["bin"] / "pi", external_material)
                self.assertEqual(p["current"].resolve().name, "1.0.0-rc.1")

    def test_partial_install_failure_restores_prior_install_state_and_external_pi(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw); home = td / "home"; home.mkdir()
            p, prior_state, prior_mode, external_material = self._prior_rc1(home)
            archive = self._archive(td)
            original = v1._write_private_json
            def fail_on_new_install_state(path, value):
                if path == p["install_state"] and isinstance(value, dict) and value.get("version") == v1.RELEASE_VERSION:
                    raise RuntimeError("synthetic post-mutation failure")
                return original(path, value)
            with mock.patch.object(v1, "_write_private_json", side_effect=fail_on_new_install_state):
                with self.assertRaisesRegex(RuntimeError, "synthetic post-mutation failure"):
                    v1.install_distribution(archive, home)
            self.assertEqual(p["install_state"].read_bytes(), prior_state)
            self.assertEqual(stat.S_IMODE(p["install_state"].stat().st_mode), prior_mode)
            self._assert_external(p["bin"] / "pi", external_material)
            self.assertEqual(p["current"].resolve().name, "1.0.0-rc.1")
            self.assertFalse((p["releases"] / v1.RELEASE_VERSION).exists())

    def test_default_pi_dispatch_is_governed_and_dangerous_bypass_is_explicit(self):
        calls = []
        with mock.patch.object(v1, "load_config", return_value={"pi_checkout":"/tmp/pi","workspace":"/w","state":"/s","trace":"/t","runtime":"manage"}), \
             mock.patch.object(v1, "current_app", return_value=Path("/app")), \
             mock.patch.object(v1, "_exec", side_effect=lambda argv, env=None: calls.append((argv,env)) or 0):
            self.assertEqual(v1.launch_pi(None, ["--profile-probe"]), 0)
        self.assertEqual(calls[0][0][0:2], ["python3", "/app/scripts/pi_native_tui_host.py"])
        self.assertNotIn(v1.DANGEROUS_BYPASS_FLAG, calls[0][0])

    def test_dangerous_bypass_verifies_pin_and_executes_exact_pinned_cli(self):
        with tempfile.TemporaryDirectory() as raw:
            td=Path(raw); checkout=td/"pi"; cli=checkout/"packages/coding-agent/dist/bundle/cli.js"; cli.parent.mkdir(parents=True); cli.write_text("x")
            app=td/"app"; (app/"scripts").mkdir(parents=True); (app/"scripts/verify_pi_pin.py").write_text("x")
            calls=[]
            completed=type("Completed",(),{"returncode":0,"stdout":"PASS"})()
            with mock.patch("subprocess.run", return_value=completed), \
                 mock.patch("shutil.which", return_value="/bin/true"), \
                 mock.patch.object(v1, "_exec", side_effect=lambda argv, env=None: calls.append(argv) or 0):
                rc=v1._verify_and_launch_pinned_ungoverned_pi(app,{"pi_checkout":str(checkout)},["--help"],{})
            self.assertEqual(rc,0)
            self.assertEqual(Path(calls[0][0]).resolve(), Path("/bin/true").resolve())
            self.assertEqual(calls[0][1],str(cli))
            self.assertEqual(calls[0][2:], ["--help"])

    def test_governed_shell_cannot_launch_node_or_pi(self):
        source=(ROOT/"scripts/pi_v1_controller_bridge.py").read_text(encoding="utf-8")
        self.assertIn('canonical_binary("ls")',source)
        self.assertIn('canonical_binary("cat")',source)
        self.assertIn('canonical_binary("printf")',source)
        self.assertNotIn('canonical_binary("node")',source)
        self.assertNotIn('canonical_binary("pi")',source)

    def test_shell_function_beats_mise_first_path_and_rollback_restores_shell(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw); home = td / "home"; home.mkdir()
            upstream = home / ".local/share/mise/installs/pi/latest/pi/pi"
            upstream.parent.mkdir(parents=True, exist_ok=True)
            upstream.write_text("#!/bin/sh\necho MISE-ORIGINAL-PI\n", encoding="utf-8")
            upstream.chmod(0o755)
            bashrc = home / ".bashrc"
            original_rc = b'export PATH="$HOME/.local/share/mise/installs/pi/latest/pi:$PATH"\n'
            bashrc.write_bytes(original_rc); bashrc.chmod(0o644)
            p, prior_state, prior_mode, external_material = self._prior_rc1(home)
            archive = self._archive(td)
            with mock.patch.dict(os.environ, {"SHELL": "/bin/bash", "LAC_PI004_TARGET_SHELL": "bash"}, clear=False):
                state = v1.install_distribution(archive, home)
                self.assertEqual(state["shell_integration"]["shell"], "bash")
                fragment = Path(state["shell_integration"]["fragment_path"])
                self.assertTrue(fragment.is_file())
                self.assertIn(v1.SHELL_BLOCK_START.encode(), bashrc.read_bytes())
                env = dict(os.environ)
                env.update({"HOME": str(home), "SHELL": "/bin/bash", "PATH": str(upstream.parent) + os.pathsep + env.get("PATH", "")})
                proc = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-c",
                     f'. "$HOME/{v1.SHELL_FRAGMENT_REL}"; export {v1.LAUNCHER_PROBE_ENV}={v1.LAUNCHER_PROBE_VALUE}; type -t pi; pi --version'],
                    env=env, cwd=home, text=True, capture_output=True, check=False, timeout=10,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("function", proc.stdout)
                self.assertIn(v1.LAUNCHER_PROBE_MARKER, proc.stdout)
                v1.rollback(home)
                self.assertEqual(bashrc.read_bytes(), original_rc)
                self.assertFalse(fragment.exists())
                proc = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-c", "pi --version"],
                    env=env, cwd=home, text=True, capture_output=True, check=False, timeout=10,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("MISE-ORIGINAL-PI", proc.stdout)
            self.assertEqual(p["install_state"].read_bytes(), prior_state)
            self.assertEqual(stat.S_IMODE(p["install_state"].stat().st_mode), prior_mode)
            self._assert_external(p["bin"] / "pi", external_material)
            self.assertEqual(p["current"].resolve().name, "1.0.0-rc.1")

    def test_partial_failure_restores_shell_rc_and_fragment(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw); home = td / "home"; home.mkdir()
            bashrc = home / ".bashrc"; original_rc = b"# owner bashrc\n"; bashrc.write_bytes(original_rc); bashrc.chmod(0o644)
            p, prior_state, prior_mode, external_material = self._prior_rc1(home)
            archive = self._archive(td)
            original = v1._write_private_json
            def fail_on_new_install_state(path, value):
                if path == p["install_state"] and isinstance(value, dict) and value.get("version") == v1.RELEASE_VERSION:
                    raise RuntimeError("synthetic shell post-mutation failure")
                return original(path, value)
            with mock.patch.dict(os.environ, {"SHELL": "/bin/bash", "LAC_PI004_TARGET_SHELL": "bash"}, clear=False), \
                 mock.patch.object(v1, "_write_private_json", side_effect=fail_on_new_install_state):
                with self.assertRaisesRegex(RuntimeError, "synthetic shell post-mutation failure"):
                    v1.install_distribution(archive, home)
            self.assertEqual(bashrc.read_bytes(), original_rc)
            self.assertFalse((home / v1.SHELL_FRAGMENT_REL).exists())
            self.assertEqual(p["install_state"].read_bytes(), prior_state)
            self.assertEqual(stat.S_IMODE(p["install_state"].stat().st_mode), prior_mode)
            self._assert_external(p["bin"] / "pi", external_material)
            self.assertEqual(p["current"].resolve().name, "1.0.0-rc.1")


if __name__ == "__main__": unittest.main()
