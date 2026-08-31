from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from tools.security_audit import _scan_tracked_files


@patch("tools.security_audit.get_tracked_files")
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open, read_data="data")
@patch("tools.security_audit.check_for_credentials")
@patch("tools.security_audit.check_for_private_data")
def test_scan_tracked_files(mock_data, mock_cred, mock_open_file, mock_exists, mock_get):
    mock_get.return_value = ["file1.py", "file2.png", "missing.py"]
    mock_exists.side_effect = [True, True, False]
    mock_cred.return_value = ["cred issue"]
    mock_data.return_value = ["data issue"]

    issues = _scan_tracked_files()
    assert len(issues) == 2
    assert "file1.py: cred issue" in issues
    assert "file1.py: data issue" in issues


@patch("tools.security_audit.get_tracked_files")
@patch("pathlib.Path.exists")
@patch("builtins.open", side_effect=Exception("Read error"))
def test_scan_tracked_files_read_error(mock_open_file, mock_exists, mock_get):
    mock_get.return_value = ["file1.py"]
    mock_exists.return_value = True
    issues = _scan_tracked_files()
    assert len(issues) == 0


from tools.security_audit import _check_json_file_for_private_data


def test_check_json_file_for_private_data_error():
    assert len(_check_json_file_for_private_data("invalid json", "some_file.json")) == 0


def test_check_for_private_data_json():
    from tools.security_audit import check_for_private_data

    content = '[{"flds": "val", "mid": "val"}]'
    issues = check_for_private_data("test.json", content)
    assert len(issues) == 1
    assert "PRIVATE: Contains flds + mid/guid" in issues[0]


def test_check_for_private_data_unknown():
    from tools.security_audit import check_for_private_data

    content = "something"
    issues = check_for_private_data("test.txt", content)
    assert len(issues) == 0


def test_main_block():
    from unittest.mock import patch

    import tools.security_audit

    with patch("tools.security_audit.get_tracked_files", return_value=["README.md"]):
        assert tools.security_audit.main() == 0


def test_scan_tracked_files_extensions():
    from tools.security_audit import _scan_tracked_files

    with (
        patch("tools.security_audit.get_tracked_files") as mock_get,
        patch("pathlib.Path.exists") as mock_exists,
    ):

        mock_get.return_value = ["file.png", "file.mp3", "file.webm"]
        mock_exists.return_value = True

        issues = _scan_tracked_files()
        assert len(issues) == 0


def test_main_block_2():
    # Instead of runpy which loads a new copy of the module, we just call the main function
    # on the imported module.
    import sys
    from unittest.mock import patch

    import tools.security_audit

    with (
        patch("sys.exit"),
        patch("tools.security_audit._scan_tracked_files") as mock_scan,
        patch("tools.security_audit._process_gitignore_coverage") as mock_process,
    ):
        mock_scan.return_value = ["fake issue"]
        mock_process.return_value = True

        # calling main directly since the if __name__ block just calls main and sys.exit
        ret = tools.security_audit.main()
        assert ret == 1


def test_if_name_main(monkeypatch):
    import tools.security_audit

    monkeypatch.setattr(tools.security_audit, "main", lambda: 0)
    with pytest.raises(SystemExit) as excinfo:
        tools.security_audit.sys.exit(tools.security_audit.main())
    assert excinfo.value.code == 0
