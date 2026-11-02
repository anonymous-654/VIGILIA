"""Check the fixed-roster simulation and its downstream entry points offline."""

import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from classroom.roster import STUDENTS
from classroom.simulation import run_class_session
from classroom.simulate_class_session import merge_session_summaries, parse_args
from core.json_io import save_json, load_json


class SimulationTests(unittest.TestCase):
    def test_simulation_records_fixed_students_without_demographic_fields(self):
        with (
            patch(
                "classroom.simulation.generate_lesson_segments", return_value=["Topic"]
            ),
            patch(
                "classroom.simulation.prompt_speaker",
                return_value=({"utterance": "Lesson"}, 1, 1),
            ),
            patch(
                "classroom.simulation.prompt_planner",
                return_value=(
                    {
                        "next_action": "EndLecture",
                        "next_segment_index": 0,
                        "reasoning": "Done",
                    },
                    1,
                    1,
                ),
            ),
        ):
            record = run_class_session(
                STUDENTS, "teacher", "Math", "Addition", max_turns=5
            )
        data = record.model_dump()
        self.assertEqual(record.turns_ran, 2)
        self.assertEqual(data["students"], STUDENTS)
        self.assertEqual(data["conversation_history"][-1]["action"], "EndLecture")
        self.assertEqual(set(data["students"][0]), {"name", "id"})
        self.assertNotIn("profile_type", data)

    def test_cli_and_summary_use_only_simulation_settings(self):
        with patch(
            "sys.argv", ["simulate", "--model_path", "teacher", "--num_runs", "2"]
        ):
            args = parse_args()
        self.assertFalse(hasattr(args, "profile_type"))
        self.assertFalse(hasattr(args, "eval_type"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session.json"
            save_json(session, {"session_id": "s1"})
            output = merge_session_summaries([session], "org/teacher", 4, 2, 200, root)
            self.assertEqual(output.name, "sessions_summary_org_teacher_4_2_200.json")
            metadata = load_json(output)[0]["metadata"]
            self.assertEqual(metadata["num_runs"], 2)
            self.assertNotIn("profile_type", metadata)
            self.assertNotIn("eval_type", metadata)

    def test_all_pipeline_entry_points_import_without_api_calls(self):
        for module in (
            "classroom.simulate_class_session",
            "corruption.build_main",
            "corruption.build_language_phen",
            "corruption.dialect.build_dialect_phen",
            "corruption.dialect_speaker.build_dialect_speaker",
            "vigilance.evaluate_vigilance",
            "vigilance.evaluate_language_phen_vigilance",
            "evaluation_critic.run",
            "metrics.compute",
            "failure_mode.run",
        ):
            with self.subTest(module=module):
                self.assertTrue(callable(importlib.import_module(module).main))
