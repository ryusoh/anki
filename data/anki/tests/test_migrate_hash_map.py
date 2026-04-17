import sys
from pathlib import Path
import tempfile
import gzip
import json
import os
from unittest.mock import patch, MagicMock

# Add the directory to sys.path so we can import the script properly
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

import importlib.util
spec = importlib.util.spec_from_file_location("migrate_hash_map", str(script_dir / "migrate-hash-map.py"))
migrate_hash_map = importlib.util.module_from_spec(spec)

import pytest

@pytest.fixture(autouse=True)
def setup_module_mocks(monkeypatch):
    """Safely setup modules for each test to avoid test pollution"""
    import types
    graph_mock = types.ModuleType('graph')
    hash_map_mock = types.ModuleType('hash_map')
    hash_map_mock.compute_note_hash = MagicMock(return_value="mock_hash")
    hash_map_mock.load_hash_map = MagicMock(return_value={})
    hash_map_mock.save_hash_map = MagicMock()

    monkeypatch.setitem(sys.modules, 'graph', graph_mock)
    monkeypatch.setitem(sys.modules, 'hash_map', hash_map_mock)

    # Reload the module under test with the mocks in place
    spec.loader.exec_module(migrate_hash_map)
    monkeypatch.setitem(sys.modules, 'migrate_hash_map', migrate_hash_map)
    yield hash_map_mock

def test_compute_file_hash():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_path = f.name

    try:
        expected = "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
        assert migrate_hash_map.compute_file_hash(temp_path) == expected
    finally:
        os.unlink(temp_path)

def test_get_staging_dir():
    with patch('pathlib.Path.cwd') as mock_cwd:
        mock_cwd.return_value = Path('/mock/project')
        with patch('pathlib.Path.exists', return_value=True):
            assert migrate_hash_map.get_staging_dir() == Path('/mock/project/data/cloudflare')

def test_get_staging_dir_fallback():
    with patch('pathlib.Path.cwd') as mock_cwd:
        mock_cwd.return_value = Path('/some/other/path')
        with patch('pathlib.Path.exists', return_value=False):
            with patch('pathlib.Path.mkdir'):
                expected_path = Path(migrate_hash_map.__file__).parent.parent / "cloudflare"
                assert migrate_hash_map.get_staging_dir() == expected_path

def test_main_with_hash_map_exists_and_abort(setup_module_mocks):
    with tempfile.TemporaryDirectory() as tempdir:
        staging_dir = Path(tempdir)
        hash_map_file = staging_dir / "hash_map.json"
        hash_map_file.touch()

        setup_module_mocks.save_hash_map.reset_mock()
        with patch('migrate_hash_map.get_staging_dir', return_value=staging_dir):
            with patch('builtins.input', return_value='n'):
                migrate_hash_map.main()
                setup_module_mocks.save_hash_map.assert_not_called()

def test_main_with_corrupt_files_and_abort(setup_module_mocks):
    with tempfile.TemporaryDirectory() as tempdir:
        staging_dir = Path(tempdir)
        notes_dir = staging_dir / "notes"
        notes_dir.mkdir(parents=True)

        with gzip.open(notes_dir / "corrupt.json.gz", "wt") as f:
            f.write("not valid json")

        setup_module_mocks.save_hash_map.reset_mock()
        with patch('migrate_hash_map.get_staging_dir', return_value=staging_dir):
            with patch('builtins.input', return_value='n'):
                with pytest.raises(SystemExit):
                    migrate_hash_map.main()
                setup_module_mocks.save_hash_map.assert_not_called()

def test_main_success_path(setup_module_mocks):
    with tempfile.TemporaryDirectory() as tempdir:
        staging_dir = Path(tempdir)

        # Add collection files
        coll_dir = staging_dir / "collection"
        coll_dir.mkdir(parents=True)
        with open(coll_dir / "notes.json.gz", "wb") as f:
            f.write(b"content")

        # Add a note
        notes_dir = staging_dir / "notes"
        notes_dir.mkdir(parents=True)
        with gzip.open(notes_dir / "123.json.gz", "wt") as f:
            f.write(json.dumps({"guid": "123"}))

        with gzip.open(notes_dir / "456.json.gz", "wt") as f:
            f.write(json.dumps({}))

        setup_module_mocks.save_hash_map.reset_mock()
        with patch('migrate_hash_map.get_staging_dir', return_value=staging_dir):
            with patch('migrate_hash_map.compute_file_hash', return_value="hash_val"):
                with patch('builtins.input', return_value='y'):
                    migrate_hash_map.main()
                    setup_module_mocks.save_hash_map.assert_called()

def test_migrate_hash_map_continue_anyway(setup_module_mocks):
    with tempfile.TemporaryDirectory() as tempdir:
        staging_dir = Path(tempdir)
        notes_dir = staging_dir / "notes"
        notes_dir.mkdir(parents=True)

        # Add a corrupt note
        with gzip.open(notes_dir / "corrupt.json.gz", "wt") as f:
            f.write("not valid json")

        setup_module_mocks.save_hash_map.reset_mock()
        with patch('migrate_hash_map.get_staging_dir', return_value=staging_dir):
            with patch('builtins.input', return_value='y'):
                migrate_hash_map.main()
                setup_module_mocks.save_hash_map.assert_called()

def test_migrate_hash_map_fallback_filename_hash(setup_module_mocks):
    with tempfile.TemporaryDirectory() as tempdir:
        staging_dir = Path(tempdir)
        notes_dir = staging_dir / "notes"
        notes_dir.mkdir(parents=True)

        # Add a note without a guid
        with gzip.open(notes_dir / "noguid.json.gz", "wt") as f:
            json.dump({"flds": "abc"}, f)

        setup_module_mocks.save_hash_map.reset_mock()
        with patch('migrate_hash_map.get_staging_dir', return_value=staging_dir):
            with patch('migrate_hash_map.compute_file_hash', return_value="file_hash_val"):
                with patch('builtins.input', return_value='y'):
                    migrate_hash_map.main()

                    # Should have been saved with filename hash
                    args, kwargs = setup_module_mocks.save_hash_map.call_args
                    hash_map = args[0]
                    assert "noguid.json.gz" in hash_map
                    assert hash_map["noguid.json.gz"] == "file_hash_val"

def test_missing_files_hash_map(setup_module_mocks):
    with tempfile.TemporaryDirectory() as tempdir:
        staging_dir = Path(tempdir)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = staging_dir
            with patch('migrate_hash_map.get_staging_dir', return_value=staging_dir):
                setup_module_mocks.save_hash_map.reset_mock()
                with patch('builtins.input', return_value='y'):
                    migrate_hash_map.main()
                    setup_module_mocks.save_hash_map.assert_called()
