import gzip
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Change directory and add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Need to properly mock before importing if the script has side effects, but it only has an __main__ block
import data.anki.security_check as security_check


def test_get_private_field_patterns():
    patterns = security_check.get_private_field_patterns()
    assert '"flds"' in patterns
    assert '"tags"' in patterns

def test_check_json_data():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)

        # Test normal file
        file_path = temp_path / "data.json"
        with open(file_path, "w") as f:
            json.dump([{"flds": "secret", "mid": 1}], f)

        violations = security_check._check_json_data("data.json", file_path)
        assert len(violations) > 0
        assert violations[0]['type'] == 'private_notes'

        # Test regression
        file_path2 = temp_path / "notes.json.gz"
        with gzip.open(file_path2, "wt") as f:
            json.dump([{"flds": "secret"}], f)

        violations2 = security_check._check_json_data("notes.json.gz", file_path2)
        assert len(violations2) > 0
        assert violations2[0]['type'] == 'data_leak_regression'

        # Invalid json
        invalid_path = temp_path / "invalid.json"
        with open(invalid_path, "w") as f:
            f.write("not json")
        violations_inv = security_check._check_json_data("invalid.json", invalid_path)
        assert len(violations_inv) == 0

def test_check_file_for_private_data():
    assert len(security_check.check_file_for_private_data("package.json", "...", None)) == 0
    assert len(security_check.check_file_for_private_data("script.py", "...", None)) == 0

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        file_path = temp_path / "data.json"
        with open(file_path, "w") as f:
            json.dump([{"flds": "secret", "mid": 1}], f)

        violations = security_check.check_file_for_private_data("data.json", "...", file_path)
        assert len(violations) > 0

def test_check_r2_staging_directory():
    with tempfile.TemporaryDirectory() as tempdir:
        project_root = Path(tempdir)

        # Mock the Path object in security_check to point to our temp root
        with patch('data.anki.security_check.Path') as MockPath:
            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_parent3 = project_root

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.parent = mock_parent3

            MockPath.return_value = mock_file_path

            # Missing gitignore
            assert len(security_check.check_r2_staging_directory()) > 0

            # Create gitignore without r2 staging
            gitignore = project_root / ".gitignore"
            with open(gitignore, "w") as f:
                f.write("node_modules\n")

            violations = security_check.check_r2_staging_directory()
            assert len(violations) > 0
            assert violations[0]['type'] == 'r2_not_ignored'

            # Create proper gitignore
            with open(gitignore, "w") as f:
                f.write("node_modules\ndata/cloudflare/\ngraph/*.json\n")

            assert len(security_check.check_r2_staging_directory()) == 0

def test_scan_tracked_file():
    with tempfile.TemporaryDirectory() as tempdir:
        project_root = Path(tempdir)
        file_path = project_root / "test.json"
        gz_path = project_root / "test.json.gz"

        # does not exist
        assert len(security_check._scan_tracked_file("notexist.json", project_root)) == 0

        # binary
        assert len(security_check._scan_tracked_file("image.png", project_root)) == 0

        # valid json
        with open(file_path, "w") as f:
            json.dump([{"flds": "secret", "mid": 1}], f)

        violations = security_check._scan_tracked_file("test.json", project_root)
        assert len(violations) > 0

        # valid json gz
        with gzip.open(gz_path, "wt") as f:
            json.dump([{"flds": "secret", "mid": 1}], f)

        violations_gz = security_check._scan_tracked_file("test.json.gz", project_root)
        assert len(violations_gz) > 0

def test_main():
    with patch("data.anki.security_check.get_tracked_files", return_value=["test.json"]):
        with patch("data.anki.security_check._scan_tracked_file", return_value=[{"file": "test.json", "message": "msg"}]):
            with patch("data.anki.security_check.check_r2_staging_directory", return_value=[]):
                assert security_check.main() == 1

    with patch("data.anki.security_check.get_tracked_files", return_value=["test.json"]):
        with patch("data.anki.security_check._scan_tracked_file", return_value=[]):
            with patch("data.anki.security_check.check_r2_staging_directory", return_value=[]):
                assert security_check.main() == 0

    with patch("data.anki.security_check.get_tracked_files", return_value=[]):
        assert security_check.main() == 0

def test_utils():
    # Capture print output or just ensure they run
    with patch("sys.stderr", new_callable=MagicMock):
        security_check.error("test err")
        security_check.warning("test warn")
        security_check.success("test success")

@patch('subprocess.run')
def test_get_gitignored_files(mock_run):
    mock_run.return_value = MagicMock(stdout="file1.json\nfile2.txt\n")
    files = security_check.get_gitignored_files()
    assert "file1.json" in files
    assert "file2.txt" in files

@patch('subprocess.run')
def test_get_tracked_files(mock_run):
    mock_run.return_value = MagicMock(stdout="file3.json\nfile4.txt\n")
    files = security_check.get_tracked_files()
    assert "file3.json" in files
    assert "file4.txt" in files
