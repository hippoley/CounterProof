"""Synthetic regression of the ExecSurface #164 stdout privacy boundary.

No ExecSurface binary, secrets, network, or private paths are used. This tests
the subprocess DEVNULL containment mechanism, not the upstream harness itself.
"""
import subprocess
import sys
import unittest


MARKER_OUT = "SYNTHETIC_PATH_STDOUT"
MARKER_ERR = "SYNTHETIC_PATH_STDERR"
SCRIPT = (
    "import sys; "
    f"print({MARKER_OUT!r}); "
    f"print({MARKER_ERR!r}, file=sys.stderr)"
)


class StreamContainmentTests(unittest.TestCase):
    def test_inherited_streams_reach_parent_capture(self):
        wrapper = (
            "import subprocess,sys; "
            "subprocess.run([sys.executable, '-c', sys.argv[1]], check=True)"
        )
        outer = subprocess.run(
            [sys.executable, "-c", wrapper, SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        self.assertIn(MARKER_OUT, outer.stdout)
        self.assertIn(MARKER_ERR, outer.stderr)

    def test_devnull_containment_drops_both_streams(self):
        wrapper = (
            "import subprocess,sys; "
            "p=subprocess.run([sys.executable, '-c', sys.argv[1]], "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
            "sys.exit(p.returncode)"
        )
        outer = subprocess.run(
            [sys.executable, "-c", wrapper, SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        self.assertNotIn(MARKER_OUT, outer.stdout + outer.stderr)
        self.assertNotIn(MARKER_ERR, outer.stdout + outer.stderr)
        self.assertEqual(outer.returncode, 0)

    def test_devnull_containment_preserves_nonzero_exit(self):
        failing = SCRIPT + "; sys.exit(23)"
        wrapper = (
            "import subprocess,sys; "
            "p=subprocess.run([sys.executable, '-c', sys.argv[1]], "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
            "sys.exit(p.returncode)"
        )
        outer = subprocess.run(
            [sys.executable, "-c", wrapper, failing],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(outer.returncode, 23)
        self.assertNotIn(MARKER_OUT, outer.stdout + outer.stderr)
        self.assertNotIn(MARKER_ERR, outer.stdout + outer.stderr)


if __name__ == "__main__":
    unittest.main()
