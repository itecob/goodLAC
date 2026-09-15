from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class A004SourceContractTests(unittest.TestCase):
    def test_new_surface_is_thin_and_has_no_phase4_capabilities(self) -> None:
        paths = [
            ROOT / "scripts/a004_terminal.py",
            ROOT / "scripts/a004_agent_worker.mjs",
            ROOT / "scripts/a004_freetoken_launcher.py",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
        self.assertNotIn("gmail", combined)
        self.assertNotIn("calendar", combined)
        self.assertNotIn("chief_of_staff", combined)
        self.assertIn("a003_controller_bridge.py", combined)
        self.assertIn("a003_model_provider_stream.py", combined)
        self.assertIn("networkmode.none", combined)
        self.assertIn("governed_pi.mjs", combined)

    def test_shell_model_contract_excludes_argv0_and_pins_baseline_ls_shape(self) -> None:
        terminal = (ROOT / "scripts/a004_terminal.py").read_text(encoding="utf-8")
        governed = (ROOT / "packages/adapters/pi/governed_pi.mjs").read_text(encoding="utf-8")
        contract = "argv contains only arguments after the executable and excludes argv[0]"
        self.assertIn(contract, terminal)
        self.assertIn(contract, governed)
        self.assertIn(
            "executable=/usr/bin/ls, argv=[], cwd=., environment={}",
            terminal,
        )

    def test_worker_does_not_emit_reasoning_in_turn_result(self) -> None:
        worker = (ROOT / "scripts/a004_agent_worker.mjs").read_text(encoding="utf-8")
        marker = 'type: "turn_result"'
        self.assertIn(marker, worker)
        turn_tail = worker[worker.index(marker):]
        self.assertNotIn("reasoning_delta", turn_tail[:1200])
        self.assertNotIn("thinking:", turn_tail[:1200])


if __name__ == "__main__":
    unittest.main(verbosity=2)
