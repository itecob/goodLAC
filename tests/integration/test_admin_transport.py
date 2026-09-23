import errno
import fcntl
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

    @staticmethod
    def bind_server_endpoint_without_start(server):
        """Test-only raw bind that intentionally bypasses startup serialization."""
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        old_umask = os.umask(0o077)
        try:
            listener.bind(str(server.socket_path))
        finally:
            os.umask(old_umask)
        os.chmod(server.socket_path, 0o600)
        listener.listen(8)
        info = server.socket_path.lstat()
        identity = (info.st_dev, info.st_ino)
        server._listener = listener
        server._socket_identity = identity
        return identity

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

        original_remove_stale_socket = contender._remove_stale_socket_serialized

        def synchronized_stale_inspection():
            original_remove_stale_socket()
            inspection_complete.set()
            if not server_bound.wait(timeout=2.0):
                raise AssertionError("competing administrator server did not bind")

        contender._remove_stale_socket_serialized = synchronized_stale_inspection

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

    def test_stale_cleanup_does_not_unlink_replacement_owner_socket(self):
        contender = UnixAdminServer(self.service, runtime_dir=self.runtime)
        server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        classification_complete = threading.Event()
        server_bound = threading.Event()
        contender_errors = []
        classified_identity = {}
        stale_identity_fd = None

        contender._prepare_parent()
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(str(contender.socket_path))
        stale.close()
        initial_info = contender.socket_path.lstat()
        initial_identity = (initial_info.st_dev, initial_info.st_ino)

        original_identity_bound_unlink = contender._unlink_stale_socket_if_same_identity

        def synchronized_identity_bound_unlink(stale_identity):
            classified_identity["value"] = stale_identity
            classification_complete.set()
            if not server_bound.wait(timeout=2.0):
                raise AssertionError("replacement administrator server did not bind")
            return original_identity_bound_unlink(stale_identity)

        contender._unlink_stale_socket_if_same_identity = synchronized_identity_bound_unlink

        def start_contender():
            try:
                contender.start()
            except BaseException as exc:
                contender_errors.append(exc)

        thread = threading.Thread(target=start_contender)
        thread.start()
        try:
            self.assertTrue(classification_complete.wait(timeout=2.0))
            self.assertEqual(classified_identity.get("value"), initial_identity)

            # A has classified the exact stale socket but has not performed its
            # final identity-bound removal. B replaces it and acquires the path.
            stale_identity_fd = os.open(
                contender.socket_path, os.O_PATH | os.O_NOFOLLOW
            )
            contender.socket_path.unlink()
            owner_identity = self.bind_server_endpoint_without_start(server)
            self.assertNotEqual(owner_identity, initial_identity)
            server_bound.set()

            thread.join(timeout=2.0)
            self.assertFalse(thread.is_alive())
            if stale_identity_fd is not None:
                os.close(stale_identity_fd)
                stale_identity_fd = None
            self.assertEqual(len(contender_errors), 1)
            self.assertIsInstance(contender_errors[0], AdminTransportError)

            # A must not unlink the replacement pathname. B keeps the exact
            # identity it acquired and remains reachable by a legitimate owner.
            current_info = server.socket_path.lstat()
            self.assertEqual((current_info.st_dev, current_info.st_ino), owner_identity)
            response = json.loads(
                self.transact(server, request_bytes("skills.list", {}))
            )
            self.assertTrue(response["ok"])
            self.assertEqual(response["result"]["skills"], [])
        finally:
            server_bound.set()
            thread.join(timeout=2.0)
            if stale_identity_fd is not None:
                os.close(stale_identity_fd)
            contender.close()
            server.close()

    def test_final_validation_to_unlink_window_serializes_competing_owner_start(self):
        contender = UnixAdminServer(self.service, runtime_dir=self.runtime)
        server = UnixAdminServer(self.service, runtime_dir=self.runtime)
        final_validation_complete = threading.Event()
        allow_unlink = threading.Event()
        server_lock_attempted = threading.Event()
        server_lock_acquired = threading.Event()
        server_bound = threading.Event()
        contender_errors = []
        server_errors = []

        contender._prepare_parent()
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(str(contender.socket_path))
        stale.close()
        initial_info = contender.socket_path.lstat()
        initial_identity = (initial_info.st_dev, initial_info.st_ino)

        original_final_validation = contender._stale_socket_identity_is_current

        def synchronized_final_validation(stale_identity):
            result = original_final_validation(stale_identity)
            if result:
                final_validation_complete.set()
                if not allow_unlink.wait(timeout=2.0):
                    raise AssertionError("final stale-socket unlink was not released")
            return result

        contender._stale_socket_identity_is_current = synchronized_final_validation

        original_serialized_cleanup = contender._remove_stale_socket_serialized

        def synchronized_serialized_cleanup():
            original_serialized_cleanup()
            # A has released stale-removal serialization but has not entered its
            # separately serialized bind phase. Let B win that safe bind race.
            if not server_bound.wait(timeout=2.0):
                raise AssertionError("competing administrator server did not bind after stale cleanup")

        contender._remove_stale_socket_serialized = synchronized_serialized_cleanup

        original_server_lock = server._acquire_socket_directory_lock

        def synchronized_server_lock():
            server_lock_attempted.set()
            lock_fd = original_server_lock()
            server_lock_acquired.set()
            return lock_fd

        server._acquire_socket_directory_lock = synchronized_server_lock

        def start_contender():
            try:
                contender.start()
            except BaseException as exc:
                contender_errors.append(exc)

        def start_server():
            try:
                server.start()
                server_bound.set()
            except BaseException as exc:
                server_errors.append(exc)
                server_bound.set()

        contender_thread = threading.Thread(target=start_contender)
        contender_thread.start()
        server_thread = None
        try:
            self.assertTrue(final_validation_complete.wait(timeout=2.0))

            # A is paused after its final stale identity/type/owner validation and
            # before destructive unlink. The directory lock is held at exactly
            # that former race window.
            lock_fd = os.open(
                contender.socket_path.parent,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            )
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(lock_fd)

            # B enters the normal LAC startup path while A is paused. B cannot
            # acquire lifecycle serialization (and therefore cannot bind) until A
            # finishes the stale removal operation.
            server_thread = threading.Thread(target=start_server)
            server_thread.start()
            self.assertTrue(server_lock_attempted.wait(timeout=2.0))
            self.assertFalse(server_lock_acquired.wait(timeout=0.05))
            self.assertFalse(server_bound.is_set())

            allow_unlink.set()

            contender_thread.join(timeout=2.0)
            server_thread.join(timeout=2.0)
            self.assertFalse(contender_thread.is_alive())
            self.assertFalse(server_thread.is_alive())
            self.assertEqual(server_errors, [])
            self.assertEqual(len(contender_errors), 1)
            self.assertIsInstance(contender_errors[0], OSError)
            self.assertEqual(contender_errors[0].errno, errno.EADDRINUSE)

            owner_info = server.socket_path.lstat()
            owner_identity = (owner_info.st_dev, owner_info.st_ino)
            self.assertEqual(owner_identity, server._socket_identity)

            # A's failed bind establishes no cleanup authority. B keeps the exact
            # pathname identity it acquired and remains operational for the owner.
            current_info = server.socket_path.lstat()
            self.assertEqual((current_info.st_dev, current_info.st_ino), owner_identity)
            response = json.loads(
                self.transact(server, request_bytes("skills.list", {}))
            )
            self.assertTrue(response["ok"])
            self.assertEqual(response["result"]["skills"], [])
        finally:
            allow_unlink.set()
            server_bound.set()
            contender_thread.join(timeout=2.0)
            if server_thread is not None:
                server_thread.join(timeout=2.0)
            contender.close()
            server.close()

    def test_insecure_runtime_directory_fails_closed(self):
        self.runtime.chmod(0o755)
        with self.assertRaises(AdminTransportError):
            UnixAdminServer(self.service, runtime_dir=self.runtime)


if __name__ == "__main__":
    unittest.main()
