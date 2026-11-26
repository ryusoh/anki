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
import sys
from pathlib import Path

import coverage

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_py_test_suites_ordered():
    """Expand $(PY_TEST_SUITES) via make in execution order."""
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
    return result.stdout.split()


def _make_py_test_suites():
    """Expand $(PY_TEST_SUITES) via make, so we test what the gate really runs."""
    return set(_make_py_test_suites_ordered())


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


def test_heavy_suites_scheduled_first():
    """Heavy root suites (tools, tests) start in wave 1 rather than straggling last."""
    ordered = _make_py_test_suites_ordered()
    assert ordered[:2] == [
        "tools",
        "tests",
    ], f"Expected tools and tests at front of PY_TEST_SUITES, got {ordered[:5]!r}"


def test_coveragerc_omits_ephemeral_tmp_modules(tmp_path):
    """Temporary modules under pytest tmp_path/OS temp dirs must not enter .coverage.

    In parallel `make check-py`, `tools` runs early while 20+ later suites
    rotate pytest's `tmp_path` retention window (last 3 `pytest-N` dirs). Any
    fixture module recorded under `pytest-of-*` is deleted before
    `coverage report` runs, causing `NoSource` on the combined report.
    """
    mod_dir = tmp_path / "pytest-of-runner" / "pytest-0" / "test_main_as_script2"
    mod_dir.mkdir(parents=True)
    mod_file = mod_dir / "dummy_transform.py"
    mod_file.write_text("x = 1\n", encoding="utf-8")

    cov_file = tmp_path / ".coverage"
    env = {**os.environ, "COVERAGE_FILE": str(cov_file)}
    result = subprocess.run(
        [sys.executable, "-m", "coverage", "run", str(mod_file)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    data = coverage.CoverageData(basename=str(cov_file))
    data.read()
    measured = {Path(p).resolve() for p in data.measured_files()}
    assert mod_file.resolve() not in measured
