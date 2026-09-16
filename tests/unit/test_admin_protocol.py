import json
import unittest

from packages.admin.protocol import (
    ADMIN_REQUEST_SCHEMA,
    ADMIN_RESPONSE_SCHEMA,
    MAX_ADMIN_MESSAGE_BYTES,
    AdminProtocolError,
    AdminRequest,
    decode_request_line,
    encode_response,
    success_response,
)


class AdminProtocolTests(unittest.TestCase):
    def test_valid_versioned_request_round_trips(self):
        payload = json.dumps(
            {
                "schema": ADMIN_REQUEST_SCHEMA,
                "request_id": "admin:test:list",
                "operation": "skills.list",
                "arguments": {},
            },
            separators=(",", ":"),
        ).encode() + b"\n"
        request = decode_request_line(payload)
        self.assertEqual(request.operation, "skills.list")
        self.assertEqual(request.arguments, {})

    def test_duplicate_keys_unknown_fields_and_unknown_operations_fail_closed(self):
        with self.assertRaises(AdminProtocolError):
            decode_request_line(
                b'{"schema":"lac.admin-request/v1","request_id":"a","request_id":"b",'
                b'"operation":"skills.list","arguments":{}}\n'
            )
        with self.assertRaises(AdminProtocolError):
            decode_request_line(
                b'{"schema":"lac.admin-request/v1","request_id":"a",'
                b'"operation":"skills.list","arguments":{},"authority":true}\n'
            )
        with self.assertRaises(AdminProtocolError):
            AdminRequest.create(request_id="a", operation="runtime.execute", arguments={})

    def test_oversized_and_non_json_material_fail_closed(self):
        with self.assertRaises(AdminProtocolError):
            decode_request_line(b"x" * (MAX_ADMIN_MESSAGE_BYTES + 1))
        with self.assertRaises(AdminProtocolError):
            AdminRequest.create(request_id="a", operation="skills.list", arguments={"bad": object()})

    def test_response_is_versioned_canonical_and_bounded(self):
        encoded = encode_response(success_response("admin:test", {"z": 1, "a": 2}))
        parsed = json.loads(encoded)
        self.assertEqual(parsed["schema"], ADMIN_RESPONSE_SCHEMA)
        self.assertTrue(parsed["ok"])
        self.assertLessEqual(len(encoded), MAX_ADMIN_MESSAGE_BYTES)
        self.assertEqual(encoded, b'{"error":null,"ok":true,"request_id":"admin:test","result":{"a":2,"z":1},"schema":"lac.admin-response/v1"}\n')


if __name__ == "__main__":
    unittest.main()
