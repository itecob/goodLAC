import json
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from packages.admin import (
    ADMIN_REQUEST_SCHEMA,
    AdminService,
    AdminTransportError,
    UnixAdminServer,
)
from packages.capabilities import CAPABILITY_MANIFEST_SCHEMA, CapabilityRegistry
from packages.state import SQLiteStateStore


def manifest():
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": [
            {
                "action": "document.read",
                "resource": {"type": "document.local", "selectors": ["document:workspace"]},
                "arguments": {
                    "type": "object",
                    "properties": {"document_id": {"type": "string", "minLength": 1, "maxLength": 128}},
                    "required": ["document_id"],
                    "additionalProperties": False,
                },
                "security_properties": ["read_only"],
            }
        ],
    }


def request_bytes(operation, arguments):
    return (
        json.dumps(
            {
                "schema": ADMIN_REQUEST_SCHEMA,
                "request_id": f"admin:{operation}",
                "operation": operation,
                "arguments": arguments,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )


class WrongUIDServer(UnixAdminServer):
    @staticmethod
    def _peer_identity(connection):
        return (os.getpid(), os.getuid() + 1, os.getgid())


class AdminTransportIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.store = SQLiteStateStore(self.root / "controller.db")
        self.service = AdminService(self.store, owner_uid=os.getuid())

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    @staticmethod
    def transact(server, payload):
        result = {}
        error = []

        def client():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                    conn.connect(str(server.socket_path))
                    conn.sendall(payload)
                    chunks = []
                    while True:
                        part = conn.recv(65536)
                        if not part:
                            break
                        chunks.append(part)
                        if b"\n" in part:
                            break
                    result["payload"] = b"".join(chunks)
            except BaseException as exc:
                error.append(exc)

        thread = threading.Thread(target=client)
        thread.start()
        server.serve_once(timeout=2.0)
        thread.join(timeout=2.0)
        if thread.is_alive():
            raise AssertionError("administrator client thread did not terminate")
        if error:
            raise error[0]
        return result.get("payload", b"")

    def test_owner_socket_is_0600_and_authorized_peer_can_call_api(self):
        server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        server.start()
        try:
            self.assertEqual(server.socket_path.stat().st_mode & 0o777, 0o600)
            response = json.loads(self.transact(server, request_bytes("skills.list", {})))
            self.assertTrue(response["ok"])
            self.assertEqual(response["result"]["skills"], [])
        finally:
            server.close()

    def test_wrong_peer_uid_is_closed_before_dangerous_request_can_mutate(self):
        server = WrongUIDServer(self.service, runtime_dir=self.runtime)
        server.start()
        try:
            payload = request_bytes("skills.register", {"manifest": manifest()})
            # A wrong-UID peer may observe EOF/reset; neither case is authority.
            result = {}

            def client():
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                        conn.connect(str(server.socket_path))
                        conn.sendall(payload)
                        result["received"] = conn.recv(1024)
                except OSError as exc:
                    result["error"] = exc.errno

            thread = threading.Thread(target=client)
            thread.start()
            self.assertTrue(server.serve_once(timeout=2.0))
            thread.join(timeout=2.0)
            self.assertFalse(thread.is_alive())
            self.assertEqual(CapabilityRegistry(self.store).list_latest(), [])
        finally:
            server.close()

    def test_insecure_runtime_directory_fails_closed(self):
        self.runtime.chmod(0o755)
        with self.assertRaises(AdminTransportError):
            UnixAdminServer(self.service, runtime_dir=self.runtime)


if __name__ == "__main__":
    unittest.main()
