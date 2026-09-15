import hashlib
import unittest

from packages.core import EffectRequest, ExecutionLease
from packages.effects.gmail import (
    GMAIL_ARCHIVE_ACTION,
    GMAIL_DELETE_ACTION,
    GMAIL_DRAFT_ACTION,
    GMAIL_READ_ACTION,
    GMAIL_SEARCH_ACTION,
    GMAIL_SEND_ACTION,
    GmailEffectAdapter,
    GmailEffectError,
)


RESOURCE = "email-account:primary"


def body_hash(body):
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def message_args(**overrides):
    body = overrides.pop("body", "Body\nwith exact whitespace.\n")
    data = {
        "to": ["to@example.com"],
        "cc": ["cc@example.com"],
        "bcc": [],
        "subject": "Subject",
        "body": body,
        "body_sha256": body_hash(body),
        "attachment_hashes": [],
    }
    data.update(overrides)
    return data


def request(action, arguments, *, resource=RESOURCE, suffix="x"):
    return EffectRequest.create(
        request_id=f"effect:b001:{suffix}",
        run_id="run:b001",
        principal_id="principal:owner",
        agent_id="agent:chief-of-staff",
        action=action,
        resource=resource,
        arguments=arguments,
        idempotency_key=f"idem:b001:{suffix}",
        created_at="2026-09-15T05:30:00Z",
        expires_at="2026-09-15T05:40:00Z",
    )


def lease(req):
    return ExecutionLease.create(
        lease_id=f"lease:{req.request_id}",
        request_id=req.request_id,
        executor_id="executor:b001",
        issued_at="2026-09-15T05:30:01Z",
        expires_at="2026-09-15T05:30:30Z",
    )


class FakeSecretProvider:
    def __init__(self):
        self.calls = []
        self.secret = object()

    def resolve(self, credential_ref):
        self.calls.append(credential_ref)
        return self.secret


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.reconciled = {}

    def search(self, *, query, max_results):
        self.calls.append(("search", query, max_results))
        return {"messages": [{"id": "m1"}]}

    def read(self, *, message_id):
        self.calls.append(("read", message_id))
        return {"message": {"id": message_id, "subject": "hello", "body": "world"}}

    def create_draft(self, *, message, request_id, idempotency_key):
        self.calls.append(("draft", request_id, idempotency_key, message))
        result = {"draft_id": "d1", "upstream_reference": "gmail:draft:d1"}
        self.reconciled[(GMAIL_DRAFT_ACTION, request_id, idempotency_key)] = result
        return result

    def send(self, *, message, request_id, idempotency_key):
        self.calls.append(("send", request_id, idempotency_key, message))
        result = {"message_id": "sent-1", "upstream_reference": "gmail:message:sent-1"}
        self.reconciled[(GMAIL_SEND_ACTION, request_id, idempotency_key)] = result
        return result

    def archive(self, *, message_id, request_id, idempotency_key):
        self.calls.append(("archive", message_id, request_id, idempotency_key))
        result = {"message_id": message_id, "archived": True, "upstream_reference": f"gmail:message:{message_id}"}
        self.reconciled[(GMAIL_ARCHIVE_ACTION, request_id, idempotency_key)] = result
        return result

    def reconcile(self, *, action, request_id, idempotency_key, operation):
        self.calls.append(("reconcile", action, request_id, idempotency_key))
        return self.reconciled.get((action, request_id, idempotency_key))


class FakeFactory:
    def __init__(self, transport):
        self.transport = transport
        self.calls = []

    def create(self, *, account_resource, secret):
        self.calls.append((account_resource, secret))
        return self.transport


class LeakyTransport(FakeTransport):
    def read(self, *, message_id):
        return {"message": {"id": message_id}, "access_token": "synthetic-canary-not-a-real-token"}


