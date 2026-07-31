"""The local-proxy fallback helper is vendored into several places; all
copies must stay in sync.

shared/proxy_fallback.py is the canonical source. Anki add-ons must be
self-contained (AnkiWeb packages ship a single add-on dir), so each
consuming add-on keeps a byte-identical vendored copy at
<addon>/proxy_fallback.py. data/anki/upload-to-r2 is a standalone script
with its own inline helper, so only its port list is pinned here. When
adding a proxy port (e.g. a new VPN client's local listener), edit the
canonical file, re-copy it to every vendored location, and update
upload-to-r2. See docs/limited-network.md, failure mode 3.
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
    '.claude',  # agent worktrees are separate checkouts, not this tree
}

PORTS_RE = re.compile(r'^_?LOCAL_PROXY_PORTS\s*=\s*(\([^)]*\))', re.MULTILINE)

CANONICAL = 'shared/proxy_fallback.py'

VENDORED_COPIES = {
    'auto_wiktionary/proxy_fallback.py',
    'auto_image/proxy_fallback.py',
    'auto_itaigi/proxy_fallback.py',
    'awesome_tts/proxy_fallback.py',
}

# Every file carrying a proxy port list, vendored or standalone. The test
# fails if one is renamed away or a new copy appears without being synced.
PORT_LIST_FILES = VENDORED_COPIES | {
    CANONICAL,
    'data/anki/upload-to-r2',
}


def _iter_source_files():
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT)
        if set(rel.parts) & SKIP_DIRS:
            continue
        if path.suffix == '.py' or rel.as_posix() in PORT_LIST_FILES:
            yield rel


def _find_port_lists():
    found = {}
    for rel in _iter_source_files():
        text = (REPO_ROOT / rel).read_text(encoding='utf-8', errors='ignore')
        match = PORTS_RE.search(text)
        if match:
            found[rel.as_posix()] = ast.literal_eval(match.group(1))
    return found


def test_vendored_copies_are_byte_identical_to_canonical():
    canonical = (REPO_ROOT / CANONICAL).read_bytes()
    for rel in sorted(VENDORED_COPIES):
        assert (
            REPO_ROOT / rel
        ).read_bytes() == canonical, f'{rel} drifted from {CANONICAL} — re-copy the canonical file'


def test_proxy_port_lists_are_in_sync():
    found = _find_port_lists()
    assert set(found) == PORT_LIST_FILES, (
        f'port-list copies changed (found {sorted(found)}); '
        'update PORT_LIST_FILES in this test and sync the lists'
    )
    distinct = {ports for ports in found.values()}
    assert len(distinct) == 1, f'proxy port lists out of sync: {found}'
