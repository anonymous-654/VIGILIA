import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vigilance import baseline


class SharedBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sessions = self.root / "sessions.json"
        self.canonical = self.root / "canonical.json"
        self.session = {
            "session_id": "s",
            "metadata": {"model_path": "teacher"},
            "conversation_history": [{"utterance": "Question?"}],
            "students": ["original"],
        }
        self.base = {
            "session_id": "s",
            "question_turn_index": 0,
            "question_turn_number": 1,
            "question_text": "Question?",
            "base_wrong_answer": "Wrong.",
            "validator_verdict": "INCORRECT",
            "validator_reasoning": "Canonical reason.",
        }
        self.sessions.write_text(json.dumps([self.session]))
        self.canonical.write_text(json.dumps([{"base_corruptions": [self.base]}]))
        self.result = {
            "session_id": "s",
            "question_turn_index": 0,
            "style_type": "plain",
            "counterfactual_wrong_answer": "Wrong.",
            "answer_eval": "INCORRECT",
            "teacher_followup": "Correction.",
            "teacher_epistemic_vigilance": "high",
            "metadata": {},
        }
        for name, value in [
            ("settings", {"version": 1}),
            ("cache_path", self.root / "cache.json"),
        ]:
            p = patch.object(baseline, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        self.mock = patch(
            "vigilance.evaluation.evaluate_single_styled_answer",
            return_value=SimpleNamespace(model_dump=lambda: dict(self.result)),
        )
        self.evaluate = self.mock.start()
        self.addCleanup(self.mock.stop)

    def test_reused_once_across_families_with_canonical_verdict(self):
        baseline.load_baselines(self.sessions, self.canonical, create=True)
        baseline.load_baselines(self.sessions, self.canonical, create=True)
        shared = baseline.load_baselines(self.sessions, self.canonical)
        plain = baseline.baseline_for(self.base, shared)
        phen = baseline.baseline_for(self.base, shared, phenomenon=True)
        self.assertEqual(plain["teacher_followup"], phen["teacher_followup"])
        self.assertEqual(
            plain["teacher_epistemic_vigilance"], phen["teacher_epistemic_vigilance"]
        )
        self.assertEqual(self.evaluate.call_count, 1)
        request = self.evaluate.call_args.args[1]
        self.assertEqual(request["answer_eval"], "INCORRECT")
        self.assertEqual(request["incorrect_validator_reason"], "Canonical reason.")

    def test_context_and_verdict_changes_invalidate(self):
        baseline.load_baselines(self.sessions, self.canonical, create=True)
        self.session["students"] = ["different replay"]
        self.sessions.write_text(json.dumps([self.session]))
        with self.assertRaises(ValueError):
            baseline.load_baselines(self.sessions, self.canonical)
        baseline.load_baselines(self.sessions, self.canonical, create=True)
        self.assertEqual(self.evaluate.call_count, 2)
        self.base["validator_verdict"] = "CORRECT"
        self.canonical.write_text(json.dumps([{"base_corruptions": [self.base]}]))
        with self.assertRaises(ValueError):
            baseline.load_baselines(self.sessions, self.canonical)

    def test_conflicting_family_answer_rejected(self):
        shared = baseline.load_baselines(self.sessions, self.canonical, create=True)
        with self.assertRaises(ValueError):
            baseline.baseline_for(dict(self.base, base_wrong_answer="Other."), shared)

    def test_old_outputs_and_changed_inputs_invalidated(self):
        baseline.load_baselines(self.sessions, self.canonical, create=True)
        output = self.root / "output.json"
        self.assertFalse(
            baseline.output_is_current(
                output, self.sessions, self.canonical, self.canonical
            )
        )
        baseline.stamp_output(output, self.sessions, self.canonical, self.canonical)
        self.assertTrue(
            baseline.output_is_current(
                output, self.sessions, self.canonical, self.canonical
            )
        )
        self.session["students"] = ["another"]
        self.sessions.write_text(json.dumps([self.session]))
        self.assertFalse(
            baseline.output_is_current(
                output, self.sessions, self.canonical, self.canonical
            )
        )

    def test_explicit_historical_reuse_requires_matching_inputs(self):
        entry = {
            "fingerprint": "old",
            "input_digest": baseline.digest([self.session, self.base]),
        }
        with patch.dict("os.environ", {"VIGILANCE_REUSE_CACHED_BASELINES": "1"}):
            self.assertTrue(
                baseline.reusable_entry(entry, self.session, self.base, "new")
            )
            self.assertFalse(
                baseline.reusable_entry(
                    entry,
                    self.session,
                    dict(self.base, validator_verdict="CORRECT"),
                    "new",
                )
            )
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(
                baseline.reusable_entry(entry, self.session, self.base, "new")
            )

    def test_partial_success_is_checkpointed(self):
        other = dict(self.base, question_turn_index=1)
        self.session["conversation_history"].append({"utterance": "Question?"})
        self.sessions.write_text(json.dumps([self.session]))
        self.canonical.write_text(
            json.dumps([{"base_corruptions": [self.base, other]}])
        )
        self.evaluate.side_effect = [
            SimpleNamespace(model_dump=lambda: dict(self.result)),
            RuntimeError("offline"),
        ]
        result = baseline.load_baselines(self.sessions, self.canonical, create=True)
        self.assertEqual(result["s:1"]["evaluation_status"], "invalid")
        self.assertIsNone(result["s:1"]["teacher_followup"])
        saved = json.loads((self.root / "cache.json").read_text())
        self.assertEqual(list(saved), ["s:0", "s:1"])
        self.assertTrue(saved["s:1"]["retryable_error"])
        # Readers reuse an explicit invalid row without invoking the teacher.
        baseline.load_baselines(self.sessions, self.canonical)
        self.assertEqual(self.evaluate.call_count, 2)
        self.evaluate.side_effect = [
            SimpleNamespace(model_dump=lambda: dict(self.result, question_turn_index=1))
        ]
        baseline.load_baselines(self.sessions, self.canonical, create=True)
        self.assertEqual(self.evaluate.call_count, 3)
        self.assertEqual(
            json.loads((self.root / "cache.failures.json").read_text()), {}
        )


class SettingsSnapshotTests(unittest.TestCase):
    def tearDown(self):
        baseline._settings_snapshot.cache_clear()

    def test_disk_changes_do_not_change_running_snapshot(self):
        baseline._settings_snapshot.cache_clear()
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(
                baseline, "_read_settings", side_effect=[{"version": 1}, {"version": 2}]
            ) as read,
        ):
            first = baseline.settings()
            first["version"] = 999
            self.assertEqual(baseline.settings(), {"version": 1})
            self.assertEqual(read.call_count, 1)

    def test_new_stage_rejects_different_settings(self):
        baseline._settings_snapshot.cache_clear()
        with (
            patch.dict("os.environ", {"VIGILANCE_SETTINGS_SNAPSHOT": '{"version": 1}'}),
            patch.object(baseline, "_read_settings", return_value={"version": 2}),
        ):
            with self.assertRaisesRegex(ValueError, "changed since launch"):
                baseline.settings()
