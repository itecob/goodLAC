import json
import os
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from packages.sandbox import (
    BubblewrapBackend,
    NetworkMode,
    RootlessPodmanBackend,
    SandboxMount,
    SandboxSpec,
    SandboxSpecError,
    SandboxUnavailable,
    load_selected_backend,
)


class SandboxBackendUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "rootfs"
        (self.root / "usr/bin").mkdir(parents=True)
        (self.root / "workspace/ro").mkdir(parents=True)
        (self.root / "workspace/rw").mkdir(parents=True)
        self.src_ro = Path(self.tmp.name) / "ro"
        self.src_rw = Path(self.tmp.name) / "rw"
        self.src_ro.mkdir()
        self.src_rw.mkdir()
        self.spec = SandboxSpec(
            runtime_root=self.root,
            instance_id="h001-test",
            mounts=(
                SandboxMount(self.src_ro, PurePosixPath("/workspace/ro"), writable=False),
                SandboxMount(self.src_rw, PurePosixPath("/workspace/rw"), writable=True),
            ),
            environment={"PATH": "/usr/bin", "HOME": "/nonexistent"},
            cwd=PurePosixPath("/workspace"),
            network=NetworkMode.NONE,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_bubblewrap_command_encodes_hard_boundary_and_no_host_env_inheritance(self):
        os.environ["LAC_UNIT_SECRET"] = "must-not-appear"
        argv = BubblewrapBackend("/usr/bin/bwrap").build_argv(
            self.spec, ("/usr/bin/agent", "--probe")
        )
        text = "\n".join(argv)
        self.assertIn("--unshare-user", argv)
        self.assertIn("--unshare-pid", argv)
        self.assertIn("--unshare-net", argv)
        self.assertIn("--unshare-ipc", argv)
        self.assertIn("--unshare-uts", argv)
        self.assertIn("--cap-drop", argv)
        self.assertIn("ALL", argv)
        self.assertIn("--die-with-parent", argv)
        self.assertIn("--new-session", argv)
        self.assertIn("--clearenv", argv)
        self.assertIn("--tmpfs", argv)
        self.assertNotIn("sudo", argv)
        self.assertNotIn("LAC_UNIT_SECRET", text)
        ro_index = argv.index(str(self.src_ro))
        rw_index = argv.index(str(self.src_rw))
        self.assertEqual(argv[ro_index - 1], "--ro-bind")
        self.assertEqual(argv[rw_index - 1], "--bind")

    def test_podman_command_is_rootless_read_only_networkless_and_capability_stripped(self):
        argv = RootlessPodmanBackend("/usr/bin/podman").build_argv(
            self.spec, ("/usr/bin/agent", "--probe")
        )
        self.assertIn("--read-only", argv)
        self.assertIn("--network=none", argv)
        self.assertIn("--http-proxy=false", argv)
        self.assertIn("--no-hosts", argv)
        self.assertIn("--no-hostname", argv)
        self.assertIn("--pid=private", argv)
        self.assertIn("--userns=keep-id", argv)
        self.assertIn("--cap-drop=ALL", argv)
        self.assertIn("--security-opt=no-new-privileges", argv)
        rootfs_index = argv.index("--rootfs")
        self.assertEqual(argv[rootfs_index + 1], str(self.root))
        self.assertEqual(argv[rootfs_index + 2], "/usr/bin/agent")
        self.assertNotIn("sudo", argv)
        self.assertFalse(any(item == "LAC_UNIT_SECRET=must-not-appear" for item in argv))

    def test_unknown_network_and_unsafe_mount_shapes_fail_closed(self):
        with self.assertRaises(SandboxSpecError):
            SandboxMount(self.src_ro, PurePosixPath("relative"))
        with self.assertRaises(SandboxSpecError):
            SandboxMount(self.src_ro, PurePosixPath("/proc/escape"))
        with self.assertRaises(SandboxSpecError):
            SandboxSpec(
                runtime_root=self.root,
                instance_id="h001-test",
                cwd=PurePosixPath("/workspace"),
                network="host",  # type: ignore[arg-type]
            )
        with self.assertRaises(SandboxSpecError):
            SandboxSpec(
                runtime_root=self.root,
                instance_id="h001-test",
                mounts=(
                    SandboxMount(self.src_ro, PurePosixPath("/workspace")),
                    SandboxMount(self.src_rw, PurePosixPath("/workspace/rw"), writable=True),
                ),
                cwd=PurePosixPath("/workspace"),
            )

    def test_relative_executable_and_missing_host_inputs_fail_closed(self):
        with self.assertRaises(SandboxSpecError):
            BubblewrapBackend("/usr/bin/bwrap").build_argv(self.spec, ("bash", "-c", "true"))
        missing = SandboxSpec(
            runtime_root=Path(self.tmp.name) / "missing",
            instance_id="h001-missing",
            cwd=PurePosixPath("/"),
        )
        with self.assertRaises(SandboxSpecError):
            BubblewrapBackend("/usr/bin/bwrap").build_argv(missing, ("/bin/true",))

    def test_missing_or_symlinked_mount_target_fails_closed_before_backend_execution(self):
        missing_root = Path(self.tmp.name) / "missing-target-root"
        (missing_root / "workspace/ro").mkdir(parents=True)
        missing_spec = SandboxSpec(
            runtime_root=missing_root,
            instance_id="h001-missing-target",
            mounts=(SandboxMount(self.src_rw, PurePosixPath("/workspace/rw"), writable=True),),
            cwd=PurePosixPath("/workspace"),
        )
        with self.assertRaises(SandboxSpecError):
            BubblewrapBackend("/usr/bin/bwrap").build_argv(
                missing_spec, ("/usr/bin/agent", "--probe")
            )

        symlink_root = Path(self.tmp.name) / "symlink-target-root"
        (symlink_root / "workspace").mkdir(parents=True)
        outside_target = Path(self.tmp.name) / "outside-target"
        outside_target.mkdir()
        (symlink_root / "workspace/rw").symlink_to(outside_target, target_is_directory=True)
        symlink_spec = SandboxSpec(
            runtime_root=symlink_root,
            instance_id="h001-symlink-target",
            mounts=(SandboxMount(self.src_rw, PurePosixPath("/workspace/rw"), writable=True),),
            cwd=PurePosixPath("/workspace"),
        )
        with self.assertRaises(SandboxSpecError):
            BubblewrapBackend("/usr/bin/bwrap").build_argv(
                symlink_spec, ("/usr/bin/agent", "--probe")
            )

    def test_missing_backend_binary_fails_closed_before_execution(self):
        missing = str(Path(self.tmp.name) / "definitely-missing-backend")
        with self.assertRaises(SandboxUnavailable):
            BubblewrapBackend(missing).run(self.spec, ("/usr/bin/agent", "--probe"))
        with self.assertRaises(SandboxUnavailable):
            RootlessPodmanBackend(missing).run(self.spec, ("/usr/bin/agent", "--probe"))

    def test_evidence_selection_requires_all_controls_and_known_backend(self):
        controls = {
            "filesystem_visibility": True,
            "writable_paths": True,
            "process_isolation": True,
            "outbound_network": True,
            "environment_inheritance": True,
            "credential_exposure": True,
            "child_process_containment": True,
            "rootless_user_namespace": True,
            "lifecycle_cleanup": True,
            "failure_mode": True,
        }
        evidence = Path(self.tmp.name) / "evidence.json"
        evidence.write_text(
            json.dumps(
                {
                    "schema": "lac.sandbox-qualification/v1",
                    "status": "PASS",
                    "selected_backend": "bubblewrap",
                    "candidates": {
                        "bubblewrap": {
                            "status": "PASS",
                            "binary": "/usr/bin/bwrap",
                            "controls": controls,
                        }
                    },
                }
            )
        )
        backend = load_selected_backend(evidence)
        self.assertEqual(backend.backend_id, "bubblewrap")

        payload = json.loads(evidence.read_text())
        payload["candidates"]["bubblewrap"]["controls"]["outbound_network"] = False
        evidence.write_text(json.dumps(payload))
        with self.assertRaises(SandboxUnavailable):
            load_selected_backend(evidence)

        payload["candidates"]["bubblewrap"]["controls"]["outbound_network"] = True
        payload["selected_backend"] = "unknown"
        evidence.write_text(json.dumps(payload))
        with self.assertRaises(SandboxUnavailable):
            load_selected_backend(evidence)


if __name__ == "__main__":
    unittest.main()
