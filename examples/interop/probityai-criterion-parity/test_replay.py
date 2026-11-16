"""Consumer-owned regression: do not import the producer's reader."""
import json
import unittest
from pathlib import Path

from replay import judge_criterion


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "physical-completion-criterion.json"


class CriterionParityTests(unittest.TestCase):
    def test_all_pinned_cases(self):
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(data["base"], "conformant-witness-proven-to-policy")
        self.assertEqual(len(data["cases"]), 14)
        self.assertEqual({row["criterionMet"] for row in data["cases"]}, {"true", "false", "absent", "null"})
        for row in data["cases"]:
            with self.subTest(row=row):
                self.assertEqual(
                    judge_criterion(row["controller"], row["criterionMet"], row["reported"]),
                    (row["decision"], row["reason"], row["owed"]),
                )

    def test_missing_is_not_false_even_after_controller_success(self):
        self.assertEqual(
            judge_criterion("succeeded", "absent", "INDETERMINATE"),
            ("conformant", "result_follows_presentation", "INDETERMINATE"),
        )
        self.assertEqual(
            judge_criterion("succeeded", "null", "NOT_SATISFIED"),
            ("nonconformant", "negative_without_observation", "INDETERMINATE"),
        )

    def test_explicit_negative_and_success_are_conflicting_claims(self):
        self.assertEqual(
            judge_criterion("succeeded", "false", "NOT_SATISFIED"),
            ("ambiguous", "conflict_erased", "CONFLICT"),
        )

    def test_fail_closed_on_unknown_values(self):
        for args in (
            ("accepted", "true", "PROVEN_TO_POLICY"),
            (None, "unknown", "INDETERMINATE"),
            (None, "false", "PHYSICAL_COMPLETION_PROVEN"),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                judge_criterion(*args)


if __name__ == "__main__":
    unittest.main()
