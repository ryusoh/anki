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
``sys.path``. When edge-tts is missing at add-on load — or its installed
version no longer satisfies ``EDGE_TTS_SPEC`` (e.g. after the spec floor is
bumped for an upstream fix) — a daemon thread reinstalls it silently; the
next single-click can then use it without restarting Anki.
"""

import os
import platform
import re
import shutil
import subprocess
import sys
import threading
from importlib import metadata as importlib_metadata
from itertools import zip_longest
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
    except Exception:
        # Not just ImportError: a deps dir built for a different Python
        # version fails later with TypeError and friends, and an add-on load
        # must never crash over an optional dependency.
        return False
    return True


_SPEC_CLAUSE_RE = re.compile(r'(>=|<=|==|>|<)\s*([0-9][0-9.]*)')


def _version_tuple(text):
    """'7.2.8' -> (7, 2, 8); leading junk or a 'v' prefix is tolerated."""
    match = re.search(r'[0-9]+(?:\.[0-9]+)*', text)
    return tuple(int(part) for part in match.group(0).split('.')) if match else ()


def _satisfies_spec(version, spec):
    """True when version '7.2.8' satisfies spec 'edge-tts>=7.0,<8'.

    Only the relational operators this project's specs use; components are
    zero-padded so 7.0 equals 7.0.0.
    """
    found = _version_tuple(version)
    for op, wanted_text in _SPEC_CLAUSE_RE.findall(spec):
        wanted = _version_tuple(wanted_text)
        cmp = 0
        for have, want in zip_longest(found, wanted, fillvalue=0):
            if have != want:
                cmp = 1 if have > want else -1
                break
        if {'>': cmp > 0, '>=': cmp >= 0, '==': cmp == 0, '<': cmp < 0, '<=': cmp <= 0}[op]:
            continue
        return False
    return True


def _installed_version():
    """Installed edge-tts version string, or None when undiscoverable."""
    try:
        return importlib_metadata.version('edge-tts')
    except Exception:
        pass
    try:
        import edge_tts

        return getattr(edge_tts, '__version__', None)
    except Exception:
        return None


def _installed_satisfies_spec():
    """True when the installed edge-tts satisfies EDGE_TTS_SPEC. An
    undiscoverable version counts as satisfying: never churn a working
    install over a metadata quirk."""
    version = _installed_version()
    return version is None or _satisfies_spec(version, EDGE_TTS_SPEC)


def ensure_deps_on_path():
    """Put the deps directory on sys.path if needed; True if edge_tts imports."""
    if _edge_tts_importable():
        return True
    target = deps_dir()
    if not (target / 'edge_tts').is_dir():
        return False
    if str(target) in sys.path:
        return _edge_tts_importable()
    # Appended, not prepended, so Anki's own bundled packages (e.g. certifi)
    # keep precedence over the runtime-installed copies.
    sys.path.append(str(target))
    if _edge_tts_importable():
        return True
    # Broken or wrong-version install — keep it off the path.
    sys.path.remove(str(target))
    return False


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


def _install_specs():
    """Package specs to install for Anki's Python version.

    pip evaluates dependency environment markers (e.g. ``python_version <
    "3.11"``) against the *installing* interpreter, not the ``--python-
    version`` target, so conditional deps must be requested explicitly.
    """
    specs = [EDGE_TTS_SPEC]
    if sys.version_info < (3, 11):
        # aiohttp imports async_timeout on Python < 3.11; pip's cross-install
        # silently drops it (see docstring above).
        specs.append('async-timeout>=4,<6')
    return specs


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
    command += _install_specs()
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
    """Install edge-tts into deps_dir() if missing or outdated; True when importable.

    "Outdated" means the installed version no longer satisfies EDGE_TTS_SPEC.
    A failed reinstall leaves the previous install untouched and still reports
    True — old but working beats none.
    """
    if ensure_deps_on_path() and _installed_satisfies_spec():
        return True
    executable = _find_pip_python()
    if executable is None:
        _log('no external python3 with pip found; edge-tts stays unavailable')
        return ensure_deps_on_path()
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
        return ensure_deps_on_path()
    if result.returncode != 0:
        shutil.rmtree(staging, ignore_errors=True)
        _log(f'edge-tts auto-install failed: {result.stderr.strip()[-300:]}')
        return ensure_deps_on_path()
    if target.exists():
        # We only get here when the existing install is broken or outdated
        # (a working, in-spec one short-circuits above), so replace it with
        # the fresh staging copy.
        shutil.rmtree(target, ignore_errors=True)
    os.rename(staging, target)  # same filesystem, so this is atomic
    ready = ensure_deps_on_path()
    if ready:
        _log('edge-tts auto-install complete')
    return ready


def bootstrap_edge_tts_background():
    """Start a daemon thread installing edge-tts if missing or outdated;
    return it or None.

    Never raises: an optional dependency must not be able to break add-on
    loading.
    """
    try:
        if ensure_deps_on_path() and _installed_satisfies_spec():
            return None
        thread = threading.Thread(target=run_bootstrap, name='awesometts-deps', daemon=True)
        thread.start()
        return thread
    except Exception as exc:
        _log(f'bootstrap skipped: {exc}')
        return None
