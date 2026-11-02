"""Check launchers after Slurm copies them away from the source checkout."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_copied_script_uses_submission_directory_and_forwards_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "slurm_script"
            shutil.copy2(ROOT / "classroom/run.sh", script)
            environment = dict(
                os.environ,
                SLURM_SUBMIT_DIR=str(ROOT / "classroom"),
                PYTHON=sys.executable,
            )
            result = subprocess.run(
                ["bash", str(script), "--help"],
                cwd=directory,
                env=environment,
                text=True,
                capture_output=True,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--model_path", result.stdout)
            self.assertNotIn("--profile_type", result.stdout)
