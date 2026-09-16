import ast
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LACCTL = REPO_ROOT / "scripts" / "lacctl"
BANNED_IMPORT_PREFIXES = (
    "packages.state",
    "packages.capabilities",
    "packages.policy",
    "packages.admin",
    "sqlite3",
)


def imports_in(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


class FakeAdminEndpoint:
    def __init__(self, runtime, responder):
        self.runtime = Path(runtime)
        self.lac = self.runtime / "lac"
        self.lac.mkdir(mode=0o700, exist_ok=True)
        self.path = self.lac / "admin-v1.sock"
        self.responder = responder
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(str(self.path))
        os.chmod(self.path, 0o600)
        self.listener.listen(1)
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def _serve(self):
        conn, _ = self.listener.accept()
        with conn:
            data = bytearray()
            while b"\n" not in data:
                chunk = conn.recv(65536)
                if not chunk:
                    return
                data.extend(chunk)
            response = self.responder(bytes(data))
            if response is not None:
                conn.sendall(response)

    def start(self):
        self.thread.start()

    def close(self):
        self.thread.join(timeout=3)
        self.listener.close()


class P005LacctlBoundaryAcceptanceTests(unittest.TestCase):
    def run_lacctl(self, runtime, *args):
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(runtime)
        return subprocess.run(
            [sys.executable, str(LACCTL), *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )

    def test_client_source_has_no_direct_canonical_state_or_admin_service_import(self):
        paths = [
            REPO_ROOT / "packages" / "lacctl" / "client.py",
            REPO_ROOT / "packages" / "lacctl" / "cli.py",
            LACCTL,
        ]
        observed = [name for path in paths for name in imports_in(path)]
        for name in observed:
            self.assertFalse(
                any(name == prefix or name.startswith(prefix + ".") for prefix in BANNED_IMPORT_PREFIXES),
                name,
            )
        source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for forbidden in ("SQLiteStateStore", "controller.db", "--state", "--socket"):
            self.assertNotIn(forbidden, source)

    def test_ambiguous_or_unsupported_cli_arguments_fail_before_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            runtime.chmod(0o700)
            (runtime / "lac").mkdir(mode=0o700)
            bad_revision = self.run_lacctl(runtime, "--json", "permissions", "show", "--revision", "0")
            self.assertEqual(bad_revision.returncode, 5)
            self.assertEqual(json.loads(bad_revision.stdout)["error"]["code"], "INVALID_LACCTL_INPUT")
            socket_override = self.run_lacctl(runtime, "--json", "skills", "list", "--socket", "/tmp/not-allowed")
            self.assertEqual(socket_override.returncode, 5)
            self.assertEqual(json.loads(socket_override.stdout)["error"]["code"], "INVALID_LACCTL_INPUT")

    def test_unavailable_admin_endpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            runtime.chmod(0o700)
            (runtime / "lac").mkdir(mode=0o700)
            result = self.run_lacctl(runtime, "--json", "skills", "list")
            self.assertEqual(result.returncode, 4)
            body = json.loads(result.stdout)
            self.assertFalse(body["ok"])
            self.assertEqual(body["error"]["code"], "ADMIN_ENDPOINT_UNAVAILABLE")

    def test_p004_rejection_is_nonzero_and_machine_readable(self):
        def reject(payload):
            request = json.loads(payload)
            return json.dumps(
                {
                    "schema": "lac.admin-response/v1",
                    "request_id": request["request_id"],
                    "ok": False,
                    "result": None,
                    "error": {"code": "ADMIN_STATE_CONFLICT", "message": "synthetic rejection"},
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode() + b"\n"

        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            runtime.chmod(0o700)
            endpoint = FakeAdminEndpoint(runtime, reject)
            endpoint.start()
            try:
                result = self.run_lacctl(runtime, "permissions", "list", "--json")
            finally:
                endpoint.close()
            self.assertEqual(result.returncode, 3)
            body = json.loads(result.stdout)
            self.assertEqual(body["error"]["code"], "ADMIN_STATE_CONFLICT")

    def test_malformed_or_unsupported_response_fails_closed(self):
        def malformed(payload):
            request = json.loads(payload)
            return json.dumps(
                {
                    "schema": "lac.admin-response/v2",
                    "request_id": request["request_id"],
                    "ok": True,
                    "result": {"skills": []},
                    "error": None,
                },
                separators=(",", ":"),
            ).encode() + b"\n"

        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            runtime.chmod(0o700)
            endpoint = FakeAdminEndpoint(runtime, malformed)
            endpoint.start()
            try:
                result = self.run_lacctl(runtime, "--json", "skills", "list")
            finally:
                endpoint.close()
            self.assertEqual(result.returncode, 5)
            body = json.loads(result.stdout)
            self.assertEqual(body["error"]["code"], "ADMIN_PROTOCOL_FAILURE")


if __name__ == "__main__":
    unittest.main()
