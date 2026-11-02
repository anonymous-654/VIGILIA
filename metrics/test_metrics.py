import unittest
from metrics.vfr import compute_vfr
from metrics.pairwise import compute_pairwise
from metrics.position import compute_positions


def record(q, style="plain", label="high", verdict="INCORRECT", **extra):
    return dict(
        session_id="session",
        question_turn_index=q,
        style_type=style,
        teacher_epistemic_vigilance=label,
        answer_eval=verdict,
        **extra,
    )


class MetricsTests(unittest.TestCase):
    def test_eligibility_and_withheld(self):
        result = compute_vfr(
            [
                record(1, label="low"),
                record(2, label="withheld"),
                record(3, label="low", verdict="CORRECT"),
                record(4, label="low", evaluation_status="invalid"),
                record(5, label="high", teacher_action_evaluated="ignored"),
            ]
        )
        self.assertEqual(result["n_evaluated"], 2)
        self.assertEqual(result["vfr"], 0.5)
        self.assertEqual(result["n_invalid"], 2)
        self.assertEqual(result["n_not_incorrect"], 1)

    def test_pair_eligibility_and_binary_outcomes(self):
        rows = [
            record(1),
            record(1, "emotion", "low"),
            record(2),
            record(2, "emotion", "withheld"),
            record(3, label="low"),
            record(3, "emotion", verdict="CORRECT"),
            record(4),
            record(4, "emotion", evaluation_status="invalid"),
            record(5, "emotion", "low"),
        ]
        result = compute_pairwise(rows, "style_type")[0]
        self.assertEqual(result["n_same_question"], 4)
        self.assertEqual(result["n_pairs"], 2)
        self.assertEqual(result["prer"], 0.5)
        self.assertEqual(result["delta_vfr_b_minus_a"], 0.5)
        self.assertEqual(result["vfr_a"], 0)

    def test_position_before_filtering(self):
        rows = [
            record(
                i,
                label="low" if i == 6 else "high",
                verdict="INCORRECT" if i in (1, 6) else "CORRECT",
            )
            for i in range(1, 7)
        ]
        results = {
            r["position"]: r for r in compute_positions(rows, "style_type", "plain")
        }
        self.assertEqual(results["first_half"]["n_total"], 3)
        self.assertEqual(results["second_half"]["vfr"], 1)
        self.assertEqual(results["second_third"]["n_evaluated"], 0)
        self.assertIsNone(results["second_third"]["vfr"])
        self.assertEqual(results["third_third"]["vfr"], 1)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            compute_pairwise([record(1), record(1)], "style_type")

    def test_paired_statistics(self):
        from metrics.statistics import paired_statistics

        result = paired_statistics([(0, 1)] * 6, 100)
        self.assertEqual(result["p_value"], 0.03125)
        self.assertEqual(result["difference_ci_low"], 1)
        self.assertEqual(result["difference_ci_high"], 1)
        self.assertEqual(paired_statistics([(0, 0), (0, 0)], 0)["p_value"], 1)
        self.assertIsNone(paired_statistics([(0, 1)], 0)["difference_ci_low"])

    def test_position_inference(self):
        import random
        from metrics.position_tests import compute_position_tests, holm

        self.assertEqual(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
        rng = random.Random(17)
        rows = []
        for session in range(40):
            for question in range(12):
                row = record(
                    question,
                    label=(
                        "low"
                        if rng.random() < (0.2 if question < 6 else 0.7)
                        else "high"
                    ),
                )
                row.update(
                    session_id=str(session),
                    subject="Math" if session % 2 else "Science",
                )
                rows.append(row)
        tests, comparisons = compute_position_tests(
            rows, "style_type", "plain", 100, 42
        )
        self.assertEqual(tests[0]["status"], "ok")
        self.assertLess(tests[0]["p_value"], 0.05)
        self.assertEqual(tests[0]["n_sessions"], 40)
        self.assertGreater(comparisons[0]["ci_low"], 0)
        self.assertEqual(comparisons[0]["n_bootstrap_valid"], 100)
        empty, contrasts = compute_position_tests(
            [record(1)], "style_type", "plain", 10
        )
        self.assertEqual(empty[0]["status"], "unavailable")
        self.assertIsNone(contrasts[0]["p_value"])

    def test_source_discovery(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from metrics.inputs import discover_inputs

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            stems = [
                "sessions_vigilance_eval",
                "sessions_degree1_language_phen_vigilance_eval",
                "sessions_dialect_phen_vigilance_eval",
                "sessions_dialect_speaker_vigilance_eval",
            ]
            for stem in stems:
                path = root / "critic" / "model" / stem / "reviewed_evaluations.json"
                path.parent.mkdir(parents=True)
                path.write_text("[]")
            other = (
                root
                / "critic/model/sessions_vigilance_eval/other_critic/reviewed_evaluations.json"
            )
            other.parent.mkdir()
            other.write_text("[]")
            found = discover_inputs("model", "critic", root / "data", root / "critic")
            self.assertEqual(len(found), 4)
            self.assertEqual(
                {x[0] for x in found},
                {"main", "language_phen", "dialect_phen", "dialect_speaker"},
            )
            self.assertEqual(
                discover_inputs("model", "original", root / "data", root / "critic"), []
            )
            self.assertEqual(
                discover_inputs(
                    "model", "critic", root / "data", root / "critic", "missing"
                ),
                [],
            )

    def test_baseline_cluster_ci(self):
        from metrics.vfr import baseline_vfr_with_ci

        rows = [
            dict(record(1), session_id="a"),
            dict(record(2), session_id="a"),
            dict(record(1, label="low"), session_id="b"),
        ]
        result = baseline_vfr_with_ci(rows, 200, 42)
        self.assertEqual(result["n_sessions"], 2)
        self.assertEqual(result["vfr"], 1 / 3)
        self.assertEqual(result["vfr_ci_low"], 0)
        self.assertEqual(result["vfr_ci_high"], 1)
        self.assertIsNone(baseline_vfr_with_ci(rows, 0)["vfr_ci_low"])
        self.assertIsNone(baseline_vfr_with_ci(rows[:2], 100)["vfr_ci_low"])

    def test_empty_matching_set(self):
        result = compute_pairwise([record(1), record(2, "emotion")], "style_type")[0]
        self.assertEqual(result["n_pairs"], 0)
        self.assertIsNone(result["prer"])


if __name__ == "__main__":
    unittest.main()
