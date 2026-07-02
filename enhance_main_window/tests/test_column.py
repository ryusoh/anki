import sys
from unittest.mock import MagicMock, patch

import pytest

# QMenu and QCursor are imported into column from aqt.qt using `from aqt.qt import *`
# We can mock it directly by setting it on the module before running the test, or patching
# `enhance_main_window.column.QMenu` with `create=True`
import enhance_main_window.column as col

col.QMenu = MagicMock()
col.QCursor = MagicMock()


def test_linkHandler():
    MagicMock()
    # It should call lastHandler
    with patch("enhance_main_window.column.lastHandler") as mock_lastHandler:
        mock_lastHandler.return_value = "last"
        assert col._linkHandler(None, "other:url") == "last"

    with (
        patch("enhance_main_window.column.columnHandler") as mock_colH,
        patch("enhance_main_window.column.columnOptions") as mock_colOpt,
    ):
        col._linkHandler(None, "dragColumn:1,2")
        mock_colH.assert_called_with(None, "1,2")

        col._linkHandler(None, "optsColumn:2")
        mock_colOpt.assert_called_with(None, "2")


def test_columnHandler():
    self_mock = MagicMock()
    with (
        patch("enhance_main_window.column.getUserOption") as mock_getOpt,
        patch("enhance_main_window.column.writeConfig") as mock_writeConfig,
    ):

        cols = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        mock_getOpt.return_value = cols

        col.columnHandler(self_mock, "0,2")

        # pop(2) -> {"name": "C"}, insert(0, ...) -> C, A, B
        assert cols == [{"name": "C"}, {"name": "A"}, {"name": "B"}]
        mock_writeConfig.assert_called()
        self_mock.show.assert_called()


def test_columnOptions():
    self_mock = MagicMock()
    with (
        patch("enhance_main_window.column.QMenu", create=True) as mock_QMenu,
        patch("enhance_main_window.column.QCursor", create=True),
    ):
        col.columnOptions(self_mock, "1")
        mock_QMenu.assert_called_with(self_mock.mw)
        mock_QMenu.return_value.addAction.assert_called()
        mock_QMenu.return_value.exec_.assert_called()


def test_deleteColumn():
    self_mock = MagicMock()
    with patch("enhance_main_window.column.askUser") as mock_askUser:
        mock_askUser.return_value = False
        col.deleteColumn(self_mock, "1")
        # Should return early
        self_mock.show.assert_not_called()

    with (
        patch("enhance_main_window.column.askUser") as mock_askUser,
        patch("enhance_main_window.column.getUserOption") as mock_getOpt,
        patch("enhance_main_window.column.writeConfig") as mock_writeConfig,
    ):
        mock_askUser.return_value = True
        cols = [{"name": "A"}, {"name": "B"}]
        mock_getOpt.return_value = cols

        col.deleteColumn(self_mock, "1")

        assert cols[1].get("present") is False
        mock_writeConfig.assert_called()
        self_mock.show.assert_called()
