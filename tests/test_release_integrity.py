"""Regression checks for release validation and corruption provenance."""

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.checkpoints import prepare_checkpoint
from core.cli import positive_int
from corruption.validators import validate_incorrectness, validate_style
from vigilance.evaluate_language_phen_vigilance import resolve_output_path


class ReleaseIntegrityTests(unittest.TestCase):
    def test_failed_correctness_validation_never_invents_a_verdict(self):
        with patch(
            "corruption.validators.query_small_json_llm",
            side_effect=ValueError("Invalid JSON"),
        ):
            with self.assertRaises(ValueError):
                validate_incorrectness("Question?", "Answer")
        for verdict in ("UNKNOWN", "incorrect", None):
            with (
                self.subTest(verdict=verdict),
                patch(
                    "corruption.validators.query_small_json_llm",
                    return_value=({"verdict": verdict, "reasoning": "Reason"}, 1, 1),
                ),
            ):
                with self.assertRaises(ValueError):
                    validate_incorrectness("Question?", "Answer")

    def test_false_string_does_not_pass_style_validation(self):
        with patch(
            "corruption.validators.query_small_json_llm",
            return_value=({"passed": "false", "reasoning": "Absent"}, 1, 1),
        ):
            with self.assertRaises(ValueError):
                validate_style("Answer", "credibility")

    def test_positive_worker_and_run_counts(self):
        self.assertEqual(positive_int("2"), 2)
        for value in ("0", "-1"):
            with self.assertRaises(argparse.ArgumentTypeError):
                positive_int(value)

    def test_evaluation_paths_preserve_limited_run_suffixes(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch(
                "vigilance.evaluate_language_phen_vigilance.evaluation_model_dir",
                return_value=Path(directory),
            ),
        ):
            for family, prefix in [
                ("language_phen", "sessions_summary_teacher_sample10_degree1"),
                ("dialect_phen", "sessions_summary_teacher_sample10"),
                ("dialect_speaker", "sessions_summary_teacher_sample10"),
            ]:
                grouped = f"{prefix}_{family}_grouped_corruptions.json"
                path = resolve_output_path(
                    "sessions_summary_teacher.json", grouped, "teacher"
                )
                self.assertEqual(path.name, f"{prefix}_{family}_vigilance_eval.json")

    def test_resume_rejects_changed_input_settings_or_missing_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, artifact = (
                root / "input.json",
                root / "manifest.json",
                root / "output.json",
            )
            source.write_text("[]")
            prepare_checkpoint(
                manifest, source, {"conditions": ["a"]}, [artifact], False
            )
            artifact.write_text("[]")
            prepare_checkpoint(
                manifest, source, {"conditions": ["a"]}, [artifact], True
            )
            with self.assertRaises(ValueError):
                prepare_checkpoint(
                    manifest, source, {"conditions": ["a"]}, [artifact], False
                )
            with self.assertRaises(ValueError):
                prepare_checkpoint(
                    manifest, source, {"conditions": ["b"]}, [artifact], True
                )
            with patch.dict(
                "os.environ", {"AZURE_HELPER_DEPLOYMENT": "different-helper"}
            ):
                with self.assertRaises(ValueError):
                    prepare_checkpoint(
                        manifest, source, {"conditions": ["a"]}, [artifact], True
                    )
            source.write_text("[{}]")
            with self.assertRaises(ValueError):
                prepare_checkpoint(
                    manifest, source, {"conditions": ["a"]}, [artifact], True
                )
            manifest.unlink()
            with self.assertRaises(ValueError):
                prepare_checkpoint(
                    manifest, source, {"conditions": ["a"]}, [artifact], True
                )
