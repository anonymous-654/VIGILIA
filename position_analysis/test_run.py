import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from position_analysis.run import analyze, prepare, rho


class PositionTests(unittest.TestCase):
    def test_rank_before_filter_and_review_completion(self):
        records = []
        for i in range(4):
            records.append(
                dict(
                    session_id="s",
                    question_turn_index=i * 3,
                    style_type="plain",
                    answer_eval="INCORRECT" if i != 1 else "CORRECT",
                    teacher_epistemic_vigilance="low",
                    evaluation_critic={"status": "error" if i == 2 else "completed"},
                )
            )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.json"
            p.write_text(json.dumps(records))
            data, _, _ = prepare([("main", p, "input")])
        self.assertEqual(list(data.position), [0, 1])
        self.assertEqual(list(data.n_session_questions), [4, 4])

    def test_positive_trend_and_cluster_interval(self):
        rng = np.random.default_rng(77)
        rows = []
        for s in range(40):
            for x in np.linspace(0, 1, 16):
                probability = 1 / (1 + np.exp(-(-2 + 3 * x)))
                rows.append(
                    dict(
                        session=str(s),
                        position=x,
                        fail=int(rng.random() < probability),
                        subject="Math",
                    )
                )
        result = analyze(pd.DataFrame(rows), 100, 42)
        self.assertEqual(result["gee_status"], "ok")
        self.assertGreater(result["gee_beta"], 0)
        self.assertLess(result["gee_p_raw"], 0.05)
        self.assertGreater(result["rho_ci_low"], 0)
        self.assertEqual(result["n_bootstrap_valid"], 100)

    def test_constant_outcomes_unavailable(self):
        data = pd.DataFrame(
            dict(
                session=["a", "a", "b", "b"],
                position=[0, 1, 0, 1],
                fail=[0] * 4,
                subject=["Math"] * 4,
            )
        )
        result = analyze(data, 10, 42)
        self.assertIsNone(result["spearman_rho"])
        self.assertEqual(result["gee_status"], "unavailable")
        self.assertIsNone(rho(np.array([0, 1]), np.array([1, 1])))


if __name__ == "__main__":
    unittest.main()
