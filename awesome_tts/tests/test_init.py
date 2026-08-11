import sys
from unittest.mock import patch

import pytest

import awesome_tts


def test_init_main_execution():
    with patch("sys.stderr.write") as mock_write:
        with patch("builtins.exit", side_effect=SystemExit(1)) as mock_exit:
            import runpy

            try:
                runpy.run_path("awesome_tts/__init__.py", run_name="__main__")
            except SystemExit as excinfo:
                assert excinfo.code == 1

            mock_write.assert_called_once()
            mock_exit.assert_called_once_with(1)


def test_init_normal_anki_operation():
    with open("awesome_tts/__init__.py") as f:
        code = f.read()

    namespace = {"__name__": "awesome_tts", "__package__": "awesome_tts"}

    # We patch hasattr to return False for _pytest_mode
    original_hasattr = hasattr

    def mock_hasattr(obj, name):
        if obj is sys and name == "_pytest_mode":
            return False
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", side_effect=mock_hasattr):
        with patch("sys.modules", sys.modules.copy()):
            sys.modules["awesome_tts.awesometts"] = type(
                "mock_awesometts",
                (),
                {
                    "browser_menus": lambda: None,
                    "cache_control": lambda: None,
                    "cards_button": lambda: None,
                    "config_menu": lambda: None,
                    "editor_button": lambda: None,
                    "reviewer_hooks": lambda: None,
                    "temp_files": lambda: None,
                    "register_tts_tag": lambda: None,
                    "display_homescreen": lambda: None,
                },
            )
            exec(compile(code, "awesome_tts/__init__.py", "exec"), namespace)


def test_init_test_mode_operation():
    with open("awesome_tts/__init__.py") as f:
        code = f.read()

    namespace = {"__name__": "awesome_tts", "__package__": "awesome_tts"}

    # We patch hasattr to return True for _pytest_mode
    original_hasattr = hasattr

    def mock_hasattr(obj, name):
        if obj is sys and name == "_pytest_mode":
            return True
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", side_effect=mock_hasattr):
        with patch("sys.modules", sys.modules.copy()):
            sys.modules["awesometts"] = type(
                "mock_awesometts",
                (),
                {
                    "browser_menus": lambda: None,
                    "cache_control": lambda: None,
                    "cards_button": lambda: None,
                    "config_menu": lambda: None,
                    "editor_button": lambda: None,
                    "reviewer_hooks": lambda: None,
                    "temp_files": lambda: None,
                    "register_tts_tag": lambda: None,
                    "display_homescreen": lambda: None,
                },
            )
            exec(compile(code, "awesome_tts/__init__.py", "exec"), namespace)
