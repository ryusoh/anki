"""Resolve the Anki add-ons root used by graph scripts.

The repo is symlinked into Anki's add-on folder at
`~/Library/Application Support/Anki2/addons21`. When a script runs from either
the repo checkout or the Anki add-on folder, `__file__` resolves to the real
path. Set `ANKI_ADDONS_DIR` to override this (e.g. in CI or when running from a
different checkout against a specific Anki data directory).
"""

from __future__ import annotations

import os
from pathlib import Path


def addons_root() -> Path:
    """Return the root directory that mirrors the Anki add-ons layout.

    Order of precedence:
    1. `ANKI_ADDONS_DIR` environment variable, if set and the directory exists.
    2. The directory containing this file's parent (`graph/..`), which is the
       repo root / Anki add-ons folder after symlink resolution.
    """
    env = os.environ.get('ANKI_ADDONS_DIR')
    if env:
        path = Path(env).expanduser().resolve()
        if path.exists():
            return path
    return Path(__file__).resolve().parents[1]


ANKI_ADDONS_DIR = addons_root()
