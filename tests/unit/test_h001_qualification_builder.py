import importlib.util
import tempfile
import unittest
from pathlib import Path


class H001QualificationBuilderTests(unittest.TestCase):
    def test_minimal_runtime_root_precreates_read_only_bind_targets(self):
        root = Path(__file__).resolve().parents[2]
        script = root / "scripts" / "h001_qualify_sandbox.py"
        spec = importlib.util.spec_from_file_location("h001_qualifier", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp_raw:
            runtime_root, _bash, _sleep = module.build_runtime_root(Path(tmp_raw))
            self.assertTrue((runtime_root / "workspace/ro").is_dir())
            self.assertTrue((runtime_root / "workspace/rw").is_dir())


if __name__ == "__main__":
    unittest.main()
