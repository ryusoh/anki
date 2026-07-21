from enhance_main_window.printing import conditionString, nowLater


def test_conditionString_falsey():
    assert conditionString(False) == ""
    assert conditionString(0) == ""
    assert conditionString(None) == ""


def test_conditionString_truthy_no_string():
    assert conditionString(True) == "True"
    assert conditionString(5) == "5"


def test_conditionString_truthy_with_string():
    assert conditionString(True, "foo") == "foo"
    assert conditionString(True, 42) == "42"


def test_conditionString_truthy_parenthesis():
    assert conditionString(True, parenthesis=True) == "(+True)"
    assert conditionString(True, "foo", parenthesis=True) == "(+foo)"


def test_nowLater():
    assert nowLater(False, False) == ""
    assert nowLater(True, False) == "True"
    assert nowLater(False, True) == "(+True)"
    assert nowLater(True, True) == "True(+True)"
    assert nowLater("now", "later") == "now(+later)"
