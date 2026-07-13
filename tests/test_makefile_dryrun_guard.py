"""Regression guard: `make -n precommit-fix` must refuse, not execute.

GNU make executes `$(MAKE)`-bearing recipe lines even under -n/-q/-t, and
precommit-fix's recipe is ONE $(MAKE)-bearing compound command — so a
"dry run" used to run the REAL git add/commit/push step (2026-07-13: an
attempted `make -n` syntax check created two junk commits). The Makefile now
refuses at parse time (before prerequisites, which would otherwise block on a
read prompt). These tests run the real `make -n` against the real repo: if
the guard regresses, the run is still harmless here (no YOLO/MSG → the commit
step is skipped; SKIP=1 → no fetch/network), but the assertions go red.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout


def test_dry_run_of_precommit_fix_is_refused():
    before = _head()
    result = subprocess.run(
        ["make", "-n", "precommit-fix", "SKIP=1"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0, (
        "make -n precommit-fix did not refuse — the $(MAKE)-bearing recipe "
        "would have executed the real commit/push step"
    )
    assert "NOT a dry run" in result.stderr + result.stdout
    assert _head() == before, "make -n precommit-fix created a commit(!)"


def test_dry_run_of_other_targets_still_works():
    result = subprocess.run(
        ["make", "-n", "help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"guard misfires on unrelated goals: {result.stderr!r}"
