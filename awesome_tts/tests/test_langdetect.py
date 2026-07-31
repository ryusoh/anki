# -*- coding: utf-8 -*-
"""Tests for awesometts.langdetect."""

import pytest

from awesome_tts.awesometts.langdetect import detect_language


@pytest.mark.parametrize(
    'text, expected',
    [
        ('日陰', 'ja'),
        ('ひかげ', 'ja'),
        ('ヒカゲ', 'ja'),
        ('ﾋｶｹﾞ', 'ja'),
        ('hello world', 'en'),
        ('123', 'en'),
        ('café', 'en'),
        ('mixed 日本語 text', 'ja'),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_empty_input_returns_none():
    assert detect_language('') is None
    assert detect_language('   \n\t  ') is None
