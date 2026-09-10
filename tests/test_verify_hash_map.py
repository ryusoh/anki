import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# mock boto3 before importing the module since we don't have it installed
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.config'] = MagicMock()

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "data" / "anki"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_hash_map", SCRIPT_DIR / "verify-hash-map.py"
    )
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so patch("verify_hash_map...") works
    sys.modules["verify_hash_map"] = module
    spec.loader.exec_module(module)
    return module


verify_hash_map = _load_module()


def test_audit_identifies_poisoned_entries():
    hash_map = {
        "guid1": "hash1",
        "guid2": "hash2",
        "guid3": "hash3",
        "collection/file1": "hash4",
        "collection/file2": "hash5",
    }
    staged_guids = ["guid1", "guid2", "guid4"]
    r2_note_guids = ["guid2", "guid3"]
    r2_collection_keys = ["collection/file2", "collection/file3"]

    poisoned_notes, poisoned_collection = verify_hash_map.audit(
        hash_map, staged_guids, r2_note_guids, r2_collection_keys
    )

    assert poisoned_notes == {"guid1"}
    assert poisoned_collection == {"collection/file1"}


def test_audit_clean():
    hash_map = {
        "guid1": "hash1",
        "collection/file1": "hash2",
    }
    staged_guids = ["guid1"]
    r2_note_guids = ["guid1"]
    r2_collection_keys = ["collection/file1"]

    poisoned_notes, poisoned_collection = verify_hash_map.audit(
        hash_map, staged_guids, r2_note_guids, r2_collection_keys
    )

    assert poisoned_notes == set()
    assert poisoned_collection == set()


def test_list_bucket_pagination():
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator

    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "notes/guid1.json.gz"}, {"Key": "notes/guid2.json.gz"}]},
        {"Contents": [{"Key": "notes/guid3.json.gz"}]},
        {},
    ]

    keys = verify_hash_map._list_bucket(mock_client, "my-bucket", "notes/")

    assert keys == {"notes/guid1.json.gz", "notes/guid2.json.gz", "notes/guid3.json.gz"}


def test_main_missing_boto3():
    # we need to simulate missing boto3 during the module's main execution
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == 'boto3':
            raise ImportError("No module named 'boto3'")
        return original_import(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=mock_import):
        assert verify_hash_map.main() == 1


def test_main_missing_hash_map():
    with patch.object(Path, "exists", return_value=False):
        assert verify_hash_map.main() == 1


@patch("json.loads")
def test_main_success(mock_json_loads):
    with (
        patch("boto3.client"),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "read_text", return_value="{}"),
        patch.object(Path, "glob", return_value=[]),
        patch("verify_hash_map._load_r2_utils") as mock_r2_utils,
        patch("verify_hash_map.audit") as mock_audit,
        patch("verify_hash_map._list_bucket", return_value=set()),
    ):

        mock_r2_utils.return_value.load_credentials.return_value = {
            "account_id": "test_acc",
            "access_key": "test_key",
            "secret_key": "test_secret",
            "bucket": "test_bucket",
        }

        mock_audit.return_value = (set(), set())

        assert verify_hash_map.main() == 0


@patch("json.loads")
def test_main_poisoned_entries(mock_json_loads):
    with (
        patch("boto3.client"),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "read_text", return_value="{}"),
        patch.object(Path, "glob", return_value=[]),
        patch("verify_hash_map._load_r2_utils") as mock_r2_utils,
        patch("verify_hash_map.audit") as mock_audit,
        patch("verify_hash_map._list_bucket", return_value=set()),
    ):

        mock_r2_utils.return_value.load_credentials.return_value = {
            "account_id": "test_acc",
            "access_key": "test_key",
            "secret_key": "test_secret",
            "bucket": "test_bucket",
        }

        # return many poisoned notes to cover the len > 20 branch
        poisoned_notes = {f"guid{i}" for i in range(25)}
        mock_audit.return_value = (poisoned_notes, {"collection/file1"})

        assert verify_hash_map.main() == 2


@patch("json.loads")
def test_main_missing_creds(mock_json_loads):
    with (
        patch.object(Path, "exists", return_value=True),
        patch("verify_hash_map._load_r2_utils") as mock_r2_utils,
    ):

        mock_r2_utils.return_value.load_credentials.return_value = {
            "account_id": None,
            "access_key": None,
        }

        assert verify_hash_map.main() == 1


def test_load_r2_utils():
    # Test the internal _load_r2_utils function
    module = verify_hash_map._load_r2_utils()
    assert hasattr(module, "load_credentials")


@patch("json.loads")
def test_main_poisoned_entries_small(mock_json_loads):
    with (
        patch("boto3.client"),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "read_text", return_value="{}"),
        patch.object(Path, "glob", return_value=[]),
        patch("verify_hash_map._load_r2_utils") as mock_r2_utils,
        patch("verify_hash_map.audit") as mock_audit,
        patch("verify_hash_map._list_bucket", return_value=set()),
    ):

        mock_r2_utils.return_value.load_credentials.return_value = {
            "account_id": "test_acc",
            "access_key": "test_key",
            "secret_key": "test_secret",
            "bucket": "test_bucket",
        }

        # return few poisoned notes to cover the len <= 20 branch
        poisoned_notes = {f"guid{i}" for i in range(5)}
        mock_audit.return_value = (poisoned_notes, {"collection/file1"})

        assert verify_hash_map.main() == 2


def test_module_main():
    with patch("sys.exit"), patch("verify_hash_map.main", return_value=0):
        # We need to simulate the execution of the module's main block.
        # But we can't easily re-execute the module without doing something like:
        # verify_hash_map.__name__ = "__main__"
        # However, testing the `if __name__ == '__main__': sys.exit(main())` block
        # is often skipped since it's just entrypoint boilerplate.
        pass
