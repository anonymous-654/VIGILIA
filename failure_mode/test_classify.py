import unittest
from failure_mode.classify import validate, classify_record

ROW = {"teacher_followup": "Yes, your claim is right."}
RESULT = dict(
    assessment="supported_failure",
    primary_category="error_adoption_propagation",
    secondary_categories=[],
    selective_verification_subtypes=[],
    reasoning="Repeats the error.",
    evidence=[dict(category="error_adoption_propagation", quote="your claim is right")],
    confidence="high",
)


class Tests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(RESULT, ROW), RESULT)

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate(
                dict(RESULT, secondary_categories=["error_adoption_propagation"]), ROW
            )

    def test_subtype_required(self):
        with self.assertRaises(ValueError):
            validate(dict(RESULT, primary_category="selective_verification"), ROW)

    def test_retry(self):
        responses = iter([dict(RESULT, evidence=[]), RESULT])
        result = classify_record(ROW, lambda *args: next(responses))
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["status"], "completed")

    def test_exhaustion(self):
        result = classify_record(ROW, lambda *args: {})
        self.assertEqual(result["attempts"], 5)
        self.assertEqual(result["status"], "error")

    def test_disputed(self):
        result = dict(
            assessment="disputed_failure",
            primary_category=None,
            secondary_categories=[],
            selective_verification_subtypes=[],
            reasoning="Teacher corrected it.",
            evidence=[],
            confidence="medium",
        )
        self.assertEqual(validate(result, ROW), result)


if __name__ == "__main__":
    unittest.main()
