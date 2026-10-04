from __future__ import annotations
import importlib.util, shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("prr",ROOT/"scripts/goodlac_public_exposure.py")
prr=importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(prr)

def git(repo,*args):
    cp=subprocess.run(["git","-C",str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if cp.returncode: raise RuntimeError(cp.stderr)
    return cp.stdout.strip()

class RemotelessCandidateTests(unittest.TestCase):
    def test_scan_allows_repository_without_origin(self):
        with tempfile.TemporaryDirectory() as raw:
            repo=Path(raw)/"repo"; repo.mkdir()
            git(repo,"init","-q")
            git(repo,"config","user.name","Role")
            git(repo,"config","user.email","role@invalid.local")
            (repo/"config").mkdir()
            shutil.copy2(ROOT/"config/prr001_exposure_policy.json",repo/"config/prr001_exposure_policy.json")
            (repo/"x.txt").write_text("ok\\n")
            git(repo,"add",".")
            git(repo,"commit","-qm","initial")
            report=prr.build_report(repo)
            self.assertIsNone(report["repository"]["origin"])
            self.assertEqual(prr.markdown_summary(report).splitlines()[4], "- Origin: `NONE`")

if __name__=="__main__":
    unittest.main()
