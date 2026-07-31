# -*- coding: utf-8 -*-

"""Tiny local language detector for the single-button TTS flow.

Only distinguishes Japanese from English (everything else). This is a
local copy to avoid cross-addon imports; it intentionally does not cover
all Unicode edge cases.
"""

from typing import Optional

__all__ = ['detect_language']


# Ranges that identify Japanese writing.
_JA_RANGES = [
    # Hiragana
    (0x3040, 0x309F),
    # Katakana (full-width)
    (0x30A0, 0x30FF),
    # Half-width katakana
    (0xFF65, 0xFF9F),
    # CJK Unified Ideographs (common kanji)
    (0x4E00, 0x9FFF),
    # CJK Unified Ideographs Extension A (less common kanji)
    (0x3400, 0x4DBF),
]


def _is_ja_char(char: str) -> bool:
    """Return True if a single character signals Japanese text."""
    if len(char) != 1:
        return False
    code = ord(char)
    return any(start <= code <= end for start, end in _JA_RANGES)


def detect_language(text: str) -> Optional[str]:
    """Return 'ja' if text contains Japanese characters, otherwise 'en'.

    Returns ``None`` for empty/whitespace input so the caller can decide
    whether to treat that as a no-op.
    """
    if not text or not text.strip():
        return None
    if any(_is_ja_char(char) for char in text):
        return 'ja'
    return 'en'
