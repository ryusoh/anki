"""Tests for tools/check_jsdom_pin.mjs — the jsdom version-pin guard.

The guard used to be an inline `node -e ' \\ ...'` Makefile script, which is
a make-version trap (see test_makefile_no_inline_multiline_scripts.py). Now
it is a real file; these tests prove it still does its one job: exit 0 on
exactly jsdom "27.0.0", exit 1 with a pointer to docs/js-testing.md on
anything else.
"""

import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "check_jsdom_pin.mjs"


def _run_with_pin(tmp_path, version):
    """The script resolves package.json relative to itself (../package.json)."""
    (tmp_path / "tools").mkdir(exist_ok=True)
    shutil.copy(SCRIPT, tmp_path / "tools" / SCRIPT.name)
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"jsdom": version}}))
    return subprocess.run(
        ["node", str(tmp_path / "tools" / SCRIPT.name)], capture_output=True, text=True
    )


def test_repo_package_json_passes_the_guard():
    result = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, f"guard rejects the repo's own pin: {result.stderr}"


def test_exact_pin_passes(tmp_path):
    assert _run_with_pin(tmp_path, "27.0.0").returncode == 0


def test_any_other_version_fails_with_explanation(tmp_path):
    for bad in ("27.0.1", "^27.0.0", "~27.0.0"):
        result = _run_with_pin(tmp_path, bad)
        assert result.returncode == 1, f"guard accepted jsdom {bad!r}"
        assert "docs/js-testing.md" in result.stderr
