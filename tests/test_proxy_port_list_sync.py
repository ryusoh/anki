"""All copies of the local-proxy fallback port list must stay identical.

The fallback helper is duplicated on purpose: each add-on directory must be
self-contained for Anki to load it, and data/anki/upload-to-r2 is a
standalone pipeline script. When adding a proxy port (e.g. a new VPN
client's local listener), update every copy — this test fails on drift and
on a silently renamed/missing copy. See docs/limited-network.md, failure
mode 3.
"""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    '.git',
    '.venv',
    'node_modules',
    '__pycache__',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
}

PORTS_RE = re.compile(r'^_?LOCAL_PROXY_PORTS\s*=\s*(\([^)]*\))', re.MULTILINE)

# The copies known to exist today; the test fails if one is renamed away or
# a new copy appears without being synced.
KNOWN_COPIES = {
    'auto_wiktionary/utils.py',
    'auto_image/utils.py',
    'data/anki/upload-to-r2',
}


def _iter_source_files():
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT)
        if set(rel.parts) & SKIP_DIRS:
            continue
        if path.suffix == '.py' or str(rel) in KNOWN_COPIES:
            yield rel


def _find_port_lists():
    found = {}
    for rel in _iter_source_files():
        text = (REPO_ROOT / rel).read_text(encoding='utf-8', errors='ignore')
        match = PORTS_RE.search(text)
        if match:
            found[rel.as_posix()] = ast.literal_eval(match.group(1))
    return found


def test_proxy_port_lists_are_in_sync():
    found = _find_port_lists()
    assert set(found) == KNOWN_COPIES, (
        f'port-list copies changed (found {sorted(found)}); '
        'update KNOWN_COPIES in this test and sync the lists'
    )
    distinct = {ports for ports in found.values()}
    assert len(distinct) == 1, f'proxy port lists out of sync: {found}'
