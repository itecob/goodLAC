import errno
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

    def test_second_server_probe_preserves_active_owner_socket_and_server(self):
        server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        contender = UnixAdminServer(self.service, runtime_dir=self.runtime)
        stop = threading.Event()
        errors = []

        server.start()

        def serve():
            while not stop.is_set():
                try:
                    server.serve_once(timeout=0.05)
                except BaseException as exc:
                    errors.append(exc)
                    return

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            with self.assertRaises(AdminTransportError):
                contender.start()

            # A server instance that never acquired the listener must not unlink
            # another instance's active endpoint during cleanup.
            contender.close()
            stop.set()
            thread.join(timeout=2.0)

            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(server.socket_path.is_socket())

            # The active server must still accept a real owner request after the
            # contender's connect-and-close liveness probe.
            response = json.loads(
                self.transact(server, request_bytes("skills.list", {}))
            )
            self.assertTrue(response["ok"])
        finally:
            stop.set()
            thread.join(timeout=2.0)
            contender.close()
            server.close()

    def test_bind_race_loser_does_not_unlink_competing_owner_socket(self):
        contender = UnixAdminServer(self.service, runtime_dir=self.runtime)
        server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        inspection_complete = threading.Event()
        server_bound = threading.Event()
        contender_errors = []

        original_remove_stale_socket = contender._remove_stale_socket

        def synchronized_stale_inspection():
            original_remove_stale_socket()
            inspection_complete.set()
            if not server_bound.wait(timeout=2.0):
                raise AssertionError("competing administrator server did not bind")

        contender._remove_stale_socket = synchronized_stale_inspection

        def start_contender():
            try:
                contender.start()
            except BaseException as exc:
                contender_errors.append(exc)

        thread = threading.Thread(target=start_contender)
        thread.start()
        try:
            self.assertTrue(inspection_complete.wait(timeout=2.0))

            # B wins the exact TOCTOU window: A has completed stale-path
            # inspection but has not attempted bind() yet.
            server.start()
            owner_info = server.socket_path.lstat()
            owner_identity = (owner_info.st_dev, owner_info.st_ino)
            server_bound.set()

            thread.join(timeout=2.0)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(contender_errors), 1)
            self.assertIsInstance(contender_errors[0], OSError)
            self.assertEqual(contender_errors[0].errno, errno.EADDRINUSE)

            # A's bind-failure cleanup has run. It must not unlink B's endpoint.
            current_info = server.socket_path.lstat()
            self.assertTrue(server.socket_path.is_socket())
            self.assertEqual((current_info.st_dev, current_info.st_ino), owner_identity)

            # B must remain operational for a legitimate owner administration call.
            response = json.loads(
                self.transact(server, request_bytes("skills.list", {}))
            )
            self.assertTrue(response["ok"])
            self.assertEqual(response["result"]["skills"], [])
        finally:
            server_bound.set()
            thread.join(timeout=2.0)
            contender.close()
            server.close()

    def test_insecure_runtime_directory_fails_closed(self):
        self.runtime.chmod(0o755)
        with self.assertRaises(AdminTransportError):
            UnixAdminServer(self.service, runtime_dir=self.runtime)


if __name__ == "__main__":
    unittest.main()
