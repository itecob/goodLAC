import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminRequest, AdminService, AdminUnauthorized, UnixAdminServer
from packages.state import EmergencyPauseRepository, SQLiteStateStore

REPO_ROOT = Path(__file__).resolve().parents[2]
LACCTL = REPO_ROOT / "scripts" / "lacctl"


class Pi002EmergencyAdminIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-pi002-emergency-admin-")
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.store = SQLiteStateStore(self.root / "controller.db")
        self.pause = EmergencyPauseRepository(self.store)
        self.pause.resume()
        self.uid = os.getuid()
        self.service = AdminService(self.store, owner_uid=self.uid)
        self.server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        self.server.start()

    def tearDown(self):
        self.server.close()
        self.store.close()
        self.tmp.cleanup()

    def lacctl_json(self, *args):
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(self.runtime)
        process = subprocess.Popen(
            [sys.executable, str(LACCTL), "--json", *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        served = self.server.serve_once(timeout=4)
        try:
            stdout, stderr = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=2)
            self.fail(f"lacctl timed out; stdout={stdout!r} stderr={stderr!r}")
        self.assertTrue(served, f"admin server saw no request; rc={process.returncode} stdout={stdout!r} stderr={stderr!r}")
        self.assertEqual(process.returncode, 0, f"stdout={stdout!r} stderr={stderr!r}")
        self.assertEqual(stderr, "")
        return json.loads(stdout)

    def test_owner_lacctl_status_pause_resume_wraps_canonical_pause_state(self):
        self.assertEqual(self.lacctl_json("emergency", "status"), {"schema": "lac.emergency-pause/v1", "paused": False})
        paused = self.lacctl_json("emergency", "pause")
        self.assertEqual(paused, {"schema": "lac.emergency-pause/v1", "paused": True})
        self.assertTrue(self.pause.get().paused)
        self.assertEqual(self.lacctl_json("emergency", "status")["paused"], True)
        resumed = self.lacctl_json("emergency", "resume")
        self.assertEqual(resumed, {"schema": "lac.emergency-pause/v1", "paused": False})
        self.assertFalse(self.pause.get().paused)

    def test_wrong_peer_uid_cannot_change_emergency_pause(self):
        request = AdminRequest.create(
            request_id="admin:pi002:unauthorized-pause",
            operation="emergency.pause",
            arguments={},
        )
        with self.assertRaises(AdminUnauthorized):
            self.service.execute(request, peer_uid=self.uid + 1)
        self.assertFalse(self.pause.get().paused)


if __name__ == "__main__":
    unittest.main(verbosity=2)
