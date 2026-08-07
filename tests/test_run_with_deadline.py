"""Tests for tools/run_with_deadline.py — the network-job watchdog.

precommit-fix `wait`s on backgrounded R2/graph-push jobs; on a limited uplink
their uploads trickle for hours (per-request timeouts never fire while bytes
still flow) and the recipe hung forever (observed 2026-07-13). The wrapper
must propagate a fast child's exit code untouched, kill a slow child's WHOLE
process group at the deadline, and exit 124 so the recipe reports the timeout.
"""

import signal
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

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


def test_kill_group_process_lookup_error_on_sigterm():
    child = MagicMock()
    with patch('os.killpg', side_effect=ProcessLookupError):
        run_with_deadline._kill_group(child)
        assert not child.wait.called


def test_kill_group_process_lookup_error_on_sigkill():
    child = MagicMock()
    child.wait.side_effect = [subprocess.TimeoutExpired(cmd="test", timeout=1), None]

    def mock_killpg(pid, sig):
        if sig == signal.SIGKILL:
            raise ProcessLookupError

    with patch('os.killpg', side_effect=mock_killpg):
        run_with_deadline._kill_group(child)
        assert child.wait.call_count == 2


def test_main_no_command_given(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_with_deadline.main(['--seconds', '10'])
    assert excinfo.value.code == 2


def test_main_no_command_given_with_dash_dash(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_with_deadline.main(['--seconds', '10', '--'])
    assert excinfo.value.code == 2

def test_run_as_main():
    import runpy
    import sys
    with patch.object(sys, 'argv', ['run_with_deadline.py', '--seconds', '0.1', '--', 'true']):
        # If we use run_module, it executes the __main__ block
        import pytest
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module('tools.run_with_deadline', run_name='__main__')
        assert excinfo.value.code == 0
