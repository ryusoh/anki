# -*- coding: utf-8 -*-
"""Tests for awesometts.quicktts single-click flow and click handler."""

import os
from unittest.mock import MagicMock

import pytest

from awesome_tts.awesometts import quicktts


def _make_editor(front='日陰', back='existing'):
    note = MagicMock()
    note.model.return_value = {'flds': [{'name': 'Front'}, {'name': 'Back'}]}
    note.fields = [front, back]

    editor = MagicMock()
    editor.note = note
    editor.loadNoteKeepingFocus = MagicMock()
    # Mirror Anki's Editor._addMedia: copies the file into collection.media
    # and returns the [sound:] tag with the final filename.
    editor._addMedia = MagicMock(side_effect=lambda path: f'[sound:{os.path.basename(path)}]')
    return editor


def _fake_router(results):
    """Return a router that invokes callbacks synchronously.

    ``results`` is a dict mapping svc_id to either a path string (success) or
    an Exception (failure).
    """

    def router(svc_id, text, options, callbacks):
        outcome = results.get(svc_id)
        if isinstance(outcome, Exception):
            callbacks['fail'](outcome, text)
        else:
            callbacks['okay'](outcome)

    return router


@pytest.fixture(autouse=True)
def _mock_tooltip(monkeypatch):
    tooltip_calls = []
    monkeypatch.setattr(quicktts, '_show_tooltip', lambda msg: tooltip_calls.append(msg))
    return tooltip_calls


def test_main_success_ja_appends_sound_and_tooltip(_mock_tooltip):
    editor = _make_editor(front='日陰', back='existing')
    router = _fake_router({'edgetts': '/cache/edgetts_abc.mp3'})

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == 'existing<div>[sound:edgetts_abc.mp3]</div>'
    assert 'added audio (edgetts)' in _mock_tooltip
    editor.loadNoteKeepingFocus.assert_called_once()


def test_main_success_after_block_tag_gets_no_blank_line(_mock_tooltip):
    # A <br> after a block-level close tag renders as a blank line; wrapping
    # the tag in its own <div> never does.
    editor = _make_editor(front='日陰', back='<div>existing</div>')
    router = _fake_router({'edgetts': '/cache/edgetts_abc.mp3'})

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == '<div>existing</div><div>[sound:edgetts_abc.mp3]</div>'


def test_front_field_tags_and_entities_are_stripped(_mock_tooltip):
    # '<a>Schelling</a>&nbsp;<a>point</a>' must be spoken as "Schelling
    # point", not "Schelling and and nbsp point".
    editor = _make_editor(
        front='<strong><a href="https://en.wiktionary.org/wiki/Schelling#English">'
        'Schelling</a>&nbsp;<a href="https://en.wiktionary.org/wiki/point#English">'
        'point</a></strong>',
        back='',
    )
    seen = []

    def router(_svc_id, text, _options, callbacks):
        seen.append(text)
        callbacks['okay']('/cache/en.mp3')

    quicktts.run_single_click_flow(editor, router)

    assert seen == ['Schelling point']


def test_strip_callable_overrides_builtin_fallback(_mock_tooltip):
    editor = _make_editor(front='<b>raw</b>', back='')
    seen = []

    def router(_svc_id, text, _options, callbacks):
        seen.append(text)
        callbacks['okay']('/cache/x.mp3')

    quicktts.run_single_click_flow(editor, router, strip=lambda _html: 'clean text')

    assert seen == ['clean text']


def test_main_success_copies_audio_into_collection_media(_mock_tooltip):
    # A [sound:] tag pointing at the AwesomeTTS cache plays nothing; the file
    # must go through Editor._addMedia into collection.media (mute-bug pin).
    editor = _make_editor(front='日陰', back='')
    router = _fake_router({'edgetts': '/cache/edgetts_abc.mp3'})

    quicktts.run_single_click_flow(editor, router)

    editor._addMedia.assert_called_once_with('/cache/edgetts_abc.mp3')


def test_main_success_collapses_trailing_breaks(_mock_tooltip):
    # The editor leaves a trailing <br> when Enter was pressed; appending our
    # own block after it would produce a blank line before the tag.
    editor = _make_editor(front='日陰', back='existing<br>')
    router = _fake_router({'edgetts': '/cache/edgetts_abc.mp3'})

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == 'existing<div>[sound:edgetts_abc.mp3]</div>'


