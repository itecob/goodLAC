from __future__ import annotations
import json
import os
import stat
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from packages.productization import v1
from scripts import a004_freetoken_launcher as managed_runtime

ROOT = Path(__file__).resolve().parents[2]


class V001ProductizationTests(unittest.TestCase):
    def _build(self, td: Path) -> Path:
        archive = td / "lac-v1.tar.gz"
        first = v1.build_distribution(ROOT, archive)
        copy = td / "lac-v1-copy.tar.gz"
        second = v1.build_distribution(ROOT, copy)
        self.assertEqual(first, second)
        self.assertEqual(archive.read_bytes(), copy.read_bytes())
        return archive

    def test_reproducible_distribution_and_clean_user_install(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw); archive = self._build(td); home = td / "home"; home.mkdir()
            with tarfile.open(archive, "r:gz") as tf:
                names = tf.getnames()
                self.assertFalse(any("/.git/" in f"/{name}/" for name in names))
                self.assertTrue(any(name.endswith("/app/scripts/lac-pi") for name in names))
                self.assertTrue(any(name.endswith("/bin/lac-owner") for name in names))
            state = v1.install_distribution(archive, home)
            self.assertEqual(state["version"], v1.RELEASE_VERSION)
            p = v1.paths(home)
            self.assertTrue(p["current"].is_symlink())
            for name in v1.BIN_NAMES:
                self.assertTrue((p["bin"] / name).is_symlink(), name)
            self.assertEqual(stat.S_IMODE(p["config"].stat().st_mode), 0o600)
            cfg = v1.load_config(home)
            self.assertEqual(cfg["runtime"], "manage")
            self.assertFalse((home / ".config/systemd/user").exists())
            self.assertFalse(state["database_migrated"])
            # Static-doctor success must not depend on whatever tools happen to
            # be installed on the machine running this acceptance test. Model
            # the documented supported host prerequisites explicitly.
            required_bins = {"git", "node", "bwrap", "fd", "rg"}

            def fake_which(name: str):
                return "/usr/bin/true" if name in required_bins else None

            with mock.patch.object(v1.shutil, "which", side_effect=fake_which), \
                 mock.patch.object(v1, "_node_requirement", return_value=(True, "v22.19.0")):
                doctor = v1.doctor(home, static_only=True)

            self.assertFalse(doctor["persistent_service_autostart"])
            self.assertTrue(doctor["default_pi_is_governed"])
            self.assertTrue(doctor["dangerous_bypass_is_explicit"])
            self.assertTrue(doctor["node"])
            self.assertTrue(doctor["node_version"])
            self.assertEqual(doctor["node_version_observed"], "v22.19.0")
            self.assertTrue(doctor["ok"])
            v1.rollback(home)
            self.assertEqual(list(home.iterdir()), [])

    def test_node_minimum_version_parser_is_exact(self):
        self.assertEqual(v1._parse_semver_triplet("v22.19.0"), (22, 19, 0))
        self.assertEqual(v1._parse_semver_triplet("22.23.2"), (22, 23, 2))
        self.assertIsNone(v1._parse_semver_triplet("22.18"))
        self.assertLess((22, 18, 9), v1.NODE_MIN_VERSION)
        self.assertGreaterEqual((22, 19, 0), v1.NODE_MIN_VERSION)

    def test_managed_endpoint_requires_exact_resolvable_model_root(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            home.mkdir()
            assets = managed_runtime.runtime_assets(home)
            assets.model_snapshot.mkdir(parents=True)
            other_root = home / "other-model-snapshot"
            other_root.mkdir()

            health = {
                "status": "ok",
                "maintenance": "serving",
                "version": managed_runtime.FREETOKEN_VERSION,
                "model": managed_runtime.SERVED_MODEL_ID,
            }

            def probe(root_marker=Ellipsis):
                model = {"id": managed_runtime.SERVED_MODEL_ID}
                if root_marker is not Ellipsis:
                    model["root"] = root_marker
                models = {"data": [model]}
                with mock.patch.object(
                    managed_runtime,
                    "_http_json",
                    side_effect=[health, models],
                ):
                    return managed_runtime.probe_exact_endpoint(assets)

            exact, detail = probe(str(assets.model_snapshot))
            self.assertTrue(exact)
            self.assertEqual(detail, "exact accepted endpoint")

            exact, detail = probe(str(other_root))
            self.assertFalse(exact)
            self.assertIn("model snapshot mismatch", detail)

            exact, detail = probe()
            self.assertFalse(exact)
            self.assertIn("model snapshot root unavailable or invalid", detail)

            for malformed in ("", 7, {"path": str(assets.model_snapshot)}):
                with self.subTest(malformed=malformed):
                    exact, detail = probe(malformed)
                    self.assertFalse(exact)
                    self.assertIn("model snapshot root unavailable or invalid", detail)

            exact, detail = probe(str(home / "does-not-exist"))
            self.assertFalse(exact)
            self.assertIn("model snapshot root unavailable or invalid", detail)

    def test_config_is_bounded_and_owner_ux_is_admin_api_alias_only(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"; home.mkdir()
            cfg = v1.load_config(home)
            changed = v1.set_config("runtime", "external", home)
            self.assertEqual(changed["runtime"], "external")
            with self.assertRaises(v1.ProductizationError): v1.set_config("authority", "ALLOW", home)
            with self.assertRaises(v1.ProductizationError): v1.set_config("runtime", "unsafe", home)
            self.assertEqual(set(cfg), {"schema", *v1.CONFIG_KEYS})

    def test_upgrade_backup_and_rollback_restore_supported_preinstall_surface(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw); archive = self._build(td); home = td / "home"; home.mkdir(); p = v1.paths(home)
            p["releases"].mkdir(parents=True); old = p["releases"] / "0.9.0"; (old / "bin").mkdir(parents=True)
            legacy_names = tuple(name for name in v1.BIN_NAMES if name != "pi")
            for name in legacy_names: (old / "bin" / name).write_text("old\n")
            p["current"].symlink_to(old)
            p["bin"].mkdir(parents=True)
            for name in legacy_names: (p["bin"] / name).symlink_to(p["current"] / "bin" / name)
            p["config"].parent.mkdir(parents=True); old_cfg = v1.default_config(home); old_cfg["runtime"]="external"
            p["config"].write_text(json.dumps(old_cfg)+"\n"); p["config"].chmod(0o600)
            p["install_state"].parent.mkdir(parents=True, exist_ok=True)
            p["install_state"].write_text(json.dumps({"schema": v1.INSTALL_SCHEMA, "version": "0.9.0"})+"\n")
            p["install_state"].chmod(0o600)
            v1.install_distribution(archive, home)
            self.assertEqual(v1.load_config(home)["runtime"], "external")
            result = v1.rollback(home)
            self.assertTrue(result["rolled_back"])
            self.assertEqual(p["current"].resolve(), old.resolve())
            self.assertEqual(v1.load_config(home)["runtime"], "external")
            self.assertFalse((p["releases"] / v1.RELEASE_VERSION).exists())

    def test_database_is_backed_up_but_not_migrated_or_rewritten(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw); archive = self._build(td); home = td / "home"; home.mkdir(); p = v1.paths(home)
            p["controller_state"].parent.mkdir(parents=True)
            db = sqlite3.connect(p["controller_state"]); db.execute("create table sentinel(v text)"); db.execute("insert into sentinel values ('keep')"); db.commit(); db.close()
            before = p["controller_state"].read_bytes()
            state = v1.install_distribution(archive, home)
            self.assertEqual(before, p["controller_state"].read_bytes())
            backup = Path(state["backup_dir"]) / "controller.db"
            self.assertTrue(backup.exists())
            db = sqlite3.connect(backup); self.assertEqual(db.execute("select v from sentinel").fetchone()[0], "keep"); db.close()
            self.assertFalse(state["database_migrated"])

    def test_installed_wrappers_reference_only_installed_app_and_accepted_surfaces(self):
        with tempfile.TemporaryDirectory() as raw:
            td=Path(raw); archive=self._build(td); home=td/"home"; home.mkdir(); v1.install_distribution(archive, home); p=v1.paths(home)
            for name in v1.BIN_NAMES:
                target=(p["bin"]/name).resolve(strict=True)
                self.assertTrue(str(target).startswith(str((p["releases"]/v1.RELEASE_VERSION).resolve())))
            help_proc=subprocess.run([str(p["bin"]/"lac-owner"), "help"], env={**os.environ,"HOME":str(home)}, text=True, capture_output=True, check=False)
            self.assertEqual(help_proc.returncode,0,help_proc.stderr)
            self.assertIn("lacctl",help_proc.stdout)
            self.assertNotIn("register",help_proc.stdout.lower())

            ctl_help=subprocess.run(
                [str(p["bin"]/"lacctl"), "--json", "--help"],
                env={**os.environ,"HOME":str(home)},
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(ctl_help.returncode,0,ctl_help.stderr)
            self.assertIn("--json",ctl_help.stdout)

            owner_option_help=subprocess.run(
                [str(p["bin"]/"lac-owner"), "permissions", "set", "--help"],
                env={**os.environ,"HOME":str(home)},
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(owner_option_help.returncode,0,owner_option_help.stderr)
            self.assertIn("--file",owner_option_help.stdout)


if __name__ == "__main__": unittest.main()
