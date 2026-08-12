# -*- coding: utf-8 -*-
"""Regression tests for the router's media cache-hit logic."""

import logging
import os
from types import SimpleNamespace

from awesome_tts.awesometts.router import Router


class _StubService:
    """Minimal service double: records run() calls and writes real bytes."""

    NAME = "Stub"
    TRAITS = []

    def __init__(self, *args, **kwargs):
        self.run_calls = 0

    def options(self):
        return []

    def modify(self, text):
        return text

    def net_reset(self):
        pass

    def net_count(self):
        return 0

    def run(self, text, options, path):
        self.run_calls += 1
        with open(path, 'wb') as file:
            file.write(b'audio-bytes')


def _make_router(cache_dir, temp_dir):
    services = SimpleNamespace(
        mappings=[('stub', _StubService)],
        dead={},
        aliases=[],
        normalize=lambda value: value,
        args=(),
        kwargs={},
    )
    router = Router(services, str(cache_dir), str(temp_dir), logging.getLogger('test'), {})

    # Run "async" spawns synchronously so tests need no Qt event loop.
    def sync_spawn(task, callback):
        exception = None
        try:
            task()
        except Exception as exc:  # noqa: BLE001 - mirrors _Pool's pass-through
            exception = exc
        callback(exception)

    router._pool = SimpleNamespace(spawn=sync_spawn)
    return router


def _collect(router, text):
    results = {}
    router(
        'stub',
        text,
        {},
        callbacks={
            'okay': lambda path: results.setdefault('okay', path),
            'fail': lambda exc, _text: results.setdefault('fail', exc),
        },
    )
    return results


def test_empty_cache_file_is_not_a_hit(tmp_path):
    """A 0-byte leftover from a failed download must not count as a cache hit.

    Regression: a failed edge-tts download left an empty file at the cache
    path; the retry was served that empty file as a "hit", and the silent
    clip ended up on the card.
    """
    cache_dir = tmp_path / 'cache'
    cache_dir.mkdir()
    router = _make_router(cache_dir, tmp_path / 'temp')

    # Poison the cache path the way a failed download does.
    path = router._path_cache('stub', 'cormorant', {})
    open(path, 'wb').close()

    results = _collect(router, 'cormorant')

    assert 'fail' not in results
    assert router._services.lookup['stub']['instance'].run_calls == 1
    assert os.path.getsize(results['okay']) > 0


def test_nonempty_cache_file_is_a_hit(tmp_path):
    """A real cached file is still served without re-running the service."""
    cache_dir = tmp_path / 'cache'
    cache_dir.mkdir()
    router = _make_router(cache_dir, tmp_path / 'temp')

    path = router._path_cache('stub', 'cormorant', {})
    with open(path, 'wb') as file:
        file.write(b'cached-audio')

    results = _collect(router, 'cormorant')

    assert 'fail' not in results
    assert router._services.lookup['stub']['instance'].run_calls == 0
    assert results['okay'] == path
