import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packages.lacctl.client import (
    ADMIN_RESPONSE_SCHEMA,
    LacctlBoundaryError,
    LacctlProtocolError,
    LacctlRequestRejected,
    decode_response_line,
    encode_request,
    resolve_admin_socket_path,
)


class LacctlClientUnitTests(unittest.TestCase):
    def test_request_is_versioned_canonical_and_deterministic(self):
        request_id_1, payload_1 = encode_request("pending.show", {"pending_id": "pending:1"})
        request_id_2, payload_2 = encode_request("pending.show", {"pending_id": "pending:1"})
        self.assertEqual(request_id_1, request_id_2)
        self.assertEqual(payload_1, payload_2)
        parsed = json.loads(payload_1)
        self.assertEqual(parsed["schema"], "lac.admin-request/v1")
        self.assertEqual(parsed["operation"], "pending.show")

    def test_response_rejects_duplicate_unknown_version_and_wrong_request_id(self):
        rid, _ = encode_request("skills.list", {})
        with self.assertRaises(LacctlProtocolError):
            decode_response_line(
                (
                    '{"schema":"lac.admin-response/v1","request_id":"%s","ok":true,'
                    '"ok":true,"result":{},"error":null}\n' % rid
                ).encode(),
                expected_request_id=rid,
            )
        with self.assertRaises(LacctlProtocolError):
            decode_response_line(
                json.dumps(
                    {
                        "schema": ADMIN_RESPONSE_SCHEMA,
                        "request_id": rid,
                        "ok": True,
                        "result": {},
                        "error": None,
                        "authority": True,
                    },
                    separators=(",", ":"),
                ).encode()
                + b"\n",
                expected_request_id=rid,
            )
        with self.assertRaises(LacctlProtocolError):
            decode_response_line(
                json.dumps(
                    {
                        "schema": "lac.admin-response/v2",
                        "request_id": rid,
                        "ok": True,
                        "result": {},
                        "error": None,
                    },
                    separators=(",", ":"),
                ).encode()
                + b"\n",
                expected_request_id=rid,
            )
        with self.assertRaises(LacctlProtocolError):
            decode_response_line(
                json.dumps(
                    {
                        "schema": ADMIN_RESPONSE_SCHEMA,
                        "request_id": rid + ":wrong",
                        "ok": True,
                        "result": {},
                        "error": None,
                    },
                    separators=(",", ":"),
                ).encode()
                + b"\n",
                expected_request_id=rid,
            )

    def test_admin_error_is_preserved_as_rejected_not_success(self):
        rid, _ = encode_request("permissions.list", {})
        response = json.dumps(
            {
                "schema": ADMIN_RESPONSE_SCHEMA,
                "request_id": rid,
                "ok": False,
                "result": None,
                "error": {"code": "ADMIN_STATE_CONFLICT", "message": "conflict"},
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode() + b"\n"
        with self.assertRaises(LacctlRequestRejected) as caught:
            decode_response_line(response, expected_request_id=rid)
        self.assertEqual(caught.exception.code, "ADMIN_STATE_CONFLICT")

    def test_socket_path_requires_owner_private_runtime_and_0600_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            runtime.chmod(0o700)
            lac = runtime / "lac"
            lac.mkdir(mode=0o700)
            endpoint = lac / "admin-v1.sock"
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                listener.bind(str(endpoint))
                os.chmod(endpoint, 0o660)
                with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}, clear=False):
                    with self.assertRaises(LacctlBoundaryError):
                        resolve_admin_socket_path()
                os.chmod(endpoint, 0o600)
                with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}, clear=False):
                    self.assertEqual(resolve_admin_socket_path(), endpoint)
            finally:
                listener.close()


if __name__ == "__main__":
    unittest.main()
