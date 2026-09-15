from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.a004_freetoken_launcher import (
    A004RuntimeError,
    CudaToolkit,
    FreeTokenRuntime,
    RuntimeAssets,
    _sanitized_runtime_env,
    discover_cuda_toolkit,
)


class A004CudaDiscoveryTests(unittest.TestCase):
    def _toolkit(self, root: Path, release: str) -> Path:
        (root / "bin").mkdir(parents=True)
        (root / "include").mkdir(parents=True)
        (root / "lib64").mkdir(parents=True)
        (root / "include" / "cuda.h").write_text("/* synthetic cuda.h */\n", encoding="utf-8")
        nvcc = root / "bin" / "nvcc"
        nvcc.write_text(
            "#!/bin/sh\n"
            f"echo 'Cuda compilation tools, release {release}, V{release}.0'\n",
            encoding="utf-8",
        )
        nvcc.chmod(0o755)
        return nvcc

    def test_discovers_cuda_home_from_nvcc_when_cuda_home_unset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lac-a004-cuda-") as tmp:
            root = Path(tmp) / "cuda-13.3"
            self._toolkit(root, "13.3")
            env = {"PATH": str(root / "bin")}
            with mock.patch.dict(os.environ, {}, clear=True):
                toolkit = discover_cuda_toolkit(env)
            self.assertEqual(toolkit.root, root.resolve())
            self.assertEqual(toolkit.nvcc, (root / "bin" / "nvcc").resolve())
            self.assertEqual(toolkit.release, "13.3")

    def test_rejects_non_cuda13_toolkit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lac-a004-cuda-") as tmp:
            root = Path(tmp) / "cuda-12.8"
            self._toolkit(root, "12.8")
            env = {"PATH": str(root / "bin")}
            with mock.patch("scripts.a004_freetoken_launcher.glob.glob", return_value=[]):
                with self.assertRaises(A004RuntimeError):
                    discover_cuda_toolkit(env)


    def test_runtime_environment_includes_accepted_venv_ninja_when_shell_path_does_not(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lac-a004-runtime-env-") as tmp:
            root = Path(tmp)
            cuda = root / "cuda-13.3"
            venv = root / "venv"
            (cuda / "bin").mkdir(parents=True)
            (venv / "bin").mkdir(parents=True)
            toolkit = CudaToolkit(root=cuda, nvcc=cuda / "bin" / "nvcc", release="13.3")
            assets = RuntimeAssets(
                freetoken_checkout=root / "checkout",
                freetoken_venv=venv,
                ft=venv / "bin" / "ft",
                ninja=venv / "bin" / "ninja",
                model_snapshot=root / "snapshot",
            )
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin", "OPENAI_API_KEY": "synthetic-secret"}, clear=True):
                env = _sanitized_runtime_env(toolkit, assets)
            self.assertEqual(env["CUDA_HOME"], str(cuda))
            self.assertEqual(env["CUDA_PATH"], str(cuda))
            self.assertEqual(env["CUDACXX"], str(cuda / "bin" / "nvcc"))
            self.assertEqual(env["PATH"].split(os.pathsep)[:3], [str(cuda / "bin"), str(venv / "bin"), "/usr/bin"])
            self.assertNotIn("OPENAI_API_KEY", env)

    def test_startup_failure_fails_closed_and_cleans_owned_process_state(self) -> None:
        class ExitedProcess:
            returncode = 7
            pid = 43210

            def poll(self):
                return self.returncode

        fake = ExitedProcess()
        toolkit = CudaToolkit(root=Path("/synthetic/cuda"), nvcc=Path("/synthetic/cuda/bin/nvcc"), release="13.3")
        with tempfile.TemporaryDirectory(prefix="lac-a004-runtime-") as tmp:
            runtime = FreeTokenRuntime(log_path=Path(tmp) / "freetoken.log", startup_timeout=0.1)
            with mock.patch("scripts.a004_freetoken_launcher.validate_runtime_assets"), \
                 mock.patch("scripts.a004_freetoken_launcher.probe_exact_endpoint", return_value=(False, "not ready")), \
                 mock.patch("scripts.a004_freetoken_launcher._can_bind", return_value=True), \
                 mock.patch("scripts.a004_freetoken_launcher.discover_cuda_toolkit", return_value=toolkit), \
                 mock.patch("scripts.a004_freetoken_launcher.subprocess.Popen", return_value=fake):
                with self.assertRaisesRegex(A004RuntimeError, "rc=7"):
                    runtime.ensure()
            self.assertIsNone(runtime.process)
            self.assertFalse(runtime.owned)

    def test_stop_terminates_owned_runtime_process_group(self) -> None:
        class RunningProcess:
            pid = 9876
            returncode = None

            def poll(self):
                return None

            def wait(self, timeout=None):
                self.returncode = 0
                return 0

        runtime = FreeTokenRuntime()
        runtime.process = RunningProcess()
        runtime.owned = True
        with mock.patch("scripts.a004_freetoken_launcher.os.killpg") as killpg:
            runtime.stop()
        killpg.assert_called_once_with(9876, 15)
        self.assertIsNone(runtime.process)
        self.assertFalse(runtime.owned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
