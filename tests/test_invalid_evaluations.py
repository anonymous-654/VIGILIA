import unittest
from unittest.mock import patch
from vigilance.evaluation import evaluate_teacher_vigilance
from metrics.vfr import compute_vfr
from metrics.pairwise import compute_pairwise


class InvalidEvaluationTests(unittest.TestCase):
    def test_invalid_response_retries_and_preserves(self):
        bad = dict(
            teacher_epistemic_vigilance="incorrectly_accepted",
            teacher_action="incorrectly_accepted",
            justification="Reason",
        )
        with (
            patch(
                "vigilance.evaluation.query_small_json_llm", return_value=(bad, 1, 1)
            ) as call,
            patch("vigilance.evaluation.time.sleep"),
        ):
            result = evaluate_teacher_vigilance(
                "history", "INCORRECT", "reason", max_attempts=2
            )
        self.assertEqual(call.call_count, 2)
        self.assertEqual(result["evaluation_status"], "invalid")
        self.assertEqual(result["raw_evaluator_response"], bad)
        self.assertEqual(result["teacher_epistemic_vigilance"], "incorrectly_accepted")

    def test_invalid_records_excluded_from_denominators_and_pairs(self):
        rows = [
            dict(
                session_id="s",
                question_turn_index=q,
                style_type=style,
                answer_eval="INCORRECT",
                teacher_epistemic_vigilance="low",
            )
            for q in (1, 2)
            for style in ("plain", "credibility")
        ]
        rows[0]["teacher_epistemic_vigilance"] = "incorrectly_accepted"
        baseline = compute_vfr([r for r in rows if r["style_type"] == "plain"])
        self.assertEqual(
            (baseline["n_evaluated"], baseline["n_invalid"], baseline["vfr"]),
            (1, 1, 1.0),
        )
        pairs = compute_pairwise(rows, "style_type", n_bootstrap=10, seed=42)
        self.assertEqual(pairs[0]["n_pairs"], 1)
        self.assertEqual(pairs[0]["n_excluded_pairs"], 1)
