"""Run the dependency-free frontend regressions through unittest discovery."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
JS_TEST = APP_ROOT / "testing" / "web_backend" / "test_recent_controls.js"


class FrontendNodeTests(unittest.TestCase):
    def test_recent_controls_node_regressions(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")

        # Release checks must not launch the opt-in browser test.
        env = os.environ.copy()
        env.pop("PLAYWRIGHT_MODULE", None)
        result = subprocess.run(
            [node, "--test", str(JS_TEST)],
            cwd=APP_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
