"""Regression coverage for classification refresh and failure plot model coverage."""

import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from metrics.plots import generate


class PlotInputsTests(unittest.TestCase):
    def test_refresh_includes_missing_models_and_respects_exclusions(self):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot  # Initialize pyplot before mocking Figure.savefig.

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            metrics = root / "metrics"
            failures = root / "failure_mode/results"
            output = metrics / "comparison"
            for model in ["classified", "missing", "excluded"]:
                (metrics / model).mkdir(parents=True)
                (metrics / model / "vfr.csv").write_text("condition,vfr\n")
            saved = failures / "classified/run/classifications.json"
            saved.parent.mkdir(parents=True)

            def save(category):
                saved.write_text(
                    json.dumps(
                        {
                            "records": [
                                {
                                    "record": {
                                        "session_id": "s1",
                                        "question_turn_index": 1,
                                    },
                                    "source_index": 0,
                                    "review": {
                                        "status": "completed",
                                        "classification": {
                                            "assessment": "supported_failure",
                                            "primary_category": category,
                                        },
                                    },
                                }
                            ]
                        }
                    )
                )

            with (
                patch("matplotlib.figure.Figure.savefig"),
                patch("metrics.plots.generate_heatmap", return_value=None),
            ):
                for category in ["error_adoption_propagation", "inaccurate_correction"]:
                    save(category)
                    generate(metrics, None, output, ["excluded"], [], failures)
                    with (
                        failures.parent / "aggregation/category_counts.csv"
                    ).open() as handle:
                        counts = {
                            r["category"]: int(r["count"])
                            for r in csv.DictReader(handle)
                        }
                    self.assertEqual(counts[category], 1)
                    self.assertEqual(sum(counts.values()), 1)
            with (output / "failure_plot_coverage.csv").open() as handle:
                coverage = {r["model"]: r for r in csv.DictReader(handle)}
            self.assertEqual(set(coverage), {"classified", "missing"})
            self.assertEqual(coverage["classified"]["n_classified"], "1")
            self.assertEqual(coverage["missing"]["status"], "no_classified_failures")
            self.assertIn(
                "missing: no classified failures", (output / "plots.md").read_text()
            )


if __name__ == "__main__":
    unittest.main()
