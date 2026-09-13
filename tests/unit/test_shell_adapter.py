import os
import shutil
import tempfile
import unittest
from pathlib import Path

from packages.core import EffectRequest
from packages.dispatcher import EffectAdapter, ReconciliationEffectAdapter
from packages.effects.shell import SHELL_EXEC_ACTION, ShellEffectAdapter, ShellEffectError


CREATED = "2026-09-13T12:00:00Z"
EXPIRES = "2026-09-13T12:10:00Z"


def system_binary(name):
    found = shutil.which(name)
    if not found:
        raise AssertionError(f"required test executable is unavailable: {name}")
    return Path(found).resolve(strict=True)


def make_request(*, executable, argv=None, cwd=".", environment=None, suffix="unit", extra=None):
    arguments = {
        "executable": str(executable),
        "argv": [] if argv is None else argv,
        "cwd": cwd,
        "environment": {} if environment is None else environment,
    }
    if extra:
        arguments.update(extra)
    return EffectRequest.create(
        request_id=f"effect:h003:{suffix}",
        run_id="run:h003",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=SHELL_EXEC_ACTION,
        resource="shell:workspace",
        arguments=arguments,
        idempotency_key=f"idem:h003:{suffix}",
        created_at=CREATED,
        expires_at=EXPIRES,
    )


class ShellEffectAdapterUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = (Path(self.tmp.name) / "workspace").resolve()
        self.workspace.mkdir()
        (self.workspace / "subdir").mkdir()
        self.printf = system_binary("printf")
        self.adapter = ShellEffectAdapter(
            self.workspace,
            allowed_executables=(self.printf,),
            allowed_environment=("LAC_H003_ALLOWED",),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_adapter_implements_protocol_and_recognizes_only_exact_typed_contract(self):
        self.assertIsInstance(self.adapter, EffectAdapter)
        self.assertIsInstance(self.adapter, ReconciliationEffectAdapter)
        valid = make_request(
            executable=self.printf,
            argv=["%s", "hello"],
            cwd="subdir",
            environment={"LAC_H003_ALLOWED": "1"},
            suffix="valid",
        )
        self.assertTrue(self.adapter.supports(valid))

        wrong_resource = EffectRequest.create(
            request_id="effect:h003:wrong-resource",
            run_id="run:h003",
            principal_id="principal:owner",
            agent_id="agent:test",
            action=SHELL_EXEC_ACTION,
            resource="shell:other",
            arguments=valid.arguments,
            idempotency_key="idem:h003:wrong-resource",
            created_at=CREATED,
            expires_at=EXPIRES,
        )
        self.assertFalse(self.adapter.supports(wrong_resource))

        extra = make_request(executable=self.printf, suffix="extra", extra={"shell": "echo bad"})
        self.assertFalse(self.adapter.supports(extra))

    def test_executable_is_exact_allowlisted_absolute_binary_and_interpreters_fail_closed(self):
        unknown = make_request(executable="/usr/bin/definitely-not-authorized", suffix="unknown")
        self.assertFalse(self.adapter.supports(unknown))

        for blocked in ("/bin/sh", "/usr/bin/bash", "/usr/bin/python3", "/usr/bin/sudo", "/usr/bin/env"):
            req = make_request(executable=blocked, suffix="blocked-" + Path(blocked).name)
            self.assertFalse(self.adapter.supports(req), blocked)

        with self.assertRaises(ShellEffectError):
            ShellEffectAdapter(
                self.workspace,
                allowed_executables=(system_binary("bash"),),
            )

    def test_cwd_must_be_canonical_existing_workspace_directory(self):
        for cwd in ("../outside", "/tmp", "subdir/../subdir", "subdir//nested"):
            req = make_request(executable=self.printf, cwd=cwd, suffix="cwd-" + str(abs(hash(cwd))))
            self.assertFalse(self.adapter.supports(req), cwd)
        missing = make_request(executable=self.printf, cwd="missing", suffix="cwd-missing")
        self.assertTrue(self.adapter.supports(missing))
        # supports() is a typed-contract check; host existence is checked at invocation.

    def test_argv_is_an_array_not_a_shell_string_and_malformed_vectors_fail_closed(self):
        shell_string = make_request(executable=self.printf, argv="hello; touch pwned", suffix="shell-string")
        self.assertFalse(self.adapter.supports(shell_string))
        nul = make_request(executable=self.printf, argv=["bad\x00arg"], suffix="nul")
        self.assertFalse(self.adapter.supports(nul))
        too_many = make_request(executable=self.printf, argv=["x"] * 129, suffix="many")
        self.assertFalse(self.adapter.supports(too_many))
        literal_metacharacters = make_request(
            executable=self.printf,
            argv=["%s", "$(touch pwned); > escaped"],
            suffix="literal",
        )
        self.assertTrue(self.adapter.supports(literal_metacharacters))

    def test_environment_is_explicit_allowlisted_and_credential_shaped_names_fail_closed(self):
        allowed = make_request(
            executable=self.printf,
            environment={"LAC_H003_ALLOWED": "bound"},
            suffix="env-allowed",
        )
        self.assertTrue(self.adapter.supports(allowed))
        for name in ("PATH", "HOME", "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY", "SSH_AUTH_SOCK", "MY_TOKEN"):
            req = make_request(executable=self.printf, environment={name: "x"}, suffix="env-" + name.lower())
            self.assertFalse(self.adapter.supports(req), name)
        with self.assertRaises(ShellEffectError):
            ShellEffectAdapter(
                self.workspace,
                allowed_executables=(self.printf,),
                allowed_environment=("AWS_SECRET_ACCESS_KEY",),
            )

    def test_working_root_and_allowed_executable_must_be_canonical_real_paths(self):
        relative = Path("not-absolute")
        with self.assertRaises(ShellEffectError):
            ShellEffectAdapter(relative, allowed_executables=(self.printf,))

        link = Path(self.tmp.name) / "workspace-link"
        link.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaises(ShellEffectError):
            ShellEffectAdapter(link, allowed_executables=(self.printf,))

        binary_link = Path(self.tmp.name) / "printf-link"
        binary_link.symlink_to(self.printf)
        with self.assertRaises(ShellEffectError):
            ShellEffectAdapter(self.workspace, allowed_executables=(binary_link,))


if __name__ == "__main__":
    unittest.main()
