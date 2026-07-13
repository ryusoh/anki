#!/usr/bin/env python3
"""Push with retries and a chunked fallback for limited-network conditions.

A bare `git push` over HTTPS dies on a slow uplink: the server times the
request out once the pack upload exceeds its window and returns HTTP 408
(`RPC failed; HTTP 408 curl 22` + `unexpected disconnect while reading
sideband packet`), and none of the upload is kept. Observed 2026-07-13 from
`make precommit-fix YOLO=1`: a 7.5 MiB pack at 53 KiB/s.

Strategy, per attempt:

1. Plain `git push` — the fast path costs nothing extra.
2. If that fails and more than one commit is unpushed, push the commits one
   at a time, oldest first. Each becomes its own, smaller HTTP request, and
   every chunk that lands moves the remote-tracking ref forward — a later
   attempt re-lists only what's left.

Retries are spaced with exponential backoff and force HTTP/1.1 plus a large
http.postBuffer (one buffered POST with a Content-Length instead of chunked
transfer-encoding — the standard remedy for proxy/408 push failures).

Exits non-zero if the branch is still not fully pushed, so callers (the
precommit-fix recipe) cannot mistake a failed push for success.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

RETRY_GIT_CONFIG = [
    '-c',
    'http.version=HTTP/1.1',
    '-c',
    'http.postBuffer=157286400',
]


def _git_run(args: list[str]) -> int:
    """Run git with output streaming to the terminal; return its exit code."""
    return subprocess.run(['git', *args], check=False).returncode


def _git_capture(args: list[str]) -> 'subprocess.CompletedProcess[str]':
    return subprocess.run(['git', *args], check=False, capture_output=True, text=True)


def upstream_branch() -> str | None:
    """Upstream of HEAD as 'remote/branch', or None if none is configured."""
    res = _git_capture(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
    if res.returncode != 0:
        return None
    return res.stdout.strip() or None


def unpushed_commits() -> list[str]:
    """SHAs on HEAD but not on its upstream, oldest first ([] if no upstream)."""
    if upstream_branch() is None:
        return []
    res = _git_capture(['rev-list', '--reverse', '@{u}..HEAD'])
    if res.returncode != 0:
        return []
    return res.stdout.split()


def _push_full(config: list[str]) -> bool:
    return _git_run([*config, 'push']) == 0


def _push_one_by_one(config: list[str]) -> bool:
    upstream = upstream_branch()
    if upstream is None:
        return False
    remote, _, branch = upstream.partition('/')
    for sha in unpushed_commits():
        print(f'  ⛓  pushing {sha[:12]} → {upstream}', flush=True)
        if _git_run([*config, 'push', remote, f'{sha}:refs/heads/{branch}']) != 0:
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='git push with retries and a chunked fallback for slow links'
    )
    parser.add_argument('--attempts', type=int, default=3, help='total push attempts (default 3)')
    parser.add_argument(
        '--base-delay',
        type=float,
        default=10.0,
        help='seconds before the first retry; doubles each retry (default 10)',
    )
    opts = parser.parse_args(argv)

    for attempt in range(1, opts.attempts + 1):
        if attempt > 1:
            delay = opts.base_delay * 2 ** (attempt - 2)
            print(
                f'🔁 Retrying push in {delay:.0f}s (attempt {attempt}/{opts.attempts},'
                ' HTTP/1.1 + buffered POST)...',
                flush=True,
            )
            time.sleep(delay)
        config = [] if attempt == 1 else RETRY_GIT_CONFIG
        if _push_full(config):
            return 0
        pending = unpushed_commits()
        if len(pending) > 1:
            print(
                f'⚠️  Full push failed with {len(pending)} commits queued —'
                ' pushing one commit at a time...',
                flush=True,
            )
            if _push_one_by_one(config):
                return 0
    print(
        f'❌ Push failed after {opts.attempts} attempts. Your commits are safe locally —'
        ' rerun `python3 tools/git_push_retry.py` (or plain `git push`) when the'
        ' network recovers.',
        file=sys.stderr,
    )
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