class GmailAdapterUnitTests(unittest.TestCase):
    def setUp(self):
        self.secrets = FakeSecretProvider()
        self.transport = FakeTransport()
        self.factory = FakeFactory(self.transport)
        self.adapter = GmailEffectAdapter(
            secret_provider=self.secrets,
            transport_factory=self.factory,
        )

    def test_supports_exact_bounded_action_shapes_without_resolving_credentials(self):
        cases = [
            request(GMAIL_SEARCH_ACTION, {"query": "from:boss@example.com", "max_results": 10}, suffix="search"),
            request(GMAIL_READ_ACTION, {"message_id": "m1"}, suffix="read"),
            request(GMAIL_DRAFT_ACTION, message_args(), suffix="draft"),
            request(GMAIL_SEND_ACTION, message_args(), suffix="send"),
            request(GMAIL_ARCHIVE_ACTION, {"message_id": "m1"}, suffix="archive"),
            request(GMAIL_DELETE_ACTION, {"message_id": "m1"}, suffix="delete"),
        ]
        for req in cases:
            with self.subTest(action=req.action):
                self.assertTrue(self.adapter.supports(req))
        self.assertEqual(self.secrets.calls, [])
        self.assertEqual(self.factory.calls, [])

    def test_unknown_or_malformed_actions_fail_closed(self):
        self.assertFalse(
            self.adapter.supports(
                request("email.forward", {"message_id": "m1"}, suffix="unknown")
            )
        )
        self.assertFalse(
            self.adapter.supports(
                request(GMAIL_SEARCH_ACTION, {"query": "x"}, suffix="missing-limit")
            )
        )
        bad = message_args(body_sha256="sha256:" + "0" * 64)
        self.assertFalse(self.adapter.supports(request(GMAIL_SEND_ACTION, bad, suffix="bad-body-hash")))
        recipient_injection = message_args(to=["approved@example.com,other@example.com"])
        self.assertFalse(
            self.adapter.supports(
                request(GMAIL_SEND_ACTION, recipient_injection, suffix="recipient-delimiter")
            )
        )

    def test_account_resource_is_part_of_exact_supported_operation(self):
        req = request(
            GMAIL_SEND_ACTION,
            message_args(),
            resource="email-account:other",
            suffix="other-account",
        )
        self.assertFalse(self.adapter.supports(req))

    def test_delete_has_no_adapter_mutation_implementation_and_never_resolves_secret(self):
        req = request(GMAIL_DELETE_ACTION, {"message_id": "m1"}, suffix="delete")
        with self.assertRaises(GmailEffectError):
            self.adapter.invoke(req, lease=lease(req))
        self.assertEqual(self.secrets.calls, [])
        self.assertEqual(self.transport.calls, [])

    def test_send_result_exposes_no_credential_reference_or_secret_material(self):
        req = request(GMAIL_SEND_ACTION, message_args(), suffix="send")
        result = self.adapter.invoke(req, lease=lease(req))
        record = result.to_record()
        text = repr(record)
        self.assertNotIn("gmail:primary", text)
        self.assertNotIn("credential", text.lower())
        self.assertEqual(result.upstream_reference, "gmail:message:sent-1")
        self.assertEqual(self.secrets.calls, ["gmail:primary"])
        self.assertIs(self.factory.calls[0][1], self.secrets.secret)

    def test_provider_credential_shaped_result_is_rejected_before_receipt_boundary(self):
        leaky = LeakyTransport()
        adapter = GmailEffectAdapter(
            secret_provider=self.secrets,
            transport_factory=FakeFactory(leaky),
        )
        req = request(GMAIL_READ_ACTION, {"message_id": "m1"}, suffix="leak")
        with self.assertRaises(GmailEffectError):
            adapter.invoke(req, lease=lease(req))

    def test_mutation_reconciliation_is_read_only_and_does_not_repeat_send(self):
        req = request(GMAIL_SEND_ACTION, message_args(), suffix="reconcile")
        first = self.adapter.invoke(req, lease=lease(req))
        before = len([call for call in self.transport.calls if call[0] == "send"])
        reconciled = self.adapter.reconcile(req, lease=lease(req))
        after = len([call for call in self.transport.calls if call[0] == "send"])
        self.assertEqual(before, 1)
        self.assertEqual(after, 1)
        self.assertEqual(reconciled.upstream_reference, first.upstream_reference)

    def test_security_relevant_send_fields_all_change_canonical_request_hash(self):
        base = request(GMAIL_SEND_ACTION, message_args(), suffix="binding")
        attachment_a = "sha256:" + "1" * 64
        attachment_b = "sha256:" + "2" * 64
        body2 = "Changed body"
        variants = {
            "account": request(GMAIL_SEND_ACTION, message_args(), resource="email-account:other", suffix="binding"),
            "to": request(GMAIL_SEND_ACTION, message_args(to=["other@example.com"]), suffix="binding"),
            "cc": request(GMAIL_SEND_ACTION, message_args(cc=["othercc@example.com"]), suffix="binding"),
            "bcc": request(GMAIL_SEND_ACTION, message_args(bcc=["blind@example.com"]), suffix="binding"),
            "subject": request(GMAIL_SEND_ACTION, message_args(subject="Changed"), suffix="binding"),
            "body": request(GMAIL_SEND_ACTION, message_args(body=body2, body_sha256=body_hash(body2)), suffix="binding"),
            "body_hash": request(GMAIL_SEND_ACTION, message_args(body_sha256="sha256:" + "3" * 64), suffix="binding"),
            "attachments": request(
                GMAIL_SEND_ACTION,
                message_args(attachment_hashes=[attachment_a, attachment_b]),
                suffix="binding",
            ),
        }
        for field, mutated in variants.items():
            with self.subTest(field=field):
                self.assertNotEqual(base.canonical_hash, mutated.canonical_hash)


if __name__ == "__main__":
    unittest.main()
