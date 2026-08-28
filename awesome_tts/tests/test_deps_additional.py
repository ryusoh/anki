import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import awesome_tts.awesometts.deps as deps

def test_deps_dir_type_error(monkeypatch):
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == 'aqt':
            raise TypeError("test")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr('builtins.__import__', fake_import)

    derived = deps.deps_dir()
    assert derived.name == 'awesome_tts_deps'
    assert derived.parent == Path(deps.__file__).resolve().parents[3]

def test_ensure_deps_on_path_broken_install(monkeypatch, tmp_path):
    (tmp_path / 'edge_tts').mkdir()
    monkeypatch.setattr(deps, 'deps_dir', lambda: tmp_path)
    importable_vals = iter([False, False])
    monkeypatch.setattr(deps, '_edge_tts_importable', lambda: next(importable_vals))

    assert deps.ensure_deps_on_path() is False
    assert str(tmp_path) not in sys.path

def test_find_pip_python_oserror_outer(monkeypatch):
    monkeypatch.setattr(deps.shutil, 'which', lambda name: '/mock/bin/python3')
    monkeypatch.setattr(deps.os.path, 'realpath', lambda p: p + "_real")

    def fake_run(command, **kwargs):
        raise OSError("test")
    monkeypatch.setattr(deps.subprocess, 'run', fake_run)

    assert deps._find_pip_python() is None

def test_wheel_platform_tags_arm_fallback(monkeypatch):
    monkeypatch.setattr(deps.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(deps.platform, 'machine', lambda: 'arm64')

    tags = deps._wheel_platform_tags()
    assert 'macosx_11_0_arm64' in tags

def test_run_bootstrap_timeout(monkeypatch):
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/mock/python')
    monkeypatch.setattr(deps, 'deps_dir', lambda: Path('/mock/target'))

    def fake_run(command, **kwargs):
        raise deps.subprocess.TimeoutExpired(cmd=command, timeout=30)

    assert deps.run_bootstrap(run=fake_run) is False

def test_bootstrap_background_exception(monkeypatch):
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)

    def fake_thread(**kwargs):
        raise Exception("test")
    monkeypatch.setattr(deps.threading, 'Thread', fake_thread)

    assert deps.bootstrap_edge_tts_background() is None

def test_ensure_deps_on_path_already_in_sys_path(monkeypatch, tmp_path):
    (tmp_path / 'edge_tts').mkdir()
    monkeypatch.setattr(deps, 'deps_dir', lambda: tmp_path)
    import sys
    sys.path.append(str(tmp_path))
    importable = iter([False, True])
    monkeypatch.setattr(deps, '_edge_tts_importable', lambda: next(importable))

    try:
        assert deps.ensure_deps_on_path() is True
    finally:
        sys.path.remove(str(tmp_path))

def test_find_pip_python_same_executable(monkeypatch):
    # the hardcoded paths in the loop will trigger subprocess.run
    # mock it out to return failure
    def fake_run(command, **kwargs):
        return MagicMock(returncode=1)
    monkeypatch.setattr(deps.subprocess, 'run', fake_run)

    # but make which return sys.executable to trigger the continue at 153
    monkeypatch.setattr(deps.shutil, 'which', lambda name: sys.executable)

    assert deps._find_pip_python() is None

def test_run_bootstrap_success_ready(monkeypatch):
    import sys
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/mock/python')
    monkeypatch.setattr(deps, 'deps_dir', lambda: Path('/mock/target'))

    def fake_run(command, **kwargs):
        return MagicMock(returncode=0, stderr='')

    monkeypatch.setattr(deps.os, 'rename', lambda *args: None)

    # mock ensure_deps_on_path for the second check
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: True)

    assert deps.run_bootstrap(run=fake_run) is True


def test_run_bootstrap_success_not_ready(monkeypatch):
    import sys
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False)
    monkeypatch.setattr(deps, '_find_pip_python', lambda: '/mock/python')
    monkeypatch.setattr(deps, 'deps_dir', lambda: Path('/mock/target'))

    def fake_run(command, **kwargs):
        return MagicMock(returncode=0, stderr='')

    monkeypatch.setattr(deps.os, 'rename', lambda *args: None)

    # mock ensure_deps_on_path for the second check
    monkeypatch.setattr(deps, 'ensure_deps_on_path', lambda: False) # this time false

    assert deps.run_bootstrap(run=fake_run) is False
