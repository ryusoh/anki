from __future__ import annotations

import pytest

from auto_itaigi.utils import format_itaigi_result, merge_itaigi_result


def test_format_full_result():
    assert (
        format_itaigi_result(
            "han-tsî/han-tsû",
            ["蕃薯", "甘薯", "地瓜"],
            "itaigi_han-tsi.mp3",
        )
        == "han-tsî/han-tsû<br>華語：蕃薯 甘薯 地瓜<br>[sound:itaigi_han-tsi.mp3]"
    )


def test_format_empty_returns_none():
    assert format_itaigi_result("", [], None) is None


def test_format_no_mandarin_line():
    assert format_itaigi_result("han-tsî", [], None) == "han-tsî"


@pytest.mark.parametrize(
    "current",
    ["", "<br>", "<br/>", "<br />", "<div><br></div>"],
)
def test_merge_replaces_empty_back(current):
    assert merge_itaigi_result(current, "new") == "new"


def test_merge_prepends_to_existing_back():
    assert merge_itaigi_result("existing", "new") == "new<br>existing"
