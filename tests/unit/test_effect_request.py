import tempfile
import unittest
from pathlib import Path

from packages.core import (
    EFFECT_REQUEST_SCHEMA,
    EffectRequest,
    EffectRequestError,
    UnsupportedEffectRequestSchema,
)
from packages.state import (
    EffectRequestIdentityConflict,
    EffectRequestRepository,
    SQLiteStateStore,
    StateStoreError,
)


BASE = {
    "request_id": "effect:001",
    "run_id": "run:001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": "simulated.write",
    "resource": "simulated:alpha",
    "arguments": {"z": 2, "nested": {"b": True, "a": [1, "x"]}},
    "idempotency_key": "idem:001",
    "created_at": "2026-09-10T18:00:00Z",
    "expires_at": "2026-09-10T18:05:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**BASE, **overrides})


class EffectRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_semantically_identical_arguments_hash_identically(self) -> None:
        left = make_request(arguments={"a": 1, "b": {"x": 2, "y": 3}})
        right = make_request(arguments={"b": {"y": 3, "x": 2}, "a": 1})
        self.assertEqual(left.arguments_json, right.arguments_json)
        self.assertEqual(left.canonical_hash, right.canonical_hash)
        self.assertEqual(left.canonical_json(), right.canonical_json())

    def test_all_security_relevant_fields_participate_in_hash(self) -> None:
        base = make_request()
        mutations = {
            "request_id": "effect:other",
            "run_id": "run:other",
            "principal_id": "principal:other",
            "agent_id": "agent:other",
            "action": "simulated.delete",
            "resource": "simulated:other",
            "arguments": {"z": 999},
            "idempotency_key": "idem:other",
            "created_at": "2026-09-10T18:00:01Z",
            "expires_at": "2026-09-10T18:06:00Z",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                changed = make_request(**{field: value})
                self.assertNotEqual(base.canonical_hash, changed.canonical_hash)

    def test_schema_is_versioned_and_unknown_schema_fails_closed(self) -> None:
        self.assertEqual(make_request().schema, EFFECT_REQUEST_SCHEMA)
        with self.assertRaises(UnsupportedEffectRequestSchema):
            make_request(schema="lac.effect-request/v999")

    def test_required_text_and_timestamp_validation_fail_closed(self) -> None:
        for field in (
            "request_id", "run_id", "principal_id", "agent_id", "action",
            "resource", "idempotency_key",
        ):
            with self.subTest(field=field):
                with self.assertRaises(EffectRequestError):
                    make_request(**{field: ""})
        with self.assertRaises(EffectRequestError):
            make_request(created_at="2026-09-10T18:00:00")
        with self.assertRaises(EffectRequestError):
            make_request(expires_at="2026-09-10T17:59:59Z")

    def test_non_canonical_json_values_are_rejected(self) -> None:
        bad_values = [
            {1: "non-string-key"},
            {"x": float("nan")},
            {"x": float("inf")},
            {"x": {1, 2}},
            {"x": b"secret"},
        ]
        for arguments in bad_values:
            with self.subTest(arguments=repr(arguments)):
                with self.assertRaises(EffectRequestError):
                    make_request(arguments=arguments)

    def test_arguments_are_not_mutable_through_returned_property(self) -> None:
        request = make_request()
        copy = request.arguments
        copy["z"] = 999
        self.assertEqual(request.arguments["z"], 2)
        self.assertEqual(request.canonical_hash, make_request().canonical_hash)

    def test_persisted_request_survives_restart(self) -> None:
        request = make_request()
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request)
        with SQLiteStateStore(self.db) as reopened:
            loaded = EffectRequestRepository(reopened).get(request.request_id)
            self.assertEqual(loaded, request)

    def test_identical_duplicate_request_id_is_idempotent(self) -> None:
        request = make_request()
        with SQLiteStateStore(self.db) as store:
            repo = EffectRequestRepository(store)
            first = repo.put(request)
            second = repo.put(make_request())
            self.assertEqual(first, second)
            count = store._conn.execute(
                "SELECT COUNT(*) FROM effect_requests WHERE request_id = ?",
                (request.request_id,),
            ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_duplicate_request_id_cannot_overwrite_different_request(self) -> None:
        with SQLiteStateStore(self.db) as store:
            repo = EffectRequestRepository(store)
            repo.put(make_request())
            with self.assertRaises(EffectRequestIdentityConflict):
                repo.put(make_request(action="simulated.other"))
            loaded = repo.get(BASE["request_id"])
            self.assertEqual(loaded.action, BASE["action"])

    def test_persisted_hash_corruption_fails_closed(self) -> None:
        request = make_request()
        with SQLiteStateStore(self.db) as store:
            repo = EffectRequestRepository(store)
            repo.put(request)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE effect_requests SET canonical_hash = ? WHERE request_id = ?",
                    ("sha256:" + ("0" * 64), request.request_id),
                )
            with self.assertRaises(StateStoreError):
                repo.get(request.request_id)


if __name__ == "__main__":
    unittest.main()
