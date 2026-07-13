"""Tests for tools/run_with_deadline.py — the network-job watchdog.

precommit-fix `wait`s on backgrounded R2/graph-push jobs; on a limited uplink
their uploads trickle for hours (per-request timeouts never fire while bytes
still flow) and the recipe hung forever (observed 2026-07-13). The wrapper
must propagate a fast child's exit code untouched, kill a slow child's WHOLE
process group at the deadline, and exit 124 so the recipe reports the timeout.
"""

import time

from tools import run_with_deadline


def test_fast_child_exit_code_is_propagated():
    assert run_with_deadline.main(['--seconds', '30', '--', 'sh', '-c', 'exit 7']) == 7


def test_fast_child_success_is_zero():
    assert run_with_deadline.main(['--seconds', '30', '--', 'true']) == 0


def test_slow_child_is_killed_at_deadline_with_exit_124():
    start = time.monotonic()
    code = run_with_deadline.main(['--seconds', '0.3', '--', 'sleep', '30'])
    elapsed = time.monotonic() - start
    assert code == run_with_deadline.TIMEOUT_EXIT_CODE
    assert elapsed < 5, f'kill took {elapsed:.1f}s — grace/kill path is wedged'


def test_grandchildren_in_the_process_group_are_killed_too(tmp_path):
    """A `make → python3 upload` tree must die with its parent.

    The child backgrounds a grandchild that would write a marker after 2s;
    if only the direct child were killed, the orphaned grandchild would
    survive and the marker would appear.
    """
    marker = tmp_path / 'survived'
    code = run_with_deadline.main(
        ['--seconds', '0.3', '--', 'sh', '-c', f'(sleep 2; touch "{marker}") & sleep 30']
    )
    assert code == run_with_deadline.TIMEOUT_EXIT_CODE
    time.sleep(2.5)
    assert not marker.exists(), 'grandchild outlived the deadline kill — group kill regressed'
