"""Acceptance-layer tests for the Strip HTML Tags addon.

These are behaviour tests, not unit tests: each one enters through the same
pycmd message the addon's own JavaScript sends when the user presses the
strip button in Anki's editor (`on_js_message`), and asserts the user-visible
outcome — the card field's new content. Expectations are hand-computed from
the feature's contract ("strip formatting, keep the visible line structure"),
independent of how the internals are factored. The unit stream lives in
test_strip_selection.py; duplication is deliberate at the boundary only.
"""

from unittest.mock import MagicMock

from editor_test_double import Editor  # installs the aqt mocks

from strip_html_tags import on_js_message


def _editor_with_fields(fields, current_field=0):
    editor = Editor()
    editor.note = MagicMock()
    editor.note.fields = list(fields)
    editor.currentField = current_field
    editor.addMode = False
    editor.loadNoteKeepingFocus = MagicMock()
    return editor


def test_strip_button_with_no_selection_turns_a_pasted_definition_into_plain_text():
    # A learner pastes a formatted dictionary entry (block wrappers, inline
    # bold, a list, an &nbsp;) into the first field and presses the strip
    # button with nothing selected: every visible line survives as its own
    # line, all formatting is gone, and the second field is untouched.
    pasted = (
        '<div class="def"><b>take up</b> — phrasal verb</div>'
        '<div>to begin to do something&nbsp;regularly</div>'
        '<ul><li>He took up jogging.</li></ul>'
    )
    editor = _editor_with_fields([pasted, '<b>keep me formatted</b>'])

    handled = on_js_message((False, None), 'stripHtmlAll', editor)

    assert handled == (True, None)  # consumed — no other addon may react
    assert editor.note.fields[0] == (
        'take up — phrasal verb<br>' 'to begin to do something regularly<br>' 'He took up jogging.'
    )
    assert editor.note.fields[1] == '<b>keep me formatted</b>'


def test_strip_button_with_a_selection_removes_only_that_selections_formatting():
    # The learner selects "beautiful world" and presses the strip button: the
    # selected text loses its <i> wrapper while the unselected <b>Hello</b>
    # keeps its formatting and the field stays balanced.
    editor = _editor_with_fields(['<div><b>Hello</b> <i>beautiful</i> world</div>'])

    handled = on_js_message((False, None), 'stripHtmlSel:beautiful world', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == '<div><b>Hello</b> beautiful world</div>'


def test_strip_button_on_an_already_plain_field_changes_nothing():
    # Pressing the button on a field that is already plain text is a no-op:
    # the field content is byte-identical and the note is not re-saved.
    editor = _editor_with_fields(['already plain text'])

    handled = on_js_message((False, None), 'stripHtmlAll', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == 'already plain text'
    editor.note.flush.assert_not_called()
    editor.loadNoteKeepingFocus.assert_not_called()
