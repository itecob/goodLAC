from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

from packages.lacctl.cli import (
    OWNER_PERMISSION_CHOICES,
    LacctlInputError,
    _operation,
    _parser,
)
from packages.productization import v1


class PostV1R4TerminalFallbackTests(unittest.TestCase):
    def test_lacctl_decide_maps_all_friendly_choices_to_existing_canonical_operation(self):
        for canonical in OWNER_PERMISSION_CHOICES:
            with self.subTest(choice=canonical):
                friendly = canonical.lower().replace("_", "-")
                args = _parser().parse_args(
                    [
                        "permissions",
                        "decide",
                        friendly,
                        "continuation:r4:test",
                        "pending:r4:test",
                    ]
                )
                operation, arguments = _operation(args)
                self.assertEqual(operation, "permissions.decide")
                self.assertEqual(
                    arguments,
                    {
                        "continuation_id": "continuation:r4:test",
                        "pending_id": "pending:r4:test",
                        "choice": canonical,
                        "scope": "RESOURCE",
                    },
                )

    def test_terminal_decide_does_not_expose_owner_selected_scope_or_subject_fields(self):
        with self.assertRaises(LacctlInputError):
            _parser().parse_args(
                [
                    "permissions",
                    "decide",
                    "always-allow",
                    "continuation:r4:test",
                    "pending:r4:test",
                    "--scope",
                    "APPLICATION",
                ]
            )

    def test_lac_owner_decide_is_only_a_thin_translation_to_lacctl(self):
        with mock.patch.object(v1, "launch_ctl", return_value=0) as launch:
            rc = v1.owner_command(
                None,
                [
                    "decide",
                    "allow-once",
                    "continuation:r4:test",
                    "pending:r4:test",
                ],
            )
        self.assertEqual(rc, 0)
        launch.assert_called_once_with(
            None,
            [
                "permissions",
                "decide",
                "allow-once",
                "continuation:r4:test",
                "pending:r4:test",
            ],
        )

    def test_owner_help_advertises_bounded_decide_without_snapshot_policy_workflow(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            rc = v1.owner_command(None, ["help"])
        self.assertEqual(rc, 0)
        output = stream.getvalue()
        self.assertIn("lac-owner decide", output)
        self.assertIn("allow-once", output)
        self.assertNotIn("permissions set", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
