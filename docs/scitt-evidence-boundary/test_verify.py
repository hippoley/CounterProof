"""Regression tests for illustrative negative-claim fixtures."""
import importlib.util
import json
import pathlib
import unittest

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("boundary_verify", HERE / "verify.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BoundaryTests(unittest.TestCase):
    def test_pinned_examples(self):
        cases = json.loads((HERE / "cases.json").read_text())
        self.assertEqual(len(cases), 7)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(module.classify(case), case["expected"])
    def test_ack_never_proves_completion(self):
        self.assertEqual(module.classify({"ack":True,"command_accepted":True}), "UNCHECKABLE")
    def test_same_admin_does_not_prove_independence(self):
        self.assertEqual(module.classify({"declared_window_position":1,"object_observation":{"position":1,"quality":"measured","sensor_id":"s"},"declared_control_domains":["a","b"]}), "INDEPENDENCE_UNPROVEN")
    def test_digest_mismatch_precedes_observation(self):
        self.assertEqual(module.classify({"statement_digest":"a","actual_statement_digest":"b","object_observation":{"position":1,"quality":"measured","sensor_id":"s"},"declared_window_position":1,"independence_proven":True}), "REFERENCE_MISMATCH")

if __name__ == "__main__":
    unittest.main()
