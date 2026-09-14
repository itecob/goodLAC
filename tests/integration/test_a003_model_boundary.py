import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class A003ModelBoundaryStaticTests(unittest.TestCase):
    def test_model_provider_bridge_has_no_authority_or_effect_imports(self):
        source = (ROOT / "scripts/a003_model_provider_stream.py").read_text(encoding="utf-8")
        self.assertIn("FreeTokenModelProvider", source)
        self.assertIn("ModelRequest", source)
        forbidden = (
            "packages.dispatcher",
            "packages.effects",
            "packages.policy",
            "packages.state",
            "ApprovalRepository",
            "ExecutionLease",
            "Dispatcher(",
            "EffectRequest",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_model_stream_scrubs_common_service_credentials(self):
        source = (ROOT / "packages/adapters/pi/model_stream_bridge.mjs").read_text(encoding="utf-8")
        for token in ("OPENAI_", "ANTHROPIC_", "AWS_", "AZURE_", "GOOGLE_", "HF_", "HUGGINGFACE_", "GITHUB_", "SSH_", "_TOKEN", "_CREDENTIAL"):
            self.assertIn(token, source)
        self.assertIn("delete env[key]", source)

    def test_effect_bridge_uses_existing_governed_components(self):
        source = (ROOT / "scripts/a003_controller_bridge.py").read_text(encoding="utf-8")
        for token in (
            "PiAgentAdapter",
            "Dispatcher",
            "FilesystemEffectAdapter",
            "ShellEffectAdapter",
            "LocalPolicyDecisionProvider",
            "SQLiteStateStore",
        ):
            self.assertIn(token, source)
        self.assertNotIn("subprocess.run", source)
        self.assertNotIn("os.system", source)

    def test_python_entrypoints_bootstrap_repo_root_before_lac_imports(self):
        for rel in (
            "scripts/a003_controller_bridge.py",
            "scripts/a003_model_provider_stream.py",
            "scripts/a003_verify_evidence.py",
        ):
            source = (ROOT / rel).read_text(encoding="utf-8")
            bootstrap = source.find("sys.path.insert(0, str(REPO_ROOT))")
            first_lac_import = source.find("from packages.")
            self.assertGreaterEqual(bootstrap, 0, rel)
            self.assertGreater(first_lac_import, bootstrap, rel)
            self.assertIn("Path(__file__).resolve().parents[1]", source, rel)

    def test_a003_does_not_add_phase4_surface(self):
        paths = [
            ROOT / "packages/adapters/pi/model_stream_bridge.mjs",
            ROOT / "scripts/a003_model_provider_stream.py",
            ROOT / "scripts/a003_controller_bridge.py",
            ROOT / "scripts/a003_qualification.mjs",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("OpenClaw", text)
        self.assertNotIn("Lane A", text)
        self.assertNotIn("compatibility gateway", text.lower())


if __name__ == "__main__":
    unittest.main()
