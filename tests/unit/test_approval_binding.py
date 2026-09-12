import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from packages.core import Approval, EffectRequest, PolicyDecision
from packages.state import (
    ApprovalBindingValidator,
    ApprovalRepository,
    ApprovalValidationError,
    EffectRequestRepository,
    PolicyDecisionRepository,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


REQUEST_VALUES = {
    "request_id": "effect:binding-001",
    "run_id": "run:binding-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": "simulated.write",
    "resource": "simulated:alpha",
    "arguments": {"value": 7, "nested": {"enabled": True}},
    "idempotency_key": "idem:binding-001",
    "created_at": "2026-09-11T16:00:00Z",
    "expires_at": "2026-09-11T16:10:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**REQUEST_VALUES, **overrides})


def make_policy_decision(request=None, *, decision="REQUIRE_APPROVAL"):
    request = request or make_request()
    return PolicyDecision.create(
        decision_id="decision:binding-001",
        request_id=request.request_id,
        decision=decision,
        policy_revision="policy:test:v1",
        reason_codes=(f"DECISION:{decision}", "MATCHED_RULE:binding"),
        evaluated_at="2026-09-11T16:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )


def make_approval(request=None, policy_decision=None, **overrides):
    request = request or make_request()
    policy_decision = policy_decision or make_policy_decision(request)
    values = {
        "approval_id": "approval:binding-001",
        "request_id": request.request_id,
        "policy_decision_id": policy_decision.decision_id,
        "canonical_request_hash": request.canonical_hash,
        "approver": "principal:owner",
        "decision": "APPROVE",
        "scope": "ONCE",
        "created_at": "2026-09-11T16:00:02Z",
        "expires_at": "2026-09-11T16:05:00Z",
        "consumed_at": None,
    }
    values.update(overrides)
    return Approval.create(**values)


class ApprovalBindingValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def persist(self, store, request=None, policy_decision=None, approval=None):
        request = request or make_request()
        policy_decision = policy_decision or make_policy_decision(request)
        approval = approval or make_approval(request, policy_decision)
        EffectRequestRepository(store).put(request)
        PolicyDecisionRepository(store).put(policy_decision)
        ApprovalRepository(store).put(approval)
        return request, policy_decision, approval

    def test_exact_unchanged_request_qualifies_without_state_mutation(self) -> None:
        with SQLiteStateStore(self.db) as store:
            request, _, approval = self.persist(store)
            before_changes = store._conn.total_changes
            validated = ApprovalBindingValidator(store).validate(
                approval_id=approval.approval_id,
                current_request=request,
                at="2026-09-11T16:04:59Z",
            )
            self.assertEqual(validated, approval)
            self.assertIsNone(validated.consumed_at)
            self.assertEqual(store._conn.total_changes, before_changes)
            self.assertIsNone(
                store._conn.execute(
                    "SELECT consumed_at FROM approvals WHERE approval_id = ?",
                    (approval.approval_id,),
                ).fetchone()[0]
            )

    def test_reject_expired_consumed_and_unknown_approval_fail_closed(self) -> None:
        cases = (
            ("reject", {"decision": "REJECT"}, "2026-09-11T16:04:00Z", "approval:binding-001"),
            ("expired", {}, "2026-09-11T16:05:00Z", "approval:binding-001"),
            ("consumed", {"consumed_at": "2026-09-11T16:00:03Z"}, "2026-09-11T16:04:00Z", "approval:binding-001"),
            ("unknown", {}, "2026-09-11T16:04:00Z", "approval:missing"),
        )
        for name, approval_overrides, at, approval_id in cases:
            with self.subTest(case=name):
                db = Path(self.tmp.name) / f"{name}.db"
                with SQLiteStateStore(db) as store:
                    request = make_request()
                    policy_decision = make_policy_decision(request)
                    approval = make_approval(request, policy_decision, **approval_overrides)
                    self.persist(store, request, policy_decision, approval)
                    with self.assertRaises(ApprovalValidationError):
                        ApprovalBindingValidator(store).validate(
                            approval_id=approval_id,
                            current_request=request,
                            at=at,
                        )

    def test_all_security_relevant_request_mutations_invalidate_prior_approval(self) -> None:
        base = make_request()
        mutations = {
            "request_id": "effect:binding-other",
            "run_id": "run:binding-other",
            "principal_id": "principal:other",
            "agent_id": "agent:other",
            "action": "simulated.delete",
            "resource": "simulated:other",
            "arguments": {"value": 999},
            "idempotency_key": "idem:binding-other",
            "created_at": "2026-09-11T16:00:01Z",
            "expires_at": "2026-09-11T16:11:00Z",
        }
        with SQLiteStateStore(self.db) as store:
            policy_decision = make_policy_decision(base)
            approval = make_approval(base, policy_decision)
            self.persist(store, base, policy_decision, approval)
            validator = ApprovalBindingValidator(store)
            for field, value in mutations.items():
                with self.subTest(field=field):
                    changed = make_request(**{field: value})
                    self.assertNotEqual(base.canonical_hash, changed.canonical_hash)
                    with self.assertRaises(ApprovalValidationError):
                        validator.validate(
                            approval_id=approval.approval_id,
                            current_request=changed,
                            at="2026-09-11T16:04:00Z",
                        )

    def test_wrong_approval_hash_and_malformed_approval_fail_closed(self) -> None:
        for name, column, value in (
            ("wrong-hash", "canonical_request_hash", "sha256:" + ("0" * 64)),
            ("bad-schema", "schema", "lac.approval/v999"),
        ):
            with self.subTest(case=name):
                db = Path(self.tmp.name) / f"{name}.db"
                with SQLiteStateStore(db) as store:
                    request, _, approval = self.persist(store)
                    with store.transaction() as conn:
                        conn.execute(
                            f"UPDATE approvals SET {column} = ? WHERE approval_id = ?",
                            (value, approval.approval_id),
                        )
                    with self.assertRaises(ApprovalValidationError):
                        ApprovalBindingValidator(store).validate(
                            approval_id=approval.approval_id,
                            current_request=request,
                            at="2026-09-11T16:04:00Z",
                        )

    def test_lost_require_approval_policy_binding_fails_closed(self) -> None:
        with SQLiteStateStore(self.db) as store:
            request, policy_decision, approval = self.persist(store)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE policy_decisions SET decision = 'ALLOW' WHERE decision_id = ?",
                    (policy_decision.decision_id,),
                )
            with self.assertRaises(ApprovalValidationError):
                ApprovalBindingValidator(store).validate(
                    approval_id=approval.approval_id,
                    current_request=request,
                    at="2026-09-11T16:04:00Z",
                )

    def test_noncanonical_current_request_and_invalid_validation_time_fail_closed(self) -> None:
        with SQLiteStateStore(self.db) as store:
            request, _, approval = self.persist(store)
            forged = replace(request, canonical_hash="sha256:" + ("f" * 64))
            validator = ApprovalBindingValidator(store)
            with self.assertRaises(ApprovalValidationError):
                validator.validate(
                    approval_id=approval.approval_id,
                    current_request=forged,
                    at="2026-09-11T16:04:00Z",
                )
            with self.assertRaises(ApprovalValidationError):
                validator.validate(
                    approval_id=approval.approval_id,
                    current_request=request,
                    at="not-a-timestamp",
                )

    def test_validator_has_no_consumption_lease_dispatch_or_execution_surface(self) -> None:
        public = {
            name for name in dir(ApprovalBindingValidator) if not name.startswith("_")
        }
        self.assertEqual(public, {"validate"})
        self.assertEqual(SCHEMA_VERSION, 6)


if __name__ == "__main__":
    unittest.main()
