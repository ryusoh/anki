from auto_wiktionary.utils import merge_definition


def test_merge_definition_empty():
    assert merge_definition("", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"
    assert merge_definition("   ", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"
    assert merge_definition("<br>", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"
    assert merge_definition("<br/>", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"
    assert merge_definition("<br />", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"
    assert merge_definition("<div><br></div>", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"


def test_merge_definition_existing():
    assert (
        merge_definition("existing content", "<ul><li>def</li></ul>")
        == "<ul><li>def</li></ul><br>existing content"
    )
    assert (
        merge_definition("old line 1<br>old line 2", "<ul><li>def</li></ul>")
        == "<ul><li>def</li></ul><br>old line 1<br>old line 2"
    )


def test_merge_definition_existing_overlap():
    parsed = "<ul><p>じゅうしょ</p><li>definition</li></ul>"

    # Just plain text
    existing1 = "じゅうしょ<br>existing content"
    assert (
        merge_definition(existing1, parsed)
        == "<ul><p>じゅうしょ</p><li>definition</li></ul>existing content"
    )

    # Wrapped in div
    existing2 = "<div>じゅうしょ</div><div>existing content</div>"
    assert (
        merge_definition(existing2, parsed)
        == "<ul><p>じゅうしょ</p><li>definition</li></ul><div>existing content</div>"
    )

    # With trailing spaces
    existing3 = "じゅうしょ <br>existing"
    assert (
        merge_definition(existing3, parsed)
        == "<ul><p>じゅうしょ</p><li>definition</li></ul>existing"
    )


def test_merge_definition_replace_did_you_mean():
    parsed = "<ul><li>definition of apple</li></ul>"

    # Existing content starts with "Did you mean:"
    existing = "<p>Word 'applz' not found. Did you mean:</p>\n<ul>\n<li>apple</li>\n</ul>"
    assert merge_definition(existing, parsed) == parsed

    # Even with other things after it, just to be safe, replace the whole field.
    existing2 = (
        "<p>Word 'applz' not found. Did you mean:</p>\n<ul><li>apple</li></ul><br>some old note"
    )
    assert merge_definition(existing2, parsed) == parsed
