from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.adapters.pi import PI_GOVERNED_TOOL_NAMES
from packages.state import EffectReceiptRepository, SQLiteStateStore

BRIDGE = ROOT / "scripts" / "a003_controller_bridge.py"


class A004ControllerObservabilityTests(unittest.TestCase):
    def bridge(self, args: list[str], payload: dict | None = None) -> dict:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), *args],
            input="" if payload is None else json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        value = json.loads(proc.stdout)
        self.assertIsInstance(value, dict)
        return value

    def receipt(self, state: Path, request_id: str) -> dict | None:
        store = SQLiteStateStore(state)
        try:
            found = EffectReceiptRepository(store).get_receipt_for_request(request_id)
            return found.to_record() if found else None
        finally:
            store.close()

    def test_exact_tools_dispatch_through_existing_bridge_and_receipts(self) -> None:
        self.assertEqual(
            tuple(PI_GOVERNED_TOOL_NAMES),
            ("lac_fs_read", "lac_fs_create", "lac_fs_replace", "lac_shell_exec"),
        )
        with tempfile.TemporaryDirectory(prefix="lac-a004-observe-") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            state = root / "controller.db"
            self.bridge(["init", "--state", str(state), "--workspace", str(workspace)])
            run_id = "run:a004:deterministic"
            payloads = [
                {"toolCallId": "a004-create", "toolName": "lac_fs_create", "arguments": {"path": "note.txt", "content": "alpha\n"}},
                {"toolCallId": "a004-read", "toolName": "lac_fs_read", "arguments": {"path": "note.txt"}},
                {"toolCallId": "a004-replace", "toolName": "lac_fs_replace", "arguments": {"path": "note.txt", "content": "alpha\nbeta\n"}},
                {"toolCallId": "a004-shell", "toolName": "lac_shell_exec", "arguments": {"executable": "/usr/bin/cat", "argv": ["note.txt"], "cwd": ".", "environment": {}}},
            ]
            receipt_ids: set[str] = set()
            for payload in payloads:
                response = self.bridge([
                    "effect", "--state", str(state), "--workspace", str(workspace), "--run-id", run_id
                ], payload)
                self.assertTrue(response.get("ok"), response)
                request_id = response.get("request_id")
                self.assertIsInstance(request_id, str)
                receipt = self.receipt(state, request_id)
                self.assertIsNotNone(receipt)
                assert receipt is not None
                self.assertEqual(receipt["outcome"], "SUCCEEDED")
                receipt_ids.add(receipt["receipt_id"])
            self.assertEqual(len(receipt_ids), 4)
            self.assertEqual((workspace / "note.txt").read_text(encoding="utf-8"), "alpha\nbeta\n")

    def test_baseline_ls_empty_argv_lists_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lac-a004-ls-") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "alpha.txt").write_text("alpha\n", encoding="utf-8")
            (workspace / "beta.txt").write_text("beta\n", encoding="utf-8")
            state = root / "controller.db"
            self.bridge(["init", "--state", str(state), "--workspace", str(workspace)])
            response = self.bridge([
                "effect", "--state", str(state), "--workspace", str(workspace), "--run-id", "run:a004:ls"
            ], {
                "toolCallId": "a004-ls",
                "toolName": "lac_shell_exec",
                "arguments": {
                    "executable": "/usr/bin/ls",
                    "argv": [],
                    "cwd": ".",
                    "environment": {},
                },
            })
            self.assertTrue(response.get("ok"), response)
            result = response.get("result")
            self.assertIsInstance(result, dict)
            assert isinstance(result, dict)
            self.assertEqual(set(str(result.get("stdout", "")).split()), {"alpha.txt", "beta.txt"})
            request_id = response.get("request_id")
            self.assertIsInstance(request_id, str)
            receipt = self.receipt(state, request_id)
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(receipt["outcome"], "SUCCEEDED")

    def test_symlink_escape_fails_without_reading_host_fixture_and_records_failed_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lac-a004-boundary-") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            host_only = root / "host-only.txt"
            secret = "SYNTHETIC-A004-HOST-ONLY-CONTENT"
            host_only.write_text(secret + "\n", encoding="utf-8")
            (workspace / "escape").symlink_to(host_only)
            state = root / "controller.db"
            self.bridge(["init", "--state", str(state), "--workspace", str(workspace)])
            response = self.bridge([
                "effect", "--state", str(state), "--workspace", str(workspace), "--run-id", "run:a004:boundary"
            ], {"toolCallId": "a004-escape", "toolName": "lac_fs_read", "arguments": {"path": "escape"}})
            self.assertFalse(response.get("ok"), response)
            self.assertNotIn(secret, json.dumps(response, sort_keys=True))
            self.assertEqual(host_only.read_text(encoding="utf-8"), secret + "\n")
            request_id = response.get("request_id")
            self.assertIsInstance(request_id, str)
            receipt = self.receipt(state, request_id)
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(receipt["outcome"], "FAILED")
            self.assertNotIn(secret, json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
