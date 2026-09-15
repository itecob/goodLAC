from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.a004_terminal import A004InputRejected, validate_terminal_input


class A004TerminalInputTests(unittest.TestCase):
    def test_residual_control_characters_are_rejected_before_model_path(self) -> None:
        for value in (
            "plain\x1b[Darrow",
            "plain\x00nul",
            "plain\x7fdel",
            "plain\u0085c1",
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises(A004InputRejected):
                    validate_terminal_input(value)
        self.assertEqual(validate_terminal_input("ordinary text\twith tab"), "ordinary text\twith tab")

    def test_left_arrow_edits_line_instead_of_submitting_escape_sequence(self) -> None:
        code = (
            "from scripts.a004_terminal import read_terminal_input, validate_terminal_input; "
            "value = validate_terminal_input(read_terminal_input('lac> ')); "
            "print('RESULT=' + repr(value), flush=True)"
        )
        master_fd, slave_fd = pty.openpty()
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            cwd=ROOT,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
        )
        os.close(slave_fd)
        output = bytearray()
        try:
            os.write(master_fd, b"ab\x1b[DX\x1b[CY\n")
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                ready, _, _ = select.select([master_fd], [], [], 0.1)
                if ready:
                    try:
                        output.extend(os.read(master_fd, 4096))
                    except OSError:
                        break
            proc.wait(timeout=5)
            while True:
                ready, _, _ = select.select([master_fd], [], [], 0)
                if not ready:
                    break
                try:
                    output.extend(os.read(master_fd, 4096))
                except OSError:
                    break
        finally:
            try:
                os.close(master_fd)
            except OSError:
                pass
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

        rendered = output.decode("utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, rendered)
        self.assertIn("RESULT='aXbY'", rendered)
        self.assertNotIn("RESULT='ab\\x1b[DX'", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
