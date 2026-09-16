import os
import tempfile
import unittest
from pathlib import Path, PurePosixPath

import packages.adapters
from packages.admin import AdminService, UnixAdminServer
from packages.dispatcher import Dispatcher
from packages.effects.shell.adapter import _copy_binary_and_libraries
from packages.sandbox import NetworkMode, SandboxSpec, get_selected_backend
from packages.state import SQLiteStateStore


class P004AdminBoundaryAcceptanceTests(unittest.TestCase):
    def test_runtime_namespaces_expose_no_admin_mutation_surface(self):
        self.assertFalse(hasattr(packages.adapters, "AdminService"))
        self.assertFalse(hasattr(packages.adapters, "CapabilityRegistry"))
        self.assertFalse(hasattr(Dispatcher, "admin"))
        self.assertFalse(hasattr(Dispatcher, "replace_policy_admin"))
        worker = Path("scripts/a003_agent_sandbox.py").read_text(encoding="utf-8")
        self.assertNotIn("admin-v1.sock", worker)
        self.assertNotIn("XDG_RUNTIME_DIR", worker)
        self.assertNotIn("packages.admin", worker)

    def test_synthetic_owner_admin_socket_is_not_visible_inside_selected_governed_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name).resolve()
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            with SQLiteStateStore(root / "controller.db") as store:
                server = UnixAdminServer(AdminService(store, owner_uid=os.getuid()), runtime_dir=runtime)
                server.start()
                try:
                    self.assertTrue(server.socket_path.is_socket())
                    rootfs = root / "sandbox-root"
                    for rel in ("proc", "dev", "tmp"):
                        (rootfs / rel).mkdir(parents=True, exist_ok=True)
                    test_binary = Path("/usr/bin/test").resolve(strict=True)
                    _copy_binary_and_libraries(test_binary, rootfs)
                    backend = get_selected_backend()
                    spec = SandboxSpec(
                        runtime_root=rootfs,
                        instance_id="p004-admin-boundary",
                        mounts=(),
                        environment={"HOME": "/nonexistent", "LC_ALL": "C", "PATH": "/usr/bin"},
                        cwd=PurePosixPath("/"),
                        network=NetworkMode.NONE,
                    )
                    completed = backend.run(
                        spec,
                        [str(test_binary), "-S", str(server.socket_path)],
                        timeout=5,
                        check=False,
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertTrue(server.socket_path.is_socket())
                finally:
                    server.close()


if __name__ == "__main__":
    unittest.main()
