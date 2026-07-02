import pytest

import enhance_main_window.htmlAndCss as htmlAndCss


def test_column_header():
    res = htmlAndCss.column_header("Title", "2")
    assert "Title" in res
    assert 'colpos = "2"' in res
    assert 'optsColumn:2' in res


def test_start_line():
    res = htmlAndCss.start_line("my-class", "123")
    assert "class = 'my-class'" in res
    assert "id = '123'" in res


def test_collapse_children_html():
    res = htmlAndCss.collapse_children_html("123", "name", "prefix")
    assert "collapse:123" in res
    assert "id = \"name\"" in res
    assert "prefix" in res


def test_deck_name():
    res = htmlAndCss.deck_name(1, "collapse", "extra", "123", "color:red;", "DeckName")
    assert "&nbsp;" * 6 in res
    assert "collapse" in res
    assert "deckextra" in res
    assert "open:123" in res
    assert "color:red;" in res
    assert "DeckName" in res


def test_number_cell_no_description():
    res = htmlAndCss.number_cell("red", "10", None)
    assert "number_cell" in res
    assert "red" in res
    assert "10" in res
    assert "tooltiptext" not in res

    res2 = htmlAndCss.number_cell("red", "10", False)
    assert "tooltiptext" not in res2


def test_number_cell_with_description():
    res = htmlAndCss.number_cell("blue", "20", "A tooltip")
    assert "tooltip number_cell" in res
    assert "blue" in res
    assert "20" in res
    assert "tooltiptext" in res
    assert "A tooltip" in res


def test_gear():
    res = htmlAndCss.gear("456")
    assert "opts:456" in res
    assert "gears.svg" in res


def test_deck_option_name():
    res = htmlAndCss.deck_option_name("OptName")
    assert "OptName" in res


def test_bar():
    res = htmlAndCss.bar("BarName", 50, 20, "green", "Overlay")
    assert "width:50%" in res
    assert "left :20%" in res
    assert "background-color:green" in res
    assert "Overlay" in res


def test_progress():
    res = htmlAndCss.progress("Content")
    assert "class=\"progress\"" in res
    assert "Content" in res
