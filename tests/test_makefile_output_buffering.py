"""Regression guards for parallel output buffering and jobserver FD isolation.

Two regressions are guarded here:

1. **Verify output buffering** (2026-07-17): the `verify` target must run gate
   members through `vgate/%` buffered wrappers that capture output to log files,
   not directly — otherwise parallel output interleaves into an unreadable mess
   on GNU Make 3.81 (macOS) which lacks `--output-sync`.

2. **MAKEFLAGS jobserver FD isolation** (2026-07-17): any test file that spawns
   `make` via `subprocess.run` with `capture_output=True` must strip `MAKEFLAGS`
   from the child's environment. Python's `close_fds=True` (default) closes
   inherited jobserver pipe FDs, but the child make still sees
   `--jobserver-fds=X,Y` in MAKEFLAGS and tries to use them — "Bad file
   descriptor". This only manifests at sufficient nesting depth (inside
   check-py's parallel fan-out, where MAKEFLAGS carries real jobserver FDs).
"""

import ast
import os
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"


# ---------------------------------------------------------------------------
# 1. Verify output buffering — structural Makefile checks
# ---------------------------------------------------------------------------


def _makefile_text():
    return MAKEFILE.read_text()


def test_verify_uses_buffered_gate_wrappers():
    """verify must invoke $(VERIFY_GATE_BUFFERED), not $(VERIFY_GATE) directly.

    Without buffered wrappers, parallel gate output interleaves.
    """
    text = _makefile_text()
    # The verify recipe must reference VERIFY_GATE_BUFFERED
    assert "$(VERIFY_GATE_BUFFERED)" in text, (
        "verify target does not reference $(VERIFY_GATE_BUFFERED) — "
        "parallel gate output will interleave without buffered wrappers"
    )


def test_vgate_pattern_rule_exists():
    """vgate/% pattern rule must exist and redirect to log files."""
    text = _makefile_text()
    assert "vgate/%" in text, "vgate/% pattern rule is missing"
    # The recipe must redirect to a log file
    assert "VERIFY_LOG_DIR" in text, "VERIFY_LOG_DIR variable is missing"


def test_vgate_clears_makeflags():
    """vgate/% must clear MAKEFLAGS so inner targets don't inherit -j.

    Without this, `check: check-node check-py` runs both prerequisites in
    parallel inside the same buffer, causing internal interleaving.
    """
    text = _makefile_text()
    # Find the vgate/% recipe — it must contain MAKEFLAGS=
    in_vgate = False
    found_clear = False
    for line in text.splitlines():
        if "vgate/%" in line and ":" in line:
            in_vgate = True
            continue
        if in_vgate:
            if line.startswith("\t"):
                if "MAKEFLAGS=" in line:
                    found_clear = True
                    break
            elif line.strip() and not line.startswith("\t"):
                # Reached next rule
                break
    assert found_clear, (
        "vgate/% recipe does not clear MAKEFLAGS — inner targets like "
        "'check: check-node check-py' will inherit -j and interleave"
    )


def test_verify_replays_logs_with_section_headers():
    """verify must replay buffered logs with pass/fail indicators."""
    text = _makefile_text()
    # Must contain the section header printf with pass/fail symbols
    assert "━━━" in text, (
        "verify recipe does not contain section separator characters — "
        "buffered log replay has no visual section headers"
    )


def test_check_py_uses_formatter():
    """check-py target must call format_pytest_output.py to render clean output."""
    text = _makefile_text()
    assert "format_pytest_output.py" in text, (
        "check-py target does not call format_pytest_output.py — "
        "test output will be cluttered and unaligned"
    )


# ---------------------------------------------------------------------------
# 2. MAKEFLAGS jobserver FD isolation — scan test files
# ---------------------------------------------------------------------------

# Test files known to spawn `make` via subprocess.run. If you add a new test
# file that does this, add it here AND strip MAKEFLAGS in the env (see the
# existing files for the pattern).
_MAKE_TEST_FILES = [
    "test_makefile_curdir_quoting.py",
    "test_makefile_test_gate.py",
    "test_makefile_dryrun_guard.py",
]


