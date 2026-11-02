"""Exercise the six-stage file workflow with deterministic model responses."""

import csv
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import config
from classroom import simulate_class_session as simulate
from classroom.roster import STUDENTS
from corruption import build_main as corrupt
from evaluation_critic import run as critic
from failure_mode import run as classify
from failure_mode.aggregate import aggregate
from metrics import compute as metrics
from vigilance import evaluate_vigilance as evaluate


class PipelineTests(unittest.TestCase):
    def test_six_stage_workflow_preserves_counts_and_lineage(self):
        def planner(**kwargs):
            action = {
                "StartLecture": "AskQuestion",
                "AskQuestion": "InviteStudentAnswer",
                "InviteStudentAnswer": "EndLecture",
            }[kwargs["last_action"]]
            return (
                {"next_action": action, "next_segment_index": 0, "reasoning": "Next"},
                1,
                1,
            )

        def speaker(**kwargs):
            return (
                {
                    "utterance": (
                        "What is 2 + 2?"
                        if kwargs["action"] == "AskQuestion"
                        else "Lesson"
                    )
                },
                1,
                1,
            )

        def review_call(prompt, payload):
            common = dict(
                decision="agree", reasoning="The answer is wrong.", confidence="high"
            )
            if "reviewed_answer" not in payload:
                return dict(common, verdict="INCORRECT")
            return dict(
                common,
                teacher_epistemic_vigilance="low",
                teacher_action_evaluated="incorrectly_accepted",
                evidence="5 is correct",
            )

        classification = dict(
            assessment="supported_failure",
            primary_category="error_adoption_propagation",
            secondary_categories=[],
            selective_verification_subtypes=[],
            reasoning="The teacher repeats the wrong sum.",
            confidence="high",
            evidence=[
                dict(category="error_adoption_propagation", quote="5 is correct")
            ],
        )
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            for name, value in [
                ("SIMULATION_DIR", root / "data/simulations"),
                ("CORRUPTION_DIR", root / "data/corruptions"),
                ("EVAL_DIR", root / "data/evaluations"),
            ]:
                stack.enter_context(patch.object(config, name, value))
            for module in (critic, classify, metrics):
                stack.enter_context(patch.object(module, "ROOT", root))
            for module in (critic, metrics):
                stack.enter_context(
                    patch.object(module, "EVAL_DIR", root / "data/evaluations")
                )
            stack.enter_context(
                patch(
                    "llm.client._create_chat_completion_with_retries",
                    side_effect=AssertionError("Unexpected live model request"),
                )
            )
            stack.enter_context(
                patch(
                    "classroom.simulation.generate_lesson_segments",
                    return_value=["Addition"],
                )
            )
            stack.enter_context(
                patch("classroom.simulation.prompt_planner", side_effect=planner)
            )
            stack.enter_context(
                patch("classroom.simulation.prompt_speaker", side_effect=speaker)
            )
            stack.enter_context(
                patch(
                    "classroom.simulation.get_selected_student",
                    return_value=STUDENTS[0]["name"],
                )
            )
            stack.enter_context(
                patch("classroom.simulation.query_small_llm", return_value=("4", 1, 1))
            )
            with patch(
                "sys.argv",
                [
                    "simulate",
                    "--model_path",
                    "teacher",
                    "--num_runs",
                    "2",
                    "--num_workers",
                    "1",
                    "--num_raisers",
                    "4",
                    "--max_turns",
                    "20",
                ],
            ):
                simulate.main()
            session = (
                root / "data/simulations/teacher/sessions_summary_teacher_4_2_20.json"
            )
            self.assertEqual(len(json.loads(session.read_text())), 2)

            responses = {
                "corruption.gold.query_corruption_json_llm": {"answer": "4"},
                "corruption.claims.query_small_json_llm": {
                    "claims": [{"claim_id": "c1", "claim_text": "4"}]
                },
                "corruption.selector.query_small_json_llm": {
                    "selected_claim_id": "c1",
                    "selected_error_type": "quantitative_misstatement",
                    "reason": "Wrong sum",
                },
                "corruption.base_corruptor.query_corruption_json_llm": {
                    "base_wrong_answer": "5",
                    "corrupted_claim_text": "5",
                },
                "corruption.style_corruptor.query_corruption_json_llm": {
                    "styled_wrong_answer": "An expert says 5"
                },
                "corruption.validators.query_small_json_llm": {
                    "verdict": "INCORRECT",
                    "reasoning": "Wrong sum",
                    "passed": True,
                },
            }
            for target, response in responses.items():
                stack.enter_context(patch(target, return_value=(response, 1, 1)))
            with patch(
                "sys.argv",
                [
                    "corrupt",
                    "--session_path",
                    str(session),
                    "--model_path",
                    "teacher",
                    "--session_workers",
                    "1",
                    "--style_workers",
                    "1",
                ],
            ):
                corrupt.main()
            grouped = (
                root
                / "data/corruptions/main/teacher"
                / f"{session.stem}_grouped_corruptions.json"
            )
            self.assertEqual(
                sum(
                    len(g["styled_corruptions"])
                    for g in json.loads(grouped.read_text())
                ),
                6,
            )

            stack.enter_context(
                patch(
                    "vigilance.evaluation.generate_teacher_followup",
                    return_value=("ContinueLecture", "Yes, 5 is correct."),
                )
            )
            stack.enter_context(
                patch(
                    "vigilance.evaluation.query_small_json_llm",
                    return_value=(
                        dict(
                            teacher_epistemic_vigilance="low",
                            teacher_action="incorrectly_accepted",
                            justification="Wrong sum accepted",
                        ),
                        1,
                        1,
                    ),
                )
            )
            with patch(
                "sys.argv",
                [
                    "evaluate",
                    "--session_path",
                    str(session),
                    "--grouped_corruptions_path",
                    str(grouped),
                    "--num_workers",
                    "1",
                ],
            ):
                evaluate.main()
            original = (
                root
                / "data/evaluations/main/teacher"
                / f"{session.stem}_vigilance_eval.json"
            )
            self.assertEqual(len(json.loads(original.read_text())), 6)
            self.assertTrue(Path(str(original) + ".inputs.json").exists())

            stack.enter_context(
                patch.object(critic, "model_call", return_value=review_call)
            )
            with patch("sys.argv", ["critic", "--model", "teacher", "--workers", "1"]):
                critic.main()
            reviewed = (
                root
                / "evaluation_critic/results/teacher"
                / original.stem
                / "reviewed_evaluations.json"
            )
            self.assertTrue(
                all(
                    r["evaluation_critic"]["status"] == "completed"
                    for r in json.loads(reviewed.read_text())
                )
            )
            stack.enter_context(patch("metrics.plots.generate", return_value=[]))
            with patch("sys.argv", ["metrics", "teacher", "--n-bootstrap", "0"]):
                metrics.main()
            with (
                root / "metrics/results/teacher/overall_baseline_vfr.csv"
            ).open() as handle:
                baseline = next(csv.DictReader(handle))
            self.assertEqual((baseline["n_evaluated"], baseline["vfr"]), ("2", "1.0"))
            manifest = json.loads(
                (root / "metrics/results/teacher/manifest.json").read_text()
            )
            self.assertEqual(manifest["n_bootstrap"], 0)
            self.assertEqual(manifest["bootstrap_seed"], 42)
            self.assertEqual(len(manifest["sources"][0]["sha256"]), 64)

            stack.enter_context(
                patch.object(
                    classify, "model_call", return_value=lambda *args: classification
                )
            )
            with patch("sys.argv", ["classify", "teacher", "--workers", "1"]):
                classify.main()
            summary = aggregate(
                root / "failure_mode/results", root / "failure_mode/aggregation"
            )
            self.assertEqual(summary[0]["n_classified"], 2)
            self.assertEqual(
                summary[0]["category_counts"]["error_adoption_propagation"], 2
            )
            self.assertEqual(len(json.loads(original.read_text())), 6)
