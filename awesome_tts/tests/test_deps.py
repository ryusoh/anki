# -*- coding: utf-8 -*-
"""Tests for awesometts.deps runtime dependency bootstrap."""

import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from awesome_tts.awesometts import deps


@pytest.fixture
def _not_importable(monkeypatch):
    monkeypatch.setattr(deps, '_edge_tts_importable', lambda: False)


def test_deps_dir_prefers_profile_base(monkeypatch):
    fake_aqt = types.SimpleNamespace(
        mw=types.SimpleNamespace(pm=types.SimpleNamespace(base='/data/Anki2'))
    )
    monkeypatch.setitem(sys.modules, 'aqt', fake_aqt)

    assert deps.deps_dir() == Path('/data/Anki2/awesome_tts_deps')


def test_deps_dir_falls_back_to_package_path():
    # conftest's aqt is a MagicMock, so pm.base is not a string and the
    # fallback derived from this file's location is used.
    derived = deps.deps_dir()

    assert derived.name == 'awesome_tts_deps'
    assert derived.parent == Path(deps.__file__).resolve().parents[3]


def test_ensure_deps_on_path_short_circuits_when_importable(monkeypatch):
    monkeypatch.setattr(deps, '_edge_tts_importable', lambda: True)

    assert deps.ensure_deps_on_path() is True


def test_ensure_deps_on_path_appends_existing_dir(monkeypatch, tmp_path):
    (tmp_path / 'edge_tts').mkdir()
    monkeypatch.setattr(deps, 'deps_dir', lambda: tmp_path)
    importable = iter([False, True])
    monkeypatch.setattr(deps, '_edge_tts_importable', lambda: next(importable))

    try:
        assert deps.ensure_deps_on_path() is True
        assert str(tmp_path) in sys.path
        # The deps dir is appended so Anki's bundled packages keep precedence.
        assert sys.path.index(str(tmp_path)) > 0
    finally:
        sys.path.remove(str(tmp_path))


def test_ensure_deps_on_path_missing_dir(monkeypatch, tmp_path, _not_importable):
    monkeypatch.setattr(deps, 'deps_dir', lambda: tmp_path)

    assert deps.ensure_deps_on_path() is False
    assert str(tmp_path) not in sys.path


def test_find_pip_python_picks_first_working_candidate(monkeypatch):
    monkeypatch.setattr(
        deps.shutil, 'which', lambda name: f'/usr/bin/{name}' if name == 'python3' else None
    )

    def fake_run(command, **_kwargs):
        result = MagicMock()
        result.returncode = 0 if command[0] == '/usr/bin/python3' else 1
        return result

    monkeypatch.setattr(deps.subprocess, 'run', fake_run)

    assert deps._find_pip_python() == '/usr/bin/python3'


def test_find_pip_python_skips_broken_candidates(monkeypatch):
    monkeypatch.setattr(deps.shutil, 'which', lambda _name: '/missing/python3')
    monkeypatch.setattr(deps.subprocess, 'run', MagicMock(side_effect=OSError('no such file')))

    assert deps._find_pip_python() is None


def test_run_bootstrap_short_circuits_when_already_importable(monkeypatch):
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: True)

    assert deps.run_bootstrap() is True


def test_run_bootstrap_gives_up_without_python(monkeypatch, _not_importable):
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: None)

    assert deps.run_bootstrap() is False


def _pip_success(command, **_kwargs):
    staging = Path(command[command.index('--target') + 1])
    (staging / 'edge_tts').mkdir(parents=True)
    return MagicMock(returncode=0, stderr='')


def test_run_bootstrap_installs_atomically(monkeypatch, tmp_path):
    target = tmp_path / 'awesome_tts_deps'
    monkeypatch.setattr(deps, 'deps_dir', lambda: target)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/usr/bin/python3')
    ready = iter([False, True])
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: next(ready))

    assert deps.run_bootstrap(run=_pip_success) is True
    assert (target / 'edge_tts').is_dir()
    assert not list(tmp_path.glob('.*.staging-*'))


def test_run_bootstrap_cleans_staging_on_pip_failure(monkeypatch, tmp_path):
    target = tmp_path / 'awesome_tts_deps'
    monkeypatch.setattr(deps, 'deps_dir', lambda: target)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/usr/bin/python3')
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)

    def pip_fail(command, **_kwargs):
        staging = Path(command[command.index('--target') + 1])
        staging.mkdir(parents=True)
        return MagicMock(returncode=1, stderr='resolution failed')

    assert deps.run_bootstrap(run=pip_fail) is False
    assert not target.exists()
    assert not list(tmp_path.glob('.*.staging-*'))


def test_run_bootstrap_reports_pip_spawn_error(monkeypatch, tmp_path):
    monkeypatch.setattr(deps, 'deps_dir', lambda: tmp_path / 'deps')
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/usr/bin/python3')
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)

    def pip_spawn_error(_command, **_kwargs):
        raise subprocess.TimeoutExpired(cmd='pip', timeout=1)

    assert deps.run_bootstrap(run=pip_spawn_error) is False


def test_run_bootstrap_discards_staging_when_target_appeared(monkeypatch, tmp_path):
    target = tmp_path / 'awesome_tts_deps'
    monkeypatch.setattr(deps, 'deps_dir', lambda: target)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/usr/bin/python3')
    ready = iter([False, True])
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: next(ready))

    def pip_race(command, **_kwargs):
        result = _pip_success(command)
        (target / 'edge_tts').mkdir(parents=True)  # another process won the race
        return result

    assert deps.run_bootstrap(run=pip_race) is True
    assert (target / 'edge_tts').is_dir()
    assert not list(tmp_path.glob('.*.staging-*'))


def test_pip_install_command_targets_running_python_version(monkeypatch):
    monkeypatch.setattr(deps, '_wheel_platform_tags', lambda: ['macosx_11_0_arm64'])

    command = deps._pip_install_command('/usr/bin/python3', Path('/tmp/staging'))

    version = f'{sys.version_info.major}.{sys.version_info.minor}'
    assert command[command.index('--python-version') + 1] == version
    assert command[command.index('--platform') + 1] == 'macosx_11_0_arm64'
    assert command[-1] == deps.EDGE_TTS_SPEC


def test_wheel_platform_tags_only_on_darwin(monkeypatch):
    monkeypatch.setattr(deps.platform, 'system', lambda: 'Linux')

    assert deps._wheel_platform_tags() == []

    monkeypatch.setattr(deps.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(deps.platform, 'machine', lambda: 'x86_64')

    assert all('x86_64' in tag for tag in deps._wheel_platform_tags())


def test_bootstrap_background_no_thread_when_importable(monkeypatch):
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: True)

    assert deps.bootstrap_edge_tts_background() is None


def test_bootstrap_background_starts_daemon_thread(monkeypatch):
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)
    thread = MagicMock()
    thread_class = MagicMock(return_value=thread)
    monkeypatch.setattr(deps.threading, 'Thread', thread_class)

    assert deps.bootstrap_edge_tts_background() is thread
    assert thread_class.call_args.kwargs['daemon'] is True
    assert thread_class.call_args.kwargs['target'] is deps.run_bootstrap
    thread.start.assert_called_once()
