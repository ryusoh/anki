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
