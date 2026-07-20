"""Regression guard: precommit-fix must not swallow a failed `git push`.

Observed 2026-07-13 (`make precommit-fix YOLO=1` on a slow uplink): the push
died with `RPC failed; HTTP 408` mid-upload, but the recipe's
`git commit && git push && ...` chain result was discarded — the final exit
guard only checked GATE_OK/SEC_OK, so make exited 0 with the commit silently
unpushed. These tests pin the fix:

* the recipe pushes via tools/git_push_retry.py (retry + chunked fallback for
  limited-network conditions), never a bare one-shot `git push`;
* a failed commit/push flips PUSH_OK=0, and the recipe's exit guard turns
  that into a non-zero exit;
* an empty index skips `git commit` without aborting the chain, so a rerun
  with nothing new to commit still retries a previously failed push.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"


def _precommit_fix_recipe() -> str:
    text = MAKEFILE.read_text()
    match = re.search(r"^precommit-fix:.*\n((?:\t.*\n)+)", text, re.M)
    assert match, "precommit-fix recipe not found in Makefile"
    return match.group(1)


def test_push_goes_through_retry_wrapper_not_bare_git_push():
    recipe = _precommit_fix_recipe()
    assert "tools/git_push_retry.py" in recipe, (
        "precommit-fix no longer pushes via tools/git_push_retry.py — a bare "
        "`git push` dies with HTTP 408 on slow uplinks and has no retry"
    )
    # Command position only (line start) — the recipe's error message may
    # legitimately *mention* 'git push' inside an echo.
    assert not re.search(r"^\s*git push\b", recipe, re.M), (
        "precommit-fix contains a bare one-shot `git push` command — route it "
        "through tools/git_push_retry.py"
    )


def test_push_failure_flips_push_ok_and_exit_guard_checks_it():
    recipe = _precommit_fix_recipe()
    assert "PUSH_OK=1" in recipe and "PUSH_OK=0" in recipe, (
        "precommit-fix no longer tracks push success in PUSH_OK — a failed "
        "push would be swallowed again (exit 0, commit silently unpushed)"
    )
    guard = re.search(r'if \[ "\$\$PUSH_OK" != "1" \];.*?exit 1', recipe, re.S)
    assert guard, "no exit-1 guard on PUSH_OK in the precommit-fix recipe"


def test_push_ok_guard_actually_exits_nonzero():
    """Execute the extracted guard under sh, both ways."""
    recipe = _precommit_fix_recipe()
    match = re.search(r'(if \[ "\$\$PUSH_OK" != "1" \];.*?exit 1; \\\n\tfi)', recipe, re.S)
    assert match, "PUSH_OK guard not found in expected shape"
    # Un-escape from make-recipe form to plain shell.
    guard = match.group(1).replace("$$", "$").replace("\\\n", "\n")
    failed = subprocess.run(["sh", "-c", f"PUSH_OK=0; {guard}"], capture_output=True)
    assert failed.returncode == 1, "guard let a failed push exit 0"
    ok = subprocess.run(["sh", "-c", f"PUSH_OK=1; {guard}"], capture_output=True)
    assert ok.returncode == 0, "guard failed a successful push"


def test_empty_index_skips_commit_but_not_push():
    recipe = _precommit_fix_recipe()
    assert "git diff --cached --quiet ||" in recipe, (
        "precommit-fix aborts on an empty index again — with nothing new to "
        "commit it must still reach the push, so a rerun after a failed push "
        "retries it"
    )


def test_auto_rebase_flag_only_in_unattended_push_path():
    recipe = _precommit_fix_recipe()
    assert (
        "tools/git_push_retry.py $$_rebase_flag" in recipe
    ), "precommit-fix no longer passes a dynamic rebase flag to git_push_retry.py"
    assert (
        '--auto-rebase' in recipe
    ), "precommit-fix does not enable --auto-rebase for git_push_retry.py"
    assert (
        'if [ "$(YOLO)" = "1" ] || [ -n "$(MSG)" ]; then _rebase_flag="--auto-rebase"; fi' in recipe
    ), "--auto-rebase must only be set in unattended YOLO=1 or MSG= push mode"
