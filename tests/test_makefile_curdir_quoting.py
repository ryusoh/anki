"""Regression guard for unquoted $(CURDIR) breaking on the space in this repo's path.

This repo's absolute path contains a space ("Application Support"). The
`pysuite/%` pattern rule (check-py's parallel suite fan-out) originally built
`COVERAGE_FILE=$(CURDIR)/$(PY_COV_DIR)/...` unquoted — /bin/sh word-splits an
unquoted VAR=value assignment at the first space, so it tried to *execute*
"Support/Anki2/addons21/coverage/py-data/..." as a command instead of setting
the env var. pytest never ran; the recipe failed with a cryptic
"No such file or directory" instead of a pytest-shaped error.

This runs the real pysuite/% recipe against the real repo path (a tmp_path
copy wouldn't reproduce the space), so it fails the same way the original bug
did if the quoting regresses.

On a checkout whose path has no space (CI: /home/runner/work/anki/anki) the
bug is unreproducible by construction, so the test SKIPS there — it used to
hard-assert the precondition instead, which failed CI the first time this
file ever reached it (2026-07-14; local runs always passed because this
machine's path does contain the space).
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    " " not in str(REPO_ROOT),
    reason="repo path has no space, so unquoted-$(CURDIR) breakage cannot "
    "manifest here (guard is meaningful only on space-containing checkouts "
    "like the primary '.../Application Support/...' one)",
)
def test_pysuite_target_writes_coverage_file():
    cov_dir = REPO_ROOT / "coverage" / "py-data"
    cov_dir.mkdir(parents=True, exist_ok=True)
    cov_file = cov_dir / ".coverage.tools"
    cov_file.unlink(missing_ok=True)

    result = subprocess.run(
        ["make", "-s", "pysuite/tools"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"pysuite/tools failed: {result.stderr!r}"
    assert cov_file.exists(), (
        "COVERAGE_FILE was never written — likely an unquoted $(CURDIR) in "
        "the pysuite/% recipe breaking on the space in this repo's path"
    )
