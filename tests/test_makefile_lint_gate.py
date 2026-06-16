"""Regression guard for the lint gate's config-detection.

The ESLint/Stylelint lint targets decide whether to run by probing for a config
file. A previous version used `ls eslint.config.* .eslintrc* >/dev/null 2>&1` as
the presence test — but `ls a* b*` exits non-zero when *either* glob is unmatched,
so with a flat `eslint.config.cjs` present (and no legacy `.eslintrc*`) the check
failed and the recipe **silently skipped ESLint/Stylelint entirely**. The gate
looked green while linting nothing.

These tests execute the Makefile's *actual* detection conditions, so they catch a
silently-skipping gate no matter how the detection is rewritten. No node/eslint
needed — only `ls`/`grep` via `sh`.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"

# The `if <cond>; then` shell conditions in the lint targets that probe for an
# ESLint/Stylelint config file.
_DETECTION_RE = re.compile(
    r"if (ls [^;]*(?:eslintrc|stylelintrc|eslint\.config|stylelint\.config)[^;]*); then"
)


def _detection_conditions():
    return [m.strip() for m in _DETECTION_RE.findall(MAKEFILE.read_text())]


def test_makefile_has_lint_config_detection():
    conds = _detection_conditions()
    # lint-js, lint-css, and the two halves of lint-fix → at least the gate pair.
    assert len(conds) >= 2, f"no lint config-detection found in Makefile: {conds!r}"


def test_detection_succeeds_with_flat_config_only(tmp_path):
    """The bug scenario: a flat config exists but the legacy glob is unmatched.

    A correct presence test returns success (config found) so the linter runs.
    The old `ls a* b* >/dev/null 2>&1` form returned failure here and skipped.
    """
    (tmp_path / "eslint.config.cjs").write_text("module.exports = [];\n")
    (tmp_path / ".stylelintrc.cjs").write_text("module.exports = {};\n")
    for cond in _detection_conditions():
        result = subprocess.run(["sh", "-c", cond], cwd=tmp_path)
        assert (
            result.returncode == 0
        ), f"lint detection skipped a present config (silent no-op gate): {cond!r}"


def test_detection_reports_absent_when_no_config(tmp_path):
    for cond in _detection_conditions():
        result = subprocess.run(["sh", "-c", cond], cwd=tmp_path)
        assert result.returncode != 0, f"lint detection found a config in an empty dir: {cond!r}"
