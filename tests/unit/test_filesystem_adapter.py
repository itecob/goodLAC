import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from packages.core import EffectRequest, ExecutionLease
from packages.dispatcher import EffectAdapter
from packages.effects.filesystem import (
    FILESYSTEM_ADAPTER_ID,
    FILESYSTEM_CREATE_ACTION,
    FILESYSTEM_DELETE_ACTION,
    FILESYSTEM_READ_ACTION,
    FILESYSTEM_REPLACE_ACTION,
    FilesystemEffectAdapter,
    FilesystemEffectError,
)


BASE = {
    "request_id": "effect:h002-unit",
    "run_id": "run:h002-unit",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": FILESYSTEM_READ_ACTION,
    "resource": "filesystem:workspace",
    "arguments": {"path": "notes/readme.txt"},
    "idempotency_key": "idem:h002-unit",
    "created_at": "2026-09-13T08:00:00Z",
    "expires_at": "2026-09-13T08:10:00Z",
}


def request(**overrides):
    return EffectRequest.create(**{**BASE, **overrides})


class FilesystemAdapterUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "notes").mkdir()
        (self.root / "notes" / "readme.txt").write_text("hello\n", encoding="utf-8")
        self.adapter = FilesystemEffectAdapter(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_adapter_implements_protocol_and_recognizes_only_typed_contract(self):
        self.assertIsInstance(self.adapter, EffectAdapter)
        self.assertEqual(self.adapter.adapter_id, FILESYSTEM_ADAPTER_ID)
        self.assertTrue(self.adapter.supports(request()))
        self.assertTrue(
            self.adapter.supports(
                request(
                    request_id="effect:create",
                    idempotency_key="idem:create",
                    action=FILESYSTEM_CREATE_ACTION,
                    arguments={"path": "notes/new.txt", "content": "new"},
                )
            )
        )
        self.assertTrue(
            self.adapter.supports(
                request(
                    request_id="effect:replace",
                    idempotency_key="idem:replace",
                    action=FILESYSTEM_REPLACE_ACTION,
                    arguments={"path": "notes/readme.txt", "content": "replacement"},
                )
            )
        )
        self.assertTrue(
            self.adapter.supports(
                request(
                    request_id="effect:delete",
                    idempotency_key="idem:delete",
                    action=FILESYSTEM_DELETE_ACTION,
                    arguments={"path": "notes/readme.txt"},
                )
            )
        )

        bad = (
            request(request_id="effect:absolute", idempotency_key="idem:absolute", arguments={"path": "/etc/passwd"}),
            request(request_id="effect:traversal", idempotency_key="idem:traversal", arguments={"path": "../secret"}),
            request(request_id="effect:dot", idempotency_key="idem:dot", arguments={"path": "notes/./readme.txt"}),
            request(request_id="effect:slashes", idempotency_key="idem:slashes", arguments={"path": "notes//readme.txt"}),
            request(request_id="effect:control", idempotency_key="idem:control", arguments={"path": "notes/bad\nname"}),
            request(request_id="effect:resource", idempotency_key="idem:resource", resource="filesystem:other"),
            request(request_id="effect:action", idempotency_key="idem:action", action="filesystem.other"),
            request(request_id="effect:extra", idempotency_key="idem:extra", arguments={"path": "notes/readme.txt", "extra": True}),
            replace(request(), canonical_hash="sha256:" + "f" * 64),
        )
        for candidate in bad:
            with self.subTest(request_id=candidate.request_id):
                self.assertFalse(self.adapter.supports(candidate))

    def test_working_root_must_be_canonical_existing_real_directory(self):
        with self.assertRaises(FilesystemEffectError):
            FilesystemEffectAdapter("relative/path")
        missing = self.root / "missing"
        with self.assertRaises(FilesystemEffectError):
            FilesystemEffectAdapter(missing)
        target = self.root / "real"
        target.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(target, target_is_directory=True)
        with self.assertRaises(FilesystemEffectError):
            FilesystemEffectAdapter(alias)

    def test_delete_has_no_direct_mutation_implementation(self):
        delete = request(
            request_id="effect:delete-direct",
            idempotency_key="idem:delete-direct",
            action=FILESYSTEM_DELETE_ACTION,
            arguments={"path": "notes/readme.txt"},
        )
        lease = ExecutionLease.create(
            lease_id="lease:h002-delete",
            request_id=delete.request_id,
            executor_id="executor:h002",
            issued_at="2026-09-13T08:00:01Z",
            expires_at="2026-09-13T08:00:20Z",
        )
        with self.assertRaises(FilesystemEffectError):
            self.adapter.invoke(delete, lease=lease)
        self.assertEqual((self.root / "notes" / "readme.txt").read_text(encoding="utf-8"), "hello\n")


if __name__ == "__main__":
    unittest.main()
