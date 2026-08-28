# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
# Copyright (C) 2010-Present  Anki AwesomeTTS Development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Single-click, auto-detect, failover TTS flow for the editor button."""

import html
import os
import re

import aqt.qt
import aqt.utils

from .langdetect import detect_language

__all__ = [
    'DOUBLE_CLICK_INTERVAL_MS',
    'LANGUAGE_SERVICES',
    'run_single_click_flow',
]


DOUBLE_CLICK_INTERVAL_MS = 300

LANGUAGE_SERVICES = {
    'ja': {
        'main': 'edgetts',
        'backup': 'voicevox',
        'voice': 'ja-JP-NanamiNeural',
    },
    'en': {
        'main': 'edgetts',
        'backup': 'kokoro',
        'voice': 'en-US-AvaNeural',
    },
}


def _plain_text(field_html):
    """Fallback HTML-to-text for the TTS source when no stripper is injected.

    Tags become spaces (never empty strings, or ``<b>a</b><b>b</b>`` would
    merge into ``ab``), character entities are decoded (``&nbsp;`` read aloud
    as "and and nbsp" was the bug that prompted this), and all whitespace —
    including the non-breaking space entities decode to — is collapsed.
    """
    text = re.sub(r'<[^>]+>', ' ', field_html)
    return ' '.join(html.unescape(text).split())


def _field_index(note, name):
    """Return the index of a field by name, or None."""
    for idx, field in enumerate(note.model()['flds']):
        if field['name'] == name:
            return idx
    return None


_TRAILING_BREAKS = re.compile(r'(?:\s|<br\s*/?>|<div>\s*<br\s*/?>\s*</div>)+$', re.IGNORECASE)


def _add_media_tag(editor, path):
    """Copy the audio file into Anki's media folder and return its [sound:] tag.

    ``[sound:]`` resolves only inside ``collection.media``, so a tag pointing
    at the AwesomeTTS cache plays nothing. This mirrors AwesomeTTS's own
    dialog, which calls ``Editor._addMedia`` (copies the file and returns the
    tag with the final, deduplicated filename).
    """
    add_media = getattr(editor, '_addMedia', None)
    if callable(add_media):
        return add_media(path)
    return f'[sound:{os.path.basename(path)}]'


def _append_sound_tag(note, back_idx, tag):
    """Append the [sound:] tag to the Back field on its own line.

    A ``<div>`` block is used instead of ``<br>``: when the existing content
    ends with a block-level close tag (``</div>``), a ``<br>`` after it
    renders as a blank line, while adjacent blocks never do. Trailing
    ``<br>``/whitespace runs (left behind by pressing Enter in the editor)
    are collapsed first for the same reason.
    """
    existing = _TRAILING_BREAKS.sub('', note.fields[back_idx])
    if existing:
        note.fields[back_idx] = existing + '<div>' + tag + '</div>'
    else:
        note.fields[back_idx] = tag


def _show_tooltip(message):
    aqt.utils.tooltip(f'AwesomeTTS: {message}', 3000)


def run_single_click_flow(editor, router, strip=None):
    """Generate audio from the Front field and append it to the Back field.

    ``strip`` converts raw field HTML to speakable text; pass AwesomeTTS's
    own ``addon.strip.from_note`` in real Anki. The local ``_plain_text``
    fallback is used when no stripper is given.
    """
    note = editor.note
    front_idx = _field_index(note, 'Front')
    back_idx = _field_index(note, 'Back')
    if front_idx is None or back_idx is None:
        _show_tooltip('Front/Back fields not found')
        return

    text = (strip or _plain_text)(note.fields[front_idx]).strip()
    if not text:
        _show_tooltip('no text in Front field')
        return

    lang = detect_language(text)
    if lang is None:
        _show_tooltip('no text in Front field')
        return

    cfg = LANGUAGE_SERVICES.get(lang)
    if cfg is None:
        _show_tooltip(f'unsupported language: {lang}')
        return

    main_id = cfg['main']
    backup_id = cfg['backup']
    main_options = {'voice': cfg['voice']} if cfg.get('voice') else {}

    def on_main_okay(path):
        _append_sound_tag(note, back_idx, _add_media_tag(editor, path))
        _refresh_editor(editor)
        _show_tooltip(f'added audio ({main_id})')

    def on_backup_okay(path):
        _append_sound_tag(note, back_idx, _add_media_tag(editor, path))
        _refresh_editor(editor)
        _show_tooltip(f'added audio ({backup_id} — {main_id} failed)')

    def on_main_fail(exception, _text):
        def on_backup_fail(backup_exception, _text):
            _show_tooltip(
                f'{main_id} failed ({exception}); {backup_id} failed ({backup_exception})'
            )

        router(
            backup_id,
            text,
            {},
            callbacks={'okay': on_backup_okay, 'fail': on_backup_fail},
        )

    router(
        main_id,
        text,
        main_options,
        callbacks={'okay': on_main_okay, 'fail': on_main_fail},
    )


def _refresh_editor(editor):
    """Ask the editor to redraw without losing focus, if available."""
    refresh = getattr(editor, 'loadNoteKeepingFocus', None) or getattr(editor, 'loadNote', None)
    if refresh:
        refresh()


def make_click_handler(launch_dialog, router, strip=None):
    """Return a click handler that distinguishes single and double clicks.

    The returned callable accepts an ``editor`` argument. A single click
    starts a short timer; if a second click arrives before the timer fires,
    the timer is cancelled and the dialog is opened. If the timer fires, the
    single-click TTS flow runs. ``strip`` is passed through to
    ``run_single_click_flow``.
    """
    state = {'waiting': False, 'timer': None}

    def on_timeout(editor):
        state['waiting'] = False
        run_single_click_flow(editor, router, strip=strip)

    def handler(editor):
        if state['waiting']:
            state['timer'].stop()
            state['waiting'] = False
            launch_dialog(editor)
            return

        state['waiting'] = True
        timer = aqt.qt.QTimer(editor.widget)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: on_timeout(editor))
        timer.start(DOUBLE_CLICK_INTERVAL_MS)
        state['timer'] = timer

    return handler
