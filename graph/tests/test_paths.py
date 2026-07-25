import os
from pathlib import Path
from unittest.mock import patch

from graph._paths import addons_root


def test_addons_root_with_valid_env(tmp_path):
    with patch.dict(os.environ, {"ANKI_ADDONS_DIR": str(tmp_path)}):
        result = addons_root()
        assert result == tmp_path.resolve()

def test_addons_root_with_invalid_env(tmp_path):
    invalid_path = tmp_path / "does_not_exist"
    with patch.dict(os.environ, {"ANKI_ADDONS_DIR": str(invalid_path)}):
        result = addons_root()
        assert result != invalid_path.resolve()
        assert result.name == "app" # or whatever the repo root is
