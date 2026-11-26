"""Fail-closed tests for the pinned release intake boundary."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import verify_release as v

class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = self.root / "cases" / "case-1"
        self.case.mkdir(parents=True)
        self.payload = b'{"status":"unknown"}\n'
        (self.case / "record.json").write_bytes(self.payload)
        self.manifest = {
            "suite": "physical-completion/v1", "synthetic": True,
            "provenance": {"source": "hippoley, issue 80"},
            "vectors": [{"id": "case-1", "path": "cases/case-1",
                         "files": {"record.json": hashlib.sha256(self.payload).hexdigest()},
                         "expected": {"decision": "conformant"}}],
            "counts": {"conformant": 1, "nonconformant": 0, "ambiguous": 0}}
        (self.root / "MANIFEST.json").write_text(json.dumps(self.manifest))

    def test_git_blob_known_vector(self):
        self.assertEqual(v.git_blob_sha(b"abc"), "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")

    def test_duplicate_json_field_refused(self):
        with self.assertRaises(v.AdmissionError):
            v.strict_json(b'{"x":1,"x":2}')

    def test_non_json_number_refused(self):
        with self.assertRaises(v.AdmissionError):
            v.strict_json(b'{"x":NaN}')

    def test_path_traversal_refused(self):
        with self.assertRaises(v.AdmissionError):
            v.safe_record(self.root, "../secret")

    def test_missing_record_refused(self):
        with self.assertRaises(v.AdmissionError):
            v.safe_record(self.root, "cases/nope/record.json")

    def test_manifest_pin_refused(self):
        with self.assertRaises(v.AdmissionError):
            v.audit(self.root)

    def test_synthetic_one_case_not_48(self):
        with patch.object(v, "MANIFEST_BLOB", v.git_blob_sha((self.root / "MANIFEST.json").read_bytes())):
            with self.assertRaises(v.AdmissionError):
                v.audit(self.root)

    def test_unknown_checkout_refused(self):
        with patch.object(v, "git", return_value="f" * 40):
            with self.assertRaises(v.AdmissionError):
                v.run(self.root / "receipt.json", checkout=self.root)

if __name__ == "__main__":
    unittest.main()
