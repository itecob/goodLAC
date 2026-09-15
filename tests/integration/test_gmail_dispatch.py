import hashlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from packages.core import Approval, EffectRequest, PolicyDecision
from packages.dispatcher import (
    DispatchAdapterError,
    DispatchApprovalRequired,
    DispatchDenied,
    DispatchDuplicateEffect,
    Dispatcher,
)
from packages.effects.gmail import (
    GMAIL_ARCHIVE_ACTION,
    GMAIL_DELETE_ACTION,
    GMAIL_DRAFT_ACTION,
    GMAIL_READ_ACTION,
    GMAIL_SEARCH_ACTION,
    GMAIL_SEND_ACTION,
    GmailEffectAdapter,
    gmail_policy_provider,
)
from packages.state import (
    AgentIdentityRepository,
    ApprovalBindingValidator,
    ApprovalRepository,
    ApprovalValidationError,
    AuditRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
)


NOW = "2026-09-15T05:30:05+00:00"
RESOURCE = "email-account:primary"
PRINCIPAL = "principal:owner"
AGENT = "agent:chief-of-staff"
CANARY_SECRET = "SYNTHETIC_B001_CANARY_NOT_A_REAL_CREDENTIAL"


def fixed_clock():
    observed = datetime.fromisoformat(NOW)
    return lambda: observed


