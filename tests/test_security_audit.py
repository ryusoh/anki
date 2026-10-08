import os
import runpy
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import security_audit


def test_check_code_file_for_private_data():
    # Content short
    assert security_audit._check_code_file_for_private_data("ACCOUNT_ID='123'") == []

    # Content long, but no hex
    long_content = "ACCOUNT_ID='123'" + " " * 1000
    assert security_audit._check_code_file_for_private_data(long_content) == []

    # Content long with hex
    long_hex = "ACCOUNT_ID='" + "a" * 32 + "'" + " " * 1000
    assert security_audit._check_code_file_for_private_data(long_hex) == [
        "HARDCODED: ACCOUNT_ID with value"
    ]


def test_check_json_file_for_private_data():
    # Not a list
    assert security_audit._check_json_file_for_private_data('{"flds": "1"}') == []

    # List, but element not dict
    assert security_audit._check_json_file_for_private_data('["string"]') == []

    # List, with flds and mid
    assert security_audit._check_json_file_for_private_data('[{"flds": "1", "mid": 123}]') == [
        "PRIVATE: Contains flds + mid/guid (full note data)"
    ]

    # List, with flds and guid
    assert security_audit._check_json_file_for_private_data('[{"flds": "1", "guid": "abc"}]') == [
        "PRIVATE: Contains flds + mid/guid (full note data)"
    ]

    # List, with tags and flds
    assert security_audit._check_json_file_for_private_data('[{"tags": ["a"], "flds": "1"}]') == [
        "PRIVATE: Contains tags + flds"
    ]

    # Invalid JSON
    assert security_audit._check_json_file_for_private_data('{invalid}') == []


def test_main_execution():
    with patch("sys.exit") as mock_exit:
        with patch("sys.argv", ["security_audit.py", "--help"]):
            runpy.run_module("tools.security_audit", run_name="__main__")
        mock_exit.assert_called()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
