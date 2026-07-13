#!/usr/bin/env python3
"""Run a command under a hard wall-clock deadline, killing its process group.

precommit-fix backgrounds its network jobs (R2 upload, public graph push) and
`wait`s on them before exiting. The upload clients have per-request timeouts,
but on a limited-bandwidth link bytes keep trickling so no timeout ever fires —
the jobs crawl for hours and the recipe hangs "forever" (observed 2026-07-13).
macOS ships no `timeout(1)`, so this is the portable equivalent.

The child runs in its own session (process group), so the TERM/KILL on expiry
reaches grandchildren too (`make` → `python3 upload-to-r2`). Exit code is the
child's own, or 124 when the deadline killed it (GNU timeout convention).

Usage: run_with_deadline.py --seconds N -- command [args...]
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys

KILL_GRACE_SECONDS = 10.0
TIMEOUT_EXIT_CODE = 124


def _kill_group(child: 'subprocess.Popen[bytes]') -> None:
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        child.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='run a command with a hard wall-clock deadline (its process group '
        'is killed on expiry; exit 124)'
    )
    parser.add_argument('--seconds', type=float, required=True, help='deadline in seconds')
    parser.add_argument('cmd', nargs=argparse.REMAINDER, help='-- command [args...]')
    opts = parser.parse_args(argv)
    cmd = opts.cmd[1:] if opts.cmd and opts.cmd[0] == '--' else opts.cmd
    if not cmd:
        parser.error('no command given (usage: --seconds N -- command args...)')

    child = subprocess.Popen(cmd, start_new_session=True)
    try:
        return child.wait(timeout=opts.seconds)
    except subprocess.TimeoutExpired:
        print(
            f'⏱  Deadline of {opts.seconds:.0f}s exceeded — killing: {" ".join(cmd)}',
            file=sys.stderr,
            flush=True,
        )
        _kill_group(child)
        return TIMEOUT_EXIT_CODE


if __name__ == '__main__':
    raise SystemExit(main())