def body_hash(body):
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def message_args(**overrides):
    body = overrides.pop("body", "B001 synthetic message body")
    data = {
        "to": ["owner@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "B001 synthetic subject",
        "body": body,
        "body_sha256": body_hash(body),
        "attachment_hashes": [],
    }
    data.update(overrides)
    return data


def make_request(*, suffix, action, arguments, resource=RESOURCE):
    return EffectRequest.create(
        request_id=f"effect:b001:{suffix}",
        run_id="run:b001",
        principal_id=PRINCIPAL,
        agent_id=AGENT,
        action=action,
        resource=resource,
        arguments=arguments,
        idempotency_key=f"idem:b001:{suffix}",
        created_at="2026-09-15T05:30:00Z",
        expires_at="2026-09-15T05:40:00Z",
    )


class SyntheticSecretProvider:
    def __init__(self):
        self.calls = []

    def resolve(self, credential_ref):
        self.calls.append(credential_ref)
        return CANARY_SECRET


class SyntheticGmailTransport:
    def __init__(self):
        self.calls = []
        self.mutations = {}
        self.send_count = 0
        self.archive_count = 0
        self.draft_count = 0

    def search(self, *, query, max_results):
        self.calls.append(("search", query, max_results))
        return {"messages": [{"id": "m-search-1", "thread_id": "t1"}], "next_page": None}

    def read(self, *, message_id):
        self.calls.append(("read", message_id))
        return {
            "message": {
                "id": message_id,
                "from": "sender@example.com",
                "to": ["owner@example.com"],
                "subject": "Synthetic message",
                "body": "Synthetic body",
            }
        }

    def create_draft(self, *, message, request_id, idempotency_key):
        self.draft_count += 1
        self.calls.append(("draft", request_id, idempotency_key))
        result = {
            "draft_id": f"draft-{self.draft_count}",
            "message_id": f"draft-message-{self.draft_count}",
            "upstream_reference": f"gmail:draft:draft-{self.draft_count}",
        }
        self.mutations[(GMAIL_DRAFT_ACTION, request_id, idempotency_key)] = result
        return result

    def send(self, *, message, request_id, idempotency_key):
        key = (GMAIL_SEND_ACTION, request_id, idempotency_key)
        if key in self.mutations:
            raise AssertionError("synthetic Gmail transport observed duplicate send invocation")
        self.send_count += 1
        self.calls.append(("send", request_id, idempotency_key))
        result = {
            "message_id": f"sent-{self.send_count}",
            "thread_id": f"thread-{self.send_count}",
            "upstream_reference": f"gmail:message:sent-{self.send_count}",
        }
        self.mutations[key] = result
        return result

    def archive(self, *, message_id, request_id, idempotency_key):
        key = (GMAIL_ARCHIVE_ACTION, request_id, idempotency_key)
        if key in self.mutations:
            raise AssertionError("synthetic Gmail transport observed duplicate archive invocation")
        self.archive_count += 1
        self.calls.append(("archive", message_id, request_id, idempotency_key))
        result = {
            "message_id": message_id,
            "archived": True,
            "upstream_reference": f"gmail:message:{message_id}",
        }
        self.mutations[key] = result
        return result

    def reconcile(self, *, action, request_id, idempotency_key, operation):
        self.calls.append(("reconcile", action, request_id, idempotency_key))
        return self.mutations.get((action, request_id, idempotency_key))


class SyntheticTransportFactory:
    def __init__(self, transport):
        self.transport = transport
        self.calls = []

    def create(self, *, account_resource, secret):
        self.calls.append((account_resource, secret))
        if secret != CANARY_SECRET:
            raise AssertionError("unexpected synthetic secret capability")
        return self.transport


class GmailDispatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.store = SQLiteStateStore(base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active(AGENT, PRINCIPAL)
        self.secret_provider = SyntheticSecretProvider()
        self.transport = SyntheticGmailTransport()
        self.factory = SyntheticTransportFactory(self.transport)
        self.adapter = GmailEffectAdapter(
            secret_provider=self.secret_provider,
            transport_factory=self.factory,
            resource=RESOURCE,
            credential_ref="gmail:primary",
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatcher(self):
        return Dispatcher(
            store=self.store,
            policy_provider=gmail_policy_provider(
                principal_id=PRINCIPAL,
                agent_id=AGENT,
                resource=RESOURCE,
            ),
            clock=fixed_clock(),
            lease_seconds=20,
        )

    def dispatch(self, req, *, approval_id=None, suffix="x"):
        EffectRequestRepository(self.store).put(req)
        return self.dispatcher().dispatch(
            req,
            adapter=self.adapter,
            decision_id=f"decision:b001:current:{suffix}",
            lease_id=f"lease:b001:{suffix}",
            executor_id="executor:b001",
            approval_id=approval_id,
        )

    def approval_foundation(self, req, *, suffix):
        EffectRequestRepository(self.store).put(req)
        decision = PolicyDecision.create(
            decision_id=f"decision:b001:foundation:{suffix}",
            request_id=req.request_id,
            decision="REQUIRE_APPROVAL",
            policy_revision="policy:gmail:chief-of-staff:v1",
            reason_codes=("DECISION:REQUIRE_APPROVAL",),
            evaluated_at="2026-09-15T05:30:01Z",
            canonical_request_hash=req.canonical_hash,
        )
        approval = Approval.create(
            approval_id=f"approval:b001:{suffix}",
            request_id=req.request_id,
            policy_decision_id=decision.decision_id,
            canonical_request_hash=req.canonical_hash,
            approver=PRINCIPAL,
            decision="APPROVE",
            scope="ONCE",
            created_at="2026-09-15T05:30:02Z",
            expires_at="2026-09-15T05:35:00Z",
        )
        PolicyDecisionRepository(self.store).put(decision)
        ApprovalRepository(self.store).put(approval)
        return approval

    def test_search_read_and_draft_succeed_through_typed_allow_path(self):
        search = make_request(
            suffix="search",
            action=GMAIL_SEARCH_ACTION,
            arguments={"query": "from:sender@example.com", "max_results": 5},
        )
        search_result = self.dispatch(search, suffix="search")
        self.assertEqual(search_result.data["messages"][0]["id"], "m-search-1")

        read = make_request(suffix="read", action=GMAIL_READ_ACTION, arguments={"message_id": "m1"})
        read_result = self.dispatch(read, suffix="read")
        self.assertEqual(read_result.data["message"]["id"], "m1")

        draft = make_request(suffix="draft", action=GMAIL_DRAFT_ACTION, arguments=message_args())
        draft_result = self.dispatch(draft, suffix="draft")
        self.assertEqual(self.transport.draft_count, 1)
        self.assertTrue(draft_result.upstream_reference.startswith("gmail:draft:"))

        for req in (search, read, draft):
            receipt = EffectReceiptRepository(self.store).get_receipt_for_request(req.request_id)
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt.outcome.value, "SUCCEEDED")

    def test_send_without_exact_approval_cannot_reach_external_effect(self):
        req = make_request(suffix="send-no-approval", action=GMAIL_SEND_ACTION, arguments=message_args())
        EffectRequestRepository(self.store).put(req)
        with self.assertRaises(DispatchApprovalRequired):
            self.dispatcher().dispatch(
                req,
                adapter=self.adapter,
                decision_id="decision:b001:no-approval",
                lease_id="lease:b001:no-approval",
                executor_id="executor:b001",
            )
        self.assertEqual(self.transport.send_count, 0)
        self.assertEqual(self.secret_provider.calls, [])

    def test_send_after_exact_approval_executes_once_and_has_durable_receipt(self):
        req = make_request(suffix="send-approved", action=GMAIL_SEND_ACTION, arguments=message_args())
        approval = self.approval_foundation(req, suffix="send-approved")
        result = self.dispatcher().dispatch(
            req,
            adapter=self.adapter,
            decision_id="decision:b001:send-approved",
            lease_id="lease:b001:send-approved",
            executor_id="executor:b001",
            approval_id=approval.approval_id,
        )
        self.assertEqual(self.transport.send_count, 1)
        self.assertEqual(result.upstream_reference, "gmail:message:sent-1")
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(req.request_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.approval_id, approval.approval_id)
        self.assertEqual(receipt.outcome.value, "SUCCEEDED")
        self.assertEqual(receipt.upstream_reference, "gmail:message:sent-1")

        with self.assertRaises(DispatchDuplicateEffect):
            self.dispatcher().dispatch(
                req,
                adapter=self.adapter,
                decision_id="decision:b001:send-duplicate",
                lease_id="lease:b001:send-duplicate",
                executor_id="executor:b001",
                approval_id=approval.approval_id,
            )
        self.assertEqual(self.transport.send_count, 1)

    def test_archive_requires_approval_and_delete_is_denied(self):
        archive = make_request(
            suffix="archive",
            action=GMAIL_ARCHIVE_ACTION,
            arguments={"message_id": "m1"},
        )
        EffectRequestRepository(self.store).put(archive)
        with self.assertRaises(DispatchApprovalRequired):
            self.dispatcher().dispatch(
                archive,
                adapter=self.adapter,
                decision_id="decision:b001:archive-no-approval",
                lease_id="lease:b001:archive-no-approval",
                executor_id="executor:b001",
            )
        self.assertEqual(self.transport.archive_count, 0)

        approval = self.approval_foundation(
            make_request(
                suffix="archive-approved",
                action=GMAIL_ARCHIVE_ACTION,
                arguments={"message_id": "m2"},
            ),
            suffix="archive-approved",
        )
        approved_req = EffectRequestRepository(self.store).get("effect:b001:archive-approved")
        self.dispatcher().dispatch(
            approved_req,
            adapter=self.adapter,
            decision_id="decision:b001:archive-approved",
            lease_id="lease:b001:archive-approved",
            executor_id="executor:b001",
            approval_id=approval.approval_id,
        )
        self.assertEqual(self.transport.archive_count, 1)

        delete = make_request(
            suffix="delete",
            action=GMAIL_DELETE_ACTION,
            arguments={"message_id": "m1"},
        )
        EffectRequestRepository(self.store).put(delete)
        before_calls = len(self.secret_provider.calls)
        with self.assertRaises(DispatchDenied):
            self.dispatcher().dispatch(
                delete,
                adapter=self.adapter,
                decision_id="decision:b001:delete",
                lease_id="lease:b001:delete",
                executor_id="executor:b001",
            )
        self.assertEqual(len(self.secret_provider.calls), before_calls)

    def test_unknown_action_and_wrong_account_fail_closed_before_credentials(self):
        unknown = make_request(suffix="unknown", action="email.forward", arguments={"message_id": "m1"})
        EffectRequestRepository(self.store).put(unknown)
        with self.assertRaises(DispatchAdapterError):
            self.dispatcher().dispatch(
                unknown,
                adapter=self.adapter,
                decision_id="decision:b001:unknown",
                lease_id="lease:b001:unknown",
                executor_id="executor:b001",
            )

        wrong_account = make_request(
            suffix="wrong-account",
            action=GMAIL_READ_ACTION,
            arguments={"message_id": "m1"},
            resource="email-account:other",
        )
        EffectRequestRepository(self.store).put(wrong_account)
        with self.assertRaises(DispatchAdapterError):
            self.dispatcher().dispatch(
                wrong_account,
                adapter=self.adapter,
                decision_id="decision:b001:wrong-account",
                lease_id="lease:b001:wrong-account",
                executor_id="executor:b001",
            )
        self.assertEqual(self.secret_provider.calls, [])

    def test_credential_canary_never_enters_request_receipt_or_audit(self):
        req = make_request(suffix="credential-isolation", action=GMAIL_READ_ACTION, arguments={"message_id": "m1"})
        self.dispatch(req, suffix="credential-isolation")
        request_record = EffectRequestRepository(self.store).get(req.request_id).to_record()
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(req.request_id)
        audit = AuditRepository(self.store).list_for_request(req.request_id)
        combined = repr(request_record) + repr(receipt.to_record()) + repr([event.details for event in audit])
        self.assertNotIn(CANARY_SECRET, combined)
        self.assertNotIn("gmail:primary", combined)


    def test_exact_approval_is_invalidated_by_each_security_relevant_send_mutation(self):
        h1 = "sha256:" + "1" * 64
        mutation_builders = {
            "account": lambda suffix: make_request(
                suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args(), resource="email-account:other"
            ),
            "to": lambda suffix: make_request(
                suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args(to=["other@example.com"])
            ),
            "cc": lambda suffix: make_request(
                suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args(cc=["cc@example.com"])
            ),
            "bcc": lambda suffix: make_request(
                suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args(bcc=["bcc@example.com"])
            ),
            "subject": lambda suffix: make_request(
                suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args(subject="changed")
            ),
            "body": lambda suffix: make_request(
                suffix=suffix,
                action=GMAIL_SEND_ACTION,
                arguments=message_args(body="changed body", body_sha256=body_hash("changed body")),
            ),
            "body_hash": lambda suffix: make_request(
                suffix=suffix,
                action=GMAIL_SEND_ACTION,
                arguments=message_args(body_sha256="sha256:" + "3" * 64),
            ),
            "attachments": lambda suffix: make_request(
                suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args(attachment_hashes=[h1])
            ),
        }
        for field, build_mutated in mutation_builders.items():
            with self.subTest(field=field):
                suffix = f"approval-mutation-{field}"
                base = make_request(suffix=suffix, action=GMAIL_SEND_ACTION, arguments=message_args())
                approval = self.approval_foundation(base, suffix=suffix)
                mutated = build_mutated(suffix)
                with self.assertRaises(ApprovalValidationError):
                    ApprovalBindingValidator(self.store).validate(
                        approval_id=approval.approval_id,
                        current_request=mutated,
                        at="2026-09-15T05:30:05Z",
                    )
        self.assertEqual(self.transport.send_count, 0)

    def test_all_send_security_fields_are_canonically_bound(self):
        base = make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args())
        body2 = "mutated body"
        h1 = "sha256:" + "1" * 64
        variants = [
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(to=["other@example.com"])),
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(cc=["cc@example.com"])),
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(bcc=["bcc@example.com"])),
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(subject="changed")),
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(body=body2, body_sha256=body_hash(body2))),
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(body_sha256="sha256:" + "3" * 64)),
            make_request(suffix="bind", action=GMAIL_SEND_ACTION, arguments=message_args(attachment_hashes=[h1])),
            make_request(
                suffix="bind",
                action=GMAIL_SEND_ACTION,
                arguments=message_args(),
                resource="email-account:other",
            ),
        ]
        for mutated in variants:
            self.assertNotEqual(base.canonical_hash, mutated.canonical_hash)


if __name__ == "__main__":
    unittest.main()
