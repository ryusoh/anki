"""Tests for tools/git_push_retry.py — the limited-network push wrapper.

`make precommit-fix YOLO=1` pushes over HTTPS; on a slow uplink the server
408s the request once the pack upload outlives its window (seen 2026-07-13:
7.5 MiB at 53 KiB/s → `RPC failed; HTTP 408`). The wrapper must retry with
backoff, fall back to pushing unpushed commits one at a time (smaller HTTP
requests, progress kept across retries), and exit non-zero if the branch is
still unpushed.

Unit tests fake the git boundary (no network); one integration test drives a
real local bare remote to validate the chunked refspec push end to end.
"""

import subprocess
from unittest.mock import patch

from tools import git_push_retry


class FakeGit:
    """Scriptable stand-in for the module's _git_run/_git_capture boundary.

    `full_push_results` / `chunk_push_results` are consumed one per call;
    when a list runs dry its last value repeats.
    """

    def __init__(
        self, upstream='origin/main', unpushed=(), full_push_results=(1,), chunk_push_results=(0,)
    ):
        self.upstream = upstream
        self.unpushed = list(unpushed)
        self.full_push_results = list(full_push_results)
        self.chunk_push_results = list(chunk_push_results)
        self.run_calls = []

    def _next(self, results):
        return results.pop(0) if len(results) > 1 else results[0]

    def git_run(self, args):
        self.run_calls.append(args)
        if args[-1] == 'push':
            code = self._next(self.full_push_results)
        else:
            code = self._next(self.chunk_push_results)
        if code == 0 and self.unpushed:
            # A successful push lands everything it targeted.
            if args[-1] == 'push':
                self.unpushed = []
            else:
                sha = args[-1].split(':', 1)[0]
                self.unpushed = self.unpushed[self.unpushed.index(sha) + 1 :]
        return code

    def git_capture(self, args):
        if args[:2] == ['rev-parse', '--abbrev-ref']:
            if self.upstream is None:
                return subprocess.CompletedProcess(args, 128, stdout='', stderr='no upstream')
            return subprocess.CompletedProcess(args, 0, stdout=self.upstream + '\n', stderr='')
        if args[0] == 'rev-list':
            return subprocess.CompletedProcess(args, 0, stdout='\n'.join(self.unpushed), stderr='')
        raise AssertionError(f'unexpected capture: {args}')


def run_main(fake, argv=()):
    with (
        patch.object(git_push_retry, '_git_run', fake.git_run),
        patch.object(git_push_retry, '_git_capture', fake.git_capture),
        patch.object(git_push_retry.time, 'sleep') as sleep,
    ):
        code = git_push_retry.main(list(argv))
    return code, sleep


def test_success_first_try_pushes_once_without_sleeping():
    fake = FakeGit(unpushed=['aaa'], full_push_results=[0])
    code, sleep = run_main(fake)
    assert code == 0
    assert fake.run_calls == [['push']]
    sleep.assert_not_called()


def test_chunked_fallback_pushes_oldest_first_with_refspecs():
    fake = FakeGit(unpushed=['aaa', 'bbb'], full_push_results=[1], chunk_push_results=[0])
    code, _ = run_main(fake)
    assert code == 0
    assert fake.run_calls == [
        ['push'],
        ['push', 'origin', 'aaa:refs/heads/main'],
        ['push', 'origin', 'bbb:refs/heads/main'],
    ]


def test_chunked_refspec_keeps_slashes_in_branch_name():
    fake = FakeGit(
        upstream='origin/feature/x',
        unpushed=['aaa', 'bbb'],
        full_push_results=[1],
        chunk_push_results=[0],
    )
    code, _ = run_main(fake)
    assert code == 0
    assert fake.run_calls[1] == ['push', 'origin', 'aaa:refs/heads/feature/x']


def test_retry_uses_backoff_and_http11_config():
    fake = FakeGit(unpushed=['aaa'], full_push_results=[1, 0])
    code, sleep = run_main(fake, ['--base-delay', '5'])
    assert code == 0
    sleep.assert_called_once_with(5.0)
    retry_push = fake.run_calls[1]
    assert 'http.version=HTTP/1.1' in retry_push
    assert any(c.startswith('http.postBuffer=') for c in retry_push)
    assert retry_push[-1] == 'push'


def test_exhausted_attempts_exit_nonzero_with_exponential_backoff():
    fake = FakeGit(unpushed=['aaa'], full_push_results=[1])
    code, sleep = run_main(fake, ['--attempts', '3', '--base-delay', '10'])
    assert code == 1
    assert [c.args[0] for c in sleep.call_args_list] == [10.0, 20.0]
    # Single unpushed commit → chunking can't shrink anything; only full pushes.
    assert all(c[-1] == 'push' for c in fake.run_calls)
    assert len(fake.run_calls) == 3


def test_partial_chunk_progress_is_kept_across_attempts():
    # Attempt 1: full push fails, chunk 'aaa' lands, chunk 'bbb' fails.
    # Attempt 2: only 'bbb' is left, so the (now equally small) full push lands it —
    # 'aaa' must not be re-uploaded.
    fake = FakeGit(unpushed=['aaa', 'bbb'], full_push_results=[1, 0], chunk_push_results=[0, 1])
    code, _ = run_main(fake, ['--attempts', '2'])
    assert code == 0
    chunk_calls = [c for c in fake.run_calls if c[-1] != 'push']
    assert [c[-1] for c in chunk_calls] == [
        'aaa:refs/heads/main',
        'bbb:refs/heads/main',
    ]
    assert fake.unpushed == []


def test_no_upstream_means_no_chunking_just_plain_retries():
    fake = FakeGit(upstream=None, full_push_results=[1])
    code, _ = run_main(fake, ['--attempts', '2'])
    assert code == 1
    assert all(c[-1] == 'push' for c in fake.run_calls)


def _git(cwd, *args):
    subprocess.run(['git', '-C', str(cwd), *args], check=True, capture_output=True)


def test_integration_chunked_push_against_real_local_remote(tmp_path, monkeypatch):
    """The refspec form must actually land commits and advance @{u}."""
    remote = tmp_path / 'remote.git'
    subprocess.run(
        ['git', 'init', '--bare', '-b', 'main', str(remote)], check=True, capture_output=True
    )
    clone = tmp_path / 'clone'
    subprocess.run(['git', 'clone', str(remote), str(clone)], check=True, capture_output=True)
    _git(clone, 'config', 'user.email', 'test@example.com')
    _git(clone, 'config', 'user.name', 'test')
    for i in range(3):
        (clone / f'f{i}.txt').write_text(str(i))
        _git(clone, 'add', '-A')
        _git(clone, 'commit', '-m', f'c{i}')
    _git(clone, 'push', '-u', 'origin', 'main')
    for i in range(3, 5):
        (clone / f'f{i}.txt').write_text(str(i))
        _git(clone, 'add', '-A')
        _git(clone, 'commit', '-m', f'c{i}')

    monkeypatch.chdir(clone)
    assert len(git_push_retry.unpushed_commits()) == 2
    assert git_push_retry._push_one_by_one([]) is True
    assert git_push_retry.unpushed_commits() == []
    local = subprocess.run(
        ['git', '-C', str(clone), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True
    ).stdout
    on_remote = subprocess.run(
        ['git', '-C', str(remote), 'rev-parse', 'main'], check=True, capture_output=True, text=True
    ).stdout
    assert local == on_remote