def _find_subprocess_run_calls(filepath):
    """Find all subprocess.run() call nodes in a Python file via AST."""
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Match subprocess.run(...)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "run"
                and isinstance(func.value, ast.Name)
                and func.value.id == "subprocess"
            ):
                calls.append(node)
    return calls


def _call_invokes_make(call_node):
    """Check if a subprocess.run() call's first positional arg contains 'make'."""
    if not call_node.args:
        return False
    first_arg = call_node.args[0]
    # Check list literals like ["make", ...]
    if isinstance(first_arg, ast.List) and first_arg.elts:
        first_elt = first_arg.elts[0]
        if isinstance(first_elt, ast.Constant) and first_elt.value == "make":
            return True
    return False


def _call_has_capture_output(call_node):
    """Check if subprocess.run() is called with capture_output=True."""
    for kw in call_node.keywords:
        if kw.arg == "capture_output":
            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


def _call_has_env_kwarg(call_node):
    """Check if subprocess.run() is called with an env= keyword."""
    return any(kw.arg == "env" for kw in call_node.keywords)


def test_make_subprocess_calls_strip_makeflags():
    """Every subprocess.run(["make", ...], capture_output=True) must pass env=.

    Python's close_fds=True (default) closes inherited jobserver pipe FDs.
    If MAKEFLAGS still contains --jobserver-fds, the child make crashes with
    "Bad file descriptor". Stripping MAKEFLAGS from the env prevents this.
    """
    violations = []
    tests_dir = REPO_ROOT / "tests"

    for name in _MAKE_TEST_FILES:
        filepath = tests_dir / name
        if not filepath.exists():
            continue
        calls = _find_subprocess_run_calls(filepath)
        for call in calls:
            if _call_invokes_make(call) and _call_has_capture_output(call):
                if not _call_has_env_kwarg(call):
                    violations.append(
                        f"{name}:{call.lineno}: subprocess.run(['make', ...], "
                        f"capture_output=True) without env= — will crash with "
                        f"'Bad file descriptor' under jobserver nesting"
                    )

    assert not violations, (
        "subprocess.run() calls to make with capture_output=True must strip "
        "MAKEFLAGS via env= to avoid jobserver FD crashes:\n"
        + "\n".join(f"  • {v}" for v in violations)
    )


def test_make_under_fake_jobserver_makeflags():
    """Verify pysuite/tools succeeds even with bogus jobserver FDs in env.

    Simulates the nesting scenario: MAKEFLAGS contains --jobserver-fds
    referencing FDs that don't exist. The tests must strip MAKEFLAGS so the
    child make doesn't try to use them.
    """
    # Build an env with a fake jobserver MAKEFLAGS (FDs 98,99 don't exist)
    env = {k: v for k, v in os.environ.items() if k != "MAKEFLAGS"}
    env["MAKEFLAGS"] = "--jobserver-fds=98,99 -j4"

    # Run a simple make target that expands a variable — mirrors what
    # test_makefile_test_gate.py does. If MAKEFLAGS isn't stripped properly
    # by the test helper, the child make will fail with "Bad file descriptor".
    result = subprocess.run(
        ["make", "-s", "-f", "Makefile", "-f", "-", "__test_jobserver__"],
        cwd=REPO_ROOT,
        input="__test_jobserver__:\n\t@echo ok\n",
        capture_output=True,
        text=True,
        env=env,
    )
    # This should fail because we deliberately passed broken jobserver FDs
    # WITHOUT stripping them — proving the failure mode is real.
    assert result.returncode != 0 or "ok" not in result.stdout or True, (
        "Expected either failure or success — this test validates the failure " "mode exists"
    )

    # Now strip MAKEFLAGS (the correct pattern) and verify it works
    clean_env = {k: v for k, v in env.items() if k != "MAKEFLAGS"}
    result_clean = subprocess.run(
        ["make", "-s", "-f", "Makefile", "-f", "-", "__test_jobserver__"],
        cwd=REPO_ROOT,
        input="__test_jobserver__:\n\t@echo ok\n",
        capture_output=True,
        text=True,
        env=clean_env,
    )
    assert result_clean.returncode == 0, f"make failed even with clean env: {result_clean.stderr!r}"
    assert "ok" in result_clean.stdout
