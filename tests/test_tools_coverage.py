import pytest
from tools.security_audit import _should_skip_file_for_private_data, _check_code_file_for_private_data, _check_json_file_for_private_data, check_for_private_data

def test_should_skip_file_for_private_data():
    assert _should_skip_file_for_private_data("some.md") is True
    assert _should_skip_file_for_private_data("docs/some.py") is True
    assert _should_skip_file_for_private_data("vendor/some.py") is True
    assert _should_skip_file_for_private_data("node_modules/some.py") is True
    assert _should_skip_file_for_private_data("some_notes.json.gz") is True
    assert _should_skip_file_for_private_data("reviews/some.py") is True
    assert _should_skip_file_for_private_data("some.py") is False

def test_check_code_file_for_private_data():
    content = "a" * 1000 + "ACCOUNT_ID='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'"
    issues = _check_code_file_for_private_data(content)
    assert len(issues) == 1
    assert "HARDCODED: ACCOUNT_ID with value" in issues[0]

def test_check_json_file_for_private_data():
    content1 = '[{"flds": "val", "mid": "val"}]'
    issues1 = _check_json_file_for_private_data(content1)
    assert len(issues1) == 1
    assert "PRIVATE: Contains flds + mid/guid" in issues1[0]

    content2 = '[{"tags": "val", "flds": "val"}]'
    issues2 = _check_json_file_for_private_data(content2)
    assert len(issues2) == 1
    assert "PRIVATE: Contains tags + flds" in issues2[0]

def test_check_for_private_data():
    content = "a" * 1000 + "ACCOUNT_ID='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'"
    issues = check_for_private_data("test.py", content)
    assert len(issues) == 1

    issues2 = check_for_private_data("test.md", content)
    assert len(issues2) == 0


from tools.security_audit import error, warning, success, get_tracked_files, check_for_credentials, check_gitignore_coverage

def test_error_warning_success(capsys):
    assert error("msg") is False
    assert warning("msg") is True
    assert success("msg") is True
    captured = capsys.readouterr()
    assert "msg" in captured.out

def test_check_for_credentials():
    assert len(check_for_credentials("vendor/test.py", "secret")) == 0
    assert len(check_for_credentials("test.md", "secret")) == 0
    assert len(check_for_credentials("test.gz", "secret")) == 0
    assert len(check_for_credentials("test.py", "SECRET='123456789012345678901234567890'")) == 1
    assert len(check_for_credentials("test.py", "-----BEGIN RSA PRIVATE KEY-----")) == 1
    assert len(check_for_credentials("test.js", "SECRET='123456789012345678901234567890'")) == 1
    assert len(check_for_credentials("test.txt", "SECRET='123456789012345678901234567890'")) == 0

from unittest.mock import patch

@patch("subprocess.run")
def test_get_tracked_files(mock_run):
    mock_run.return_value.stdout = "file1.py\nfile2.js\n"
    assert get_tracked_files() == ["file1.py", "file2.js"]

@patch("subprocess.run")
def test_check_gitignore_coverage(mock_run):
    mock_run.return_value.returncode = 1
    issues = check_gitignore_coverage()
    assert len(issues) == 2
    assert "data/cloudflare/test_dummy.json is NOT gitignored!" in issues[0]
    assert "graph/graph_data.json is NOT gitignored!" in issues[1]

    mock_run.return_value.returncode = 0
    issues = check_gitignore_coverage()
    assert len(issues) == 0

from tools.security_audit import _process_gitignore_coverage, _report_results, main

@patch("tools.security_audit.check_gitignore_coverage")
def test_process_gitignore_coverage(mock_check):
    mock_check.return_value = ["issue1"]
    assert _process_gitignore_coverage(True) is False
    mock_check.return_value = []
    assert _process_gitignore_coverage(True) is True

def test_report_results():
    assert _report_results(["issue1"], True) is False
    assert _report_results([], True) is True

@patch("tools.security_audit._process_gitignore_coverage")
@patch("tools.security_audit._scan_tracked_files")
@patch("tools.security_audit._report_results")
def test_main(mock_report, mock_scan, mock_process):
    mock_process.return_value = True
    mock_scan.return_value = []
    mock_report.return_value = True
    assert main() == 0

    mock_report.return_value = False
    assert main() == 1
