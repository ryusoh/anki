import hashlib
import importlib.util
import json
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPT_DIR = Path(__file__).parent
SCRIPT = SCRIPT_DIR.parent / 'upload_public.py'

_upload_public_loader = SourceFileLoader('upload_public_mod', str(SCRIPT))
_upload_public_spec = importlib.util.spec_from_loader('upload_public_mod', _upload_public_loader)
upload_public = importlib.util.module_from_spec(_upload_public_spec)
_upload_public_loader.exec_module(upload_public)


@pytest.fixture
def public_files(tmp_path):
    """Create two temporary public graph files and return their paths + hashes."""
    base = tmp_path / 'base'
    graph_dir = base / 'graph'
    graph_dir.mkdir(parents=True)

    graph_data = {'nodes': [{'id': 'n1'}], 'links': []}
    history_data = {'dates': ['2021-01-01'], 'history': {}}

    graph_file = graph_dir / 'graph_data_public.json'
    history_file = graph_dir / 'history_data_public.json'

    graph_file.write_text(json.dumps(graph_data, separators=(',', ':')))
    history_file.write_text(json.dumps(history_data, separators=(',', ':')))

    graph_hash = hashlib.sha256(graph_file.read_bytes()).hexdigest()
    history_hash = hashlib.sha256(history_file.read_bytes()).hexdigest()

    return {
        'base': base,
        'graph_file': graph_file,
        'history_file': history_file,
        'graph_hash': graph_hash,
        'history_hash': history_hash,
    }


def fake_upload_factory(failing_key=None):
    def fake_upload(bucket, key, data, creds, verbose=False, quiet=False, **kwargs):
        return key != failing_key, len(data)

    return fake_upload


@pytest.fixture
def mock_creds():
    return {'account_id': 'acct', 'access_key': 'ak', 'secret_key': 'sk', 'bucket': 'b'}


def test_skips_unchanged_file(public_files, mock_creds, tmp_path, monkeypatch, capsys):
    hash_map_file = tmp_path / 'hash_map.json'
    hash_map_file.write_text(
        json.dumps(
            {
                'graph/graph_data_public.json': public_files['graph_hash'],
            }
        )
    )

    monkeypatch.setattr(upload_public, 'BASE', public_files['base'])
    monkeypatch.setattr(upload_public, 'HASH_MAP_FILE', hash_map_file)
    monkeypatch.setattr(upload_public.r2_utils, 'load_credentials', lambda: dict(mock_creds))
    monkeypatch.setattr(upload_public.r2_utils, 'upload_to_r2', fake_upload_factory())

    upload_public.upload_public_data()

    captured = capsys.readouterr()
    assert 'graph/graph_data_public.json unchanged' in captured.out
    assert 'graph/history_data_public.json' in captured.out  # changed/new -> uploaded


def test_uploads_changed_file_and_updates_hash_map(
    public_files, mock_creds, tmp_path, monkeypatch, capsys
):
    hash_map_file = tmp_path / 'hash_map.json'
    hash_map_file.write_text('{}')

    monkeypatch.setattr(upload_public, 'BASE', public_files['base'])
    monkeypatch.setattr(upload_public, 'HASH_MAP_FILE', hash_map_file)
    monkeypatch.setattr(upload_public.r2_utils, 'load_credentials', lambda: dict(mock_creds))
    monkeypatch.setattr(upload_public.r2_utils, 'upload_to_r2', fake_upload_factory())

    upload_public.upload_public_data()

    captured = capsys.readouterr()
    assert 'graph/graph_data_public.json' in captured.out
    assert 'graph/history_data_public.json' in captured.out

    hash_map = json.loads(hash_map_file.read_text())
    assert hash_map['graph/graph_data_public.json'] == public_files['graph_hash']
    assert hash_map['graph/history_data_public.json'] == public_files['history_hash']


def test_mixed_unchanged_and_changed(public_files, mock_creds, tmp_path, monkeypatch):
    hash_map_file = tmp_path / 'hash_map.json'
    hash_map_file.write_text(
        json.dumps(
            {
                'graph/graph_data_public.json': public_files['graph_hash'],
            }
        )
    )

    # Modify history file so only it changes
    public_files['history_file'].write_text(
        json.dumps({'dates': ['2021-01-02'], 'history': {}}, separators=(',', ':'))
    )

    attempted = []

    def recording_upload(bucket, key, data, creds, verbose=False, quiet=False, **kwargs):
        attempted.append(key)
        return True, len(data)

    monkeypatch.setattr(upload_public, 'BASE', public_files['base'])
    monkeypatch.setattr(upload_public, 'HASH_MAP_FILE', hash_map_file)
    monkeypatch.setattr(upload_public.r2_utils, 'load_credentials', lambda: dict(mock_creds))
    monkeypatch.setattr(upload_public.r2_utils, 'upload_to_r2', recording_upload)

    upload_public.upload_public_data()

    assert attempted == ['graph/history_data_public.json']

    hash_map = json.loads(hash_map_file.read_text())
    assert hash_map['graph/graph_data_public.json'] == public_files['graph_hash']
    new_history_hash = hashlib.sha256(public_files['history_file'].read_bytes()).hexdigest()
    assert hash_map['graph/history_data_public.json'] == new_history_hash


def test_failed_upload_not_recorded(public_files, mock_creds, tmp_path, monkeypatch):
    hash_map_file = tmp_path / 'hash_map.json'
    hash_map_file.write_text('{}')

    monkeypatch.setattr(upload_public, 'BASE', public_files['base'])
    monkeypatch.setattr(upload_public, 'HASH_MAP_FILE', hash_map_file)
    monkeypatch.setattr(upload_public.r2_utils, 'load_credentials', lambda: dict(mock_creds))
    monkeypatch.setattr(
        upload_public.r2_utils,
        'upload_to_r2',
        fake_upload_factory(failing_key='graph/graph_data_public.json'),
    )

    upload_public.upload_public_data()

    hash_map = json.loads(hash_map_file.read_text())
    assert 'graph/graph_data_public.json' not in hash_map
    assert hash_map['graph/history_data_public.json'] == public_files['history_hash']


def test_missing_file_skipped(mock_creds, tmp_path, monkeypatch, capsys):
    base = tmp_path / 'base'
    base.mkdir()
    hash_map_file = tmp_path / 'hash_map.json'
    hash_map_file.write_text('{}')

    monkeypatch.setattr(upload_public, 'BASE', base)
    monkeypatch.setattr(upload_public, 'HASH_MAP_FILE', hash_map_file)
    monkeypatch.setattr(upload_public.r2_utils, 'load_credentials', lambda: dict(mock_creds))
    monkeypatch.setattr(upload_public.r2_utils, 'upload_to_r2', fake_upload_factory())

    upload_public.upload_public_data()

    captured = capsys.readouterr()
    assert 'graph/graph_data_public.json (not found)' in captured.out
    assert 'graph/history_data_public.json (not found)' in captured.out


def test_missing_credentials_exit(tmp_path, monkeypatch):
    hash_map_file = tmp_path / 'hash_map.json'
    hash_map_file.write_text('{}')
    monkeypatch.setattr(upload_public, 'HASH_MAP_FILE', hash_map_file)
    monkeypatch.setattr(
        upload_public.r2_utils,
        'load_credentials',
        lambda: {'account_id': '', 'access_key': '', 'secret_key': '', 'bucket': 'b'},
    )

    with pytest.raises(SystemExit) as exc_info:
        upload_public.upload_public_data()
    assert exc_info.value.code == 1


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