def test_add_media_tag_falls_back_without_editor_add_media(_mock_tooltip):
    editor = _make_editor(front='日陰', back='')
    editor._addMedia = None
    router = _fake_router({'edgetts': '/cache/edgetts_abc.mp3'})

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == '[sound:edgetts_abc.mp3]'


def test_main_success_empty_back_uses_no_br(_mock_tooltip):
    editor = _make_editor(front='apple', back='')
    router = _fake_router({'edgetts': '/cache/en.mp3'})

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == '[sound:en.mp3]'


def test_main_failure_falls_back_to_voicevox(_mock_tooltip):
    editor = _make_editor(front='日陰', back='')
    router = _fake_router(
        {'edgetts': RuntimeError('network down'), 'voicevox': '/cache/voicevox.mp3'}
    )

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == '[sound:voicevox.mp3]'
    assert 'added audio (voicevox — edgetts failed)' in _mock_tooltip


def test_en_main_failure_falls_back_to_kokoro(_mock_tooltip):
    editor = _make_editor(front='apple', back='')
    router = _fake_router({'edgetts': RuntimeError('network down'), 'kokoro': '/cache/kokoro.mp3'})

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == '[sound:kokoro.mp3]'
    assert 'added audio (kokoro — edgetts failed)' in _mock_tooltip


def test_both_engines_fail_shows_error_tooltip(_mock_tooltip):
    editor = _make_editor(front='日陰', back='')
    router = _fake_router(
        {
            'edgetts': RuntimeError('network down'),
            'voicevox': RuntimeError('engine not running'),
        }
    )

    quicktts.run_single_click_flow(editor, router)

    assert editor.note.fields[1] == ''
    tooltip = _mock_tooltip[0]
    assert 'edgetts failed' in tooltip
    assert 'voicevox failed' in tooltip


def test_empty_front_field_no_engine_call(_mock_tooltip):
    editor = _make_editor(front='   ', back='back')
    router = MagicMock()

    quicktts.run_single_click_flow(editor, router)

    router.assert_not_called()
    assert editor.note.fields[1] == 'back'


def test_click_handler_single_click_runs_flow(monkeypatch):
    editor = _make_editor()
    router = MagicMock()
    launch_dialog = MagicMock()
    handler = quicktts.make_click_handler(launch_dialog, router)

    # Stub QTimer so it fires immediately.
    timer_instance = MagicMock()
    timer_class = MagicMock(return_value=timer_instance)
    monkeypatch.setattr(quicktts.aqt.qt, 'QTimer', timer_class)

    # Capture the timeout callback and invoke it directly.
    def start(_interval):
        # invoke the most recently connected callback
        calls = timer_instance.timeout.connect.call_args_list
        if calls:
            calls[-1][0][0]()

    timer_instance.start = start

    handler(editor)

    router.assert_called_once()
    launch_dialog.assert_not_called()


def test_click_handler_double_click_opens_dialog(monkeypatch):
    editor = _make_editor()
    router = MagicMock()
    launch_dialog = MagicMock()
    handler = quicktts.make_click_handler(launch_dialog, router)

    timer_instance = MagicMock()
    timer_class = MagicMock(return_value=timer_instance)
    monkeypatch.setattr(quicktts.aqt.qt, 'QTimer', timer_class)

    handler(editor)
    handler(editor)

    timer_instance.stop.assert_called_once()
    launch_dialog.assert_called_once_with(editor)
    router.assert_not_called()


def test_click_handler_triple_click_opens_dialog_once(monkeypatch):
    editor = _make_editor()
    router = MagicMock()
    launch_dialog = MagicMock()
    handler = quicktts.make_click_handler(launch_dialog, router)

    timer_instance = MagicMock()
    timer_class = MagicMock(return_value=timer_instance)
    monkeypatch.setattr(quicktts.aqt.qt, 'QTimer', timer_class)

    handler(editor)
    handler(editor)
    handler(editor)

    assert launch_dialog.call_count == 1
    # The third click starts a new single-click timer (first + third starts).
    assert timer_instance.start.call_count == 2
    router.assert_not_called()
