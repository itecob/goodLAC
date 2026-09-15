import base64
import json
import unittest
from urllib.parse import parse_qs, urlparse

from packages.effects.gmail import GoogleGmailTransportError, GoogleGmailTransportFactory


TOKEN = "SYNTHETIC_GOOGLE_BEARER_NOT_A_REAL_CREDENTIAL"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, request, *, timeout):
        self.calls.append((request, timeout))
        if not self.responses:
            raise AssertionError("unexpected Gmail API call")
        return FakeResponse(self.responses.pop(0))


def decode_raw(raw):
    padded = raw + "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")


class GoogleGmailTransportUnitTests(unittest.TestCase):
    def transport(self, responses):
        opener = FakeOpener(responses)
        factory = GoogleGmailTransportFactory(opener=opener)
        transport = factory.create(account_resource="email-account:primary", secret=TOKEN)
        return transport, opener

    def test_search_uses_bounded_gmail_messages_endpoint_and_bearer_only_in_http_header(self):
        transport, opener = self.transport(
            [{"messages": [{"id": "m1", "threadId": "t1"}], "resultSizeEstimate": 1}]
        )
        result = transport.search(query="from:sender@example.com", max_results=5)
        self.assertEqual(result["messages"], [{"id": "m1", "thread_id": "t1"}])
        req, timeout = opener.calls[0]
        parsed = urlparse(req.full_url)
        self.assertEqual(parsed.path, "/gmail/v1/users/me/messages")
        query = parse_qs(parsed.query)
        self.assertEqual(query["q"], ["from:sender@example.com"])
        self.assertEqual(query["maxResults"], ["5"])
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.headers["Authorization"], "Bearer " + TOKEN)
        self.assertNotIn(TOKEN, repr(result))
        self.assertEqual(timeout, 30.0)

    def test_send_builds_rfc822_message_with_deterministic_request_identity(self):
        transport, opener = self.transport([{"id": "sent1", "threadId": "thread1"}])
        message = {
            "to": ["to@example.com"],
            "cc": ["cc@example.com"],
            "bcc": ["bcc@example.com"],
            "subject": "Subject",
            "body": "Body text",
            "body_sha256": "sha256:" + "0" * 64,
            "attachment_hashes": [],
        }
        result = transport.send(
            message=message,
            request_id="effect:b001:send-real-shape",
            idempotency_key="idem:b001:send-real-shape",
        )
        self.assertEqual(result["upstream_reference"], "gmail:message:sent1")
        req, _ = opener.calls[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertTrue(req.full_url.endswith("/messages/send"))
        payload = json.loads(req.data.decode("utf-8"))
        raw = decode_raw(payload["raw"])
        self.assertIn("To: to@example.com", raw)
        self.assertIn("Cc: cc@example.com", raw)
        self.assertIn("Bcc: bcc@example.com", raw)
        self.assertIn("Subject: Subject", raw)
        self.assertIn("X-LAC-Request-ID: effect:b001:send-real-shape", raw)
        self.assertIn("Message-ID:", raw)
        self.assertIn("<lac.", raw)
        self.assertIn("Body text", raw)
        self.assertNotIn(TOKEN, raw)

    def test_send_rejects_nonempty_attachment_hashes_without_payload_bytes(self):
        transport, opener = self.transport([])
        with self.assertRaises(GoogleGmailTransportError):
            transport.send(
                message={
                    "to": ["to@example.com"],
                    "cc": [],
                    "bcc": [],
                    "subject": "x",
                    "body": "x",
                    "body_sha256": "sha256:" + "0" * 64,
                    "attachment_hashes": ["sha256:" + "1" * 64],
                },
                request_id="effect:b001:attachment",
                idempotency_key="idem:b001:attachment",
            )
        self.assertEqual(opener.calls, [])

    def test_archive_and_reconciliation_verify_inbox_label_absence(self):
        transport, opener = self.transport(
            [
                {"id": "m1", "labelIds": ["SENT"]},
                {"id": "m1", "labelIds": ["SENT"]},
            ]
        )
        result = transport.archive(
            message_id="m1",
            request_id="effect:b001:archive",
            idempotency_key="idem:b001:archive",
        )
        self.assertTrue(result["archived"])
        reconciled = transport.reconcile(
            action="email.archive",
            request_id="effect:b001:archive",
            idempotency_key="idem:b001:archive",
            operation={"action": "email.archive", "message_id": "m1"},
        )
        self.assertTrue(reconciled["archived"])
        self.assertEqual(opener.calls[0][0].get_method(), "POST")
        self.assertEqual(opener.calls[1][0].get_method(), "GET")

    def test_read_decodes_plain_text_message_without_exposing_http_credential(self):
        body = base64.urlsafe_b64encode(b"hello world").decode("ascii").rstrip("=")
        transport, _ = self.transport(
            [
                {
                    "id": "m1",
                    "threadId": "t1",
                    "labelIds": ["INBOX"],
                    "snippet": "hello",
                    "payload": {
                        "mimeType": "text/plain",
                        "headers": [
                            {"name": "From", "value": "from@example.com"},
                            {"name": "Subject", "value": "Hi"},
                        ],
                        "body": {"data": body},
                    },
                }
            ]
        )
        result = transport.read(message_id="m1")
        self.assertEqual(result["message"]["body"], "hello world")
        self.assertEqual(result["message"]["subject"], "Hi")
        self.assertNotIn(TOKEN, repr(result))

    def test_factory_rejects_missing_bearer_capability_without_echoing_secret_material(self):
        factory = GoogleGmailTransportFactory(opener=FakeOpener([]))
        with self.assertRaises(GoogleGmailTransportError) as ctx:
            factory.create(account_resource="email-account:primary", secret=object())
        self.assertNotIn(TOKEN, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
