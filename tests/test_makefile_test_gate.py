"""Regression guard for the Python test gate's suite auto-discovery.

`PY_TEST_SUITES` is derived at make time from
`git ls-files ... '*/test_*.py'` (mirroring JS_FILES/MD_FILES). If that
discovery ever breaks — a narrowed glob, a bad `sed` delimiter emptying the
list, an `--exclude-standard` misfire — `make check-py` would loop over nothing
and still print "✅ Python tests complete": a green gate running **zero tests**.

These tests expand the Makefile's *actual* variable and assert it stays
non-empty and covers every discovered addon test directory, so a silently
no-op'd gate fails loudly no matter how discovery is rewritten. Only `make`
and `git` are needed.
"""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_py_test_suites():
    """Expand $(PY_TEST_SUITES) via make, so we test what the gate really runs."""
    # Strip MAKEFLAGS so the child make doesn't try to use inherited jobserver
    # FDs that Python's close_fds=True (default) has already closed — otherwise
    # this test fails with "Bad file descriptor" when run at sufficient nesting
    # depth (inside check-py's parallel fan-out).
    env = {k: v for k, v in os.environ.items() if k != "MAKEFLAGS"}
    result = subprocess.run(
        ["make", "-s", "-f", "Makefile", "-f", "-", "__print_py_suites__"],
        cwd=REPO_ROOT,
        input="__print_py_suites__:\n\t@echo $(PY_TEST_SUITES)\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"make failed to expand PY_TEST_SUITES: {result.stderr!r}"
    return set(result.stdout.split())


def _discovered_test_dirs():
    """Directories holding a test_*.py, computed independently of the Makefile."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*/test_*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return {str(Path(p).parent) for p in result.stdout.split()}


def test_py_test_suites_nonempty():
    """A discovery that expands to nothing turns `make check-py` into a no-op."""
    suites = _make_py_test_suites()
    assert suites, "PY_TEST_SUITES expanded to nothing — the gate would run zero tests"


def test_py_test_suites_covers_every_addon_test_dir():
    """Every dir with a test_*.py must be gated, so new addons can't drift ungated."""
    missing = _discovered_test_dirs() - _make_py_test_suites()
    assert not missing, f"test directories not gated by PY_TEST_SUITES: {sorted(missing)}"
