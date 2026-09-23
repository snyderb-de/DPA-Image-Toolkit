"""
Every compression profile must survive being frozen into the EXE.

tifffile resolves codecs lazily through imagecodecs, so PyInstaller's analysis
never sees them and they have to be named in `hiddenimports`. A module missing
from that list is invisible from source — the package is installed, the whole
suite passes — and the EXE builds clean. It fails only when a user picks that
codec on their own machine.

That is exactly what shipped: the spec listed `_imcd` and `_shared`, its
comment claimed LZW, PackBits and JPEG were covered, and JPEG was not. The
built EXE contained no `_jpeg8`, and a JPEG merge would have raised
`DelayedImportError: could not import name 'jpeg8_encode' from 'imagecodecs'`.

So this does not hardcode a list of modules. It encodes with each profile the
UI offers, watches which imagecodecs modules that actually loads, and requires
the spec to name them. A new profile, or an imagecodecs release that moves a
codec into a new module, fails here instead of in someone's hands.
"""

import ast
import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine import compression

SPEC = APP_ROOT / "packaging" / "dpa-toolkit.spec"

# One profile per process: imports are cached process-wide, so a second profile
# in the same interpreter would inherit the first one's modules.
PROBE = textwrap.dedent("""
    import io, json, sys
    import numpy as np
    import tifffile

    codec = sys.argv[1]
    if codec == "none":
        codec = None

    buffer = io.BytesIO()
    with tifffile.TiffWriter(buffer) as writer:
        writer.write(
            np.full((64, 64), 128, np.uint8),
            photometric="minisblack",
            compression=codec,
        )

    print(json.dumps({
        "bytes": len(buffer.getvalue()),
        "modules": sorted(m for m in sys.modules if m.startswith("imagecodecs")),
    }))
""")

# Stands in for the frozen EXE, which holds only what the spec bundles.
FROZEN = textwrap.dedent("""
    import sys
    hidden = set(sys.argv[2].split(",")) if sys.argv[2] else set()

    class OnlyBundled:
        def find_spec(self, name, path=None, target=None):
            if name.startswith("imagecodecs") and name not in hidden:
                raise ImportError("No module named '%s'" % name)
            return None

    sys.meta_path.insert(0, OnlyBundled())
""") + PROBE


def spec_hiddenimports() -> list:
    """The hiddenimports list as the spec really declares it."""
    tree = ast.parse(SPEC.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "hiddenimports":
            return [
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant)
            ]
    raise AssertionError(f"no hiddenimports found in {SPEC}")


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", script, *args],
        capture_output=True, text=True, timeout=300, cwd=str(APP_ROOT),
    )


class FrozenCodecTests(unittest.TestCase):
    def setUp(self):
        self.hidden = [n for n in spec_hiddenimports() if n.startswith("imagecodecs")]

    def modules_used_by(self, key: str) -> set:
        result = run(PROBE, compression.resolve(key) or "none")
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        return set(json.loads(result.stdout)["modules"])

    def test_the_spec_names_every_module_the_profiles_load(self):
        for key in compression.get_keys():
            with self.subTest(profile=key):
                missing = self.modules_used_by(key) - set(self.hidden)
                self.assertFalse(
                    missing,
                    f"compression profile {key!r} loads {sorted(missing)}, which "
                    f"{SPEC.name} does not name. PyInstaller finds some of these "
                    f"on its own through static imports, so this is not proof the "
                    f"EXE breaks — the next test is. Name them anyway, so the "
                    f"bundle does not depend on which imports happen to be "
                    f"analyzable in the installed version.",
                )

    def test_every_profile_encodes_with_only_what_the_spec_bundles(self):
        """The same claim from the other side: run it as the EXE would."""
        for key in compression.get_keys():
            with self.subTest(profile=key):
                result = run(FROZEN, compression.resolve(key) or "none", ",".join(self.hidden))
                self.assertEqual(
                    result.returncode, 0,
                    f"profile {key!r} cannot encode inside the EXE.\n"
                    f"{result.stderr[-1500:]}",
                )
                self.assertGreater(json.loads(result.stdout)["bytes"], 0)

    def test_the_guard_catches_a_missing_module(self):
        """Drop _jpeg8 — the module that really was missing — and JPEG must fail."""
        hidden = [n for n in self.hidden if n != "imagecodecs._jpeg8"]

        result = run(FROZEN, compression.resolve("jpeg"), ",".join(hidden))

        self.assertNotEqual(result.returncode, 0, "a missing codec module went unnoticed")

    def test_the_spec_still_bundles_imagecodecs_itself(self):
        self.assertIn("imagecodecs", self.hidden)
