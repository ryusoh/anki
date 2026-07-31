# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
# Copyright (C) 2010-Present  Anki AwesomeTTS Development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Runtime bootstrap for the optional edge-tts dependency.

Anki's bundled Python is frozen and has no pip, so third-party packages are
installed by an external python3 into a deps directory inside Anki's data
folder (a sibling of ``addons21``), and this module puts that directory on
``sys.path``. When edge-tts is missing at add-on load, a daemon thread
installs it silently; the next single-click can then use it without
restarting Anki.
"""

import os
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path

__all__ = [
    'EDGE_TTS_SPEC',
    'bootstrap_edge_tts_background',
    'deps_dir',
    'ensure_deps_on_path',
    'run_bootstrap',
]

EDGE_TTS_SPEC = 'edge-tts>=7.0,<8'

_DEPS_DIRNAME = 'awesome_tts_deps'
_PIP_TIMEOUT_SEC = 600


def _log(message):
    print(f'AwesomeTTS deps: {message}', file=sys.stderr)


def deps_dir():
    """Return the directory holding runtime-installed packages."""
    try:
        import aqt

        base = aqt.mw.pm.base
    except (ImportError, AttributeError, TypeError):
        base = None
    if isinstance(base, str) and base:
        return Path(base) / _DEPS_DIRNAME
    # Fallback: <Anki2>/addons21/awesome_tts/awesometts/deps.py
    return Path(__file__).resolve().parents[3] / _DEPS_DIRNAME


def _edge_tts_importable():
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return False
    return True


def ensure_deps_on_path():
    """Put the deps directory on sys.path if needed; True if edge_tts imports."""
    if _edge_tts_importable():
        return True
    target = deps_dir()
    if (target / 'edge_tts').is_dir() and str(target) not in sys.path:
        # Appended, not prepended, so Anki's own bundled packages (e.g.
        # certifi) keep precedence over the runtime-installed copies.
        sys.path.append(str(target))
    return _edge_tts_importable()


def _wheel_platform_tags():
    """pip --platform tags for this machine ([] lets pip use its defaults)."""
    if platform.system() != 'Darwin':
        return []
    if platform.machine() == 'arm64':
        return [
            'macosx_11_0_arm64',
            'macosx_11_0_universal2',
            'macosx_10_13_universal2',
            'macosx_10_9_universal2',
        ]
    return ['macosx_10_13_x86_64', 'macosx_10_9_x86_64']


def _pip_install_command(executable, staging):
    """Build a pip command that installs for Anki's Python version.

    ``--python-version`` + ``--only-binary=:all:`` let any external python3
    resolve wheels that match Anki's bundled interpreter, so the install
    works even when no python3 with a matching version exists on PATH.
    """
    version = f'{sys.version_info.major}.{sys.version_info.minor}'
    command = [
        executable,
        '-m',
        'pip',
        'install',
        '--quiet',
        '--upgrade',
        '--target',
        str(staging),
        '--only-binary=:all:',
        '--python-version',
        version,
    ]
    for tag in _wheel_platform_tags():
        command += ['--platform', tag]
    command.append(EDGE_TTS_SPEC)
    return command


def _find_pip_python():
    """Return an external python3 executable that has pip, or None."""
    candidates = [shutil.which('python3'), shutil.which('python')]
    candidates += ['/opt/homebrew/bin/python3', '/usr/local/bin/python3']
    for executable in dict.fromkeys(path for path in candidates if path):
        if os.path.realpath(executable) == os.path.realpath(sys.executable):
            continue
        try:
            result = subprocess.run(
                [executable, '-m', 'pip', '--version'],
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return executable
    return None


def run_bootstrap(run=subprocess.run):
    """Install edge-tts into deps_dir() if missing; True when importable."""
    if ensure_deps_on_path():
        return True
    executable = _find_pip_python()
    if executable is None:
        _log('no external python3 with pip found; edge-tts stays unavailable')
        return False
    target = deps_dir()
    staging = target.parent / f'.{target.name}.staging-{os.getpid()}'
    try:
        result = run(
            _pip_install_command(executable, staging),
            capture_output=True,
            text=True,
            timeout=_PIP_TIMEOUT_SEC,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        _log(f'edge-tts auto-install could not run: {exc}')
        return False
    if result.returncode != 0:
        shutil.rmtree(staging, ignore_errors=True)
        _log(f'edge-tts auto-install failed: {result.stderr.strip()[-300:]}')
        return False
    if target.exists():
        # Another process installed it first; discard our copy.
        shutil.rmtree(staging, ignore_errors=True)
    else:
        os.rename(staging, target)  # same filesystem, so this is atomic
    ready = ensure_deps_on_path()
    if ready:
        _log('edge-tts auto-install complete')
    return ready


def bootstrap_edge_tts_background():
    """Start a daemon thread installing edge-tts if missing; return it or None."""
    if ensure_deps_on_path():
        return None
    thread = threading.Thread(target=run_bootstrap, name='awesometts-deps', daemon=True)
    thread.start()
    return thread
