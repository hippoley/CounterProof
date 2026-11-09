import tempfile
import unittest
from pathlib import Path
from pipeline_rea import analyze

class PipelineReaTests(unittest.TestCase):
    def test_jenkins(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "Jenkinsfile"
            p.write_text("stage('Build') { credentialsId: 'deploy-token' }")
            r = analyze(p)
            self.assertEqual(r["stages_or_jobs"], ["Build"])
            self.assertEqual(r["credential_reference_names"], ["deploy-token"])

    def test_github(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".github/workflows/ci.yml"
            p.parent.mkdir(parents=True)
            p.write_text("jobs:\n  test:\n    env:\n      KEY: ${{ secrets.API_KEY }}\n")
            r = analyze(p)
            self.assertEqual(r["stages_or_jobs"], ["test"])
            self.assertEqual(r["credential_reference_names"], ["API_KEY"])

    def test_secret_redacted(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".gitlab-ci.yml"
            p.write_text("stages:\n  - build\nAPI_KEY: topsecret123456789\n")
            r = analyze(p)
            self.assertEqual(r["stages_or_jobs"], ["build"])
            self.assertNotIn("topsecret123456789", str(r))
            self.assertEqual(r["findings"][0]["rule"], "possible-inline-secret")

if __name__ == "__main__":
    unittest.main()
