import unittest
from evaluation_critic.review import review_record, apply_review, validate

ROW = dict(
    asked_question="What is 2+2?",
    counterfactual_wrong_answer="5",
    teacher_followup="It is 4, not 5.",
    answer_eval="INCORRECT",
    teacher_epistemic_vigilance="low",
    teacher_action_evaluated="incorrectly_accepted",
)
ANSWER = dict(
    decision="agree", verdict="INCORRECT", reasoning="2+2=4.", confidence="high"
)
TEACHER = dict(
    decision="revise",
    teacher_epistemic_vigilance="high",
    teacher_action_evaluated="correctly_corrected",
    reasoning="The teacher repairs the arithmetic.",
    evidence="4, not 5",
    confidence="high",
)


class ReviewTests(unittest.TestCase):
    def test_update_without_mutation(self):
        responses = iter([ANSWER, TEACHER])
        audit = review_record(ROW, lambda *args: next(responses))
        result = apply_review(ROW, audit)
        self.assertEqual(audit["status"], "completed")
        self.assertEqual(result["teacher_epistemic_vigilance"], "high")
        self.assertEqual(ROW["teacher_epistemic_vigilance"], "low")

    def test_uncertain_blocks_teacher(self):
        calls = []

        def call(*args):
            calls.append(args)
            return dict(
                decision="uncertain",
                verdict=None,
                reasoning="Ambiguous",
                confidence="low",
            )

        audit = review_record(ROW, call)
        self.assertEqual(len(calls), 1)
        self.assertEqual(apply_review(ROW, audit)["evaluation_status"], "invalid")

    def test_error_resume_reuses_answer(self):
        responses = iter([ANSWER, dict(TEACHER, evidence="fabricated")])
        audit = review_record(ROW, lambda *args: next(responses))
        self.assertEqual(audit["status"], "error")
        calls = []

        def call(*args):
            calls.append(args)
            return TEACHER

        repaired = review_record(ROW, call, audit)
        self.assertEqual(len(calls), 1)
        self.assertEqual(repaired["status"], "completed")

    def test_retry_repairs_validation(self):
        responses = iter([ANSWER, dict(TEACHER, evidence="wrong"), TEACHER])
        requests = []

        def call(prompt, payload):
            requests.append(payload)
            return next(responses)

        audit = review_record(ROW, call)
        self.assertEqual(audit["status"], "completed")
        self.assertEqual(audit["teacher_attempt_count"], 2)
        self.assertIn("retry_feedback", requests[-1])

    def test_five_attempt_limit(self):
        calls = []

        def call(*args):
            calls.append(args)
            raise RuntimeError("Unavailable")

        audit = review_record(ROW, call)
        self.assertEqual(len(calls), 5)
        self.assertEqual(audit["status"], "error")
        self.assertEqual(len(audit["attempts"]["answer"]), 5)

    def test_skipped_preserves_original(self):
        result = apply_review(ROW, dict(status="skipped"))
        self.assertEqual(
            {k: v for k, v in result.items() if k != "evaluation_critic"}, ROW
        )

    def test_verdict_action_conflict(self):
        with self.assertRaises(ValueError):
            validate(TEACHER, "teacher", ROW, "CORRECT")


if __name__ == "__main__":
    unittest.main()
