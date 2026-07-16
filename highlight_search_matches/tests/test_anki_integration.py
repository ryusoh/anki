from unittest.mock import MagicMock, patch

from highlight_search_matches.anki_integration import (
    init_addon,
    on_browser_did_search_filter,
)


def _make_context(search, ids, notes_by_item, notes_mode=False):
    """Build a SearchContext mock whose col resolves item ids to note mocks."""
    ctx = MagicMock()
    ctx.search = search
    ctx.ids = ids
    ctx.browser.table.is_notes_mode.return_value = notes_mode

    def get_note(item_id):
        return notes_by_item[item_id]

    def get_card(item_id):
        card = MagicMock()
        card.note.return_value = notes_by_item[item_id]
        return card

    ctx.browser.col.get_note.side_effect = get_note
    ctx.browser.col.get_card.side_effect = get_card
    return ctx


def _note(note_id, fields):
    note = MagicMock()
    note.id = note_id
    note.fields = fields
    return note


def test_filter_drops_entity_only_matches_cards_mode():
    ctx = _make_context(
        "BSP",
        ids=[11, 22],
        notes_by_item={
            11: _note(1, ["BSP tree"]),
            22: _note(2, ["word1&nbsp;word2"]),
        },
    )
    on_browser_did_search_filter(ctx)
    assert ctx.ids == [11]


def test_filter_drops_entity_only_matches_notes_mode():
    ctx = _make_context(
        "BSP",
        ids=[1, 2],
        notes_by_item={
            1: _note(1, ["word1&nbsp;word2"]),
            2: _note(2, ["a BSP here"]),
        },
        notes_mode=True,
    )
    on_browser_did_search_filter(ctx)
    assert ctx.ids == [2]
    assert not ctx.browser.col.get_card.called


def test_filter_skips_when_no_plain_terms():
    ctx = _make_context("deck:Default", ids=[11], notes_by_item={})
    on_browser_did_search_filter(ctx)
    assert ctx.ids == [11]
    assert not ctx.browser.col.get_card.called
    assert not ctx.browser.col.get_note.called


def test_filter_skips_wildcard_terms():
    # "BS*" can match text we cannot verify literally — never drop results
    ctx = _make_context("BS*", ids=[11], notes_by_item={11: _note(1, ["BSD"])})
    on_browser_did_search_filter(ctx)
    assert ctx.ids == [11]
    assert not ctx.browser.col.get_card.called


def test_filter_skips_empty_ids():
    ctx = _make_context("BSP", ids=None, notes_by_item={})
    on_browser_did_search_filter(ctx)
    assert ctx.ids is None


def test_filter_survives_exceptions():
    ctx = _make_context("BSP", ids=[11, 22], notes_by_item={})
    ctx.browser.col.get_card.side_effect = Exception("db error")
    on_browser_did_search_filter(ctx)
    assert ctx.ids == [11, 22]


def test_filter_drops_every_card_of_a_noise_note():
    shared = _note(1, ["word1&nbsp;word2"])
    ctx = _make_context("BSP", ids=[11, 22], notes_by_item={11: shared, 22: shared})
    on_browser_did_search_filter(ctx)
    assert ctx.ids == []
    assert ctx.browser.col.get_card.call_count == 2


def test_init_addon_registers_hook():
    with patch('highlight_search_matches.anki_integration.browser_did_search', MagicMock()) as hook:
        init_addon()
        hook.append.assert_called_once_with(on_browser_did_search_filter)


def test_filter_no_changes_when_kept_equals_ids():
    # If all items match exactly, the context ids list should remain unchanged
    ctx = _make_context(
        "BSP",
        ids=[11],
        notes_by_item={
            11: _note(1, ["BSP tree"]),
        },
    )
    original_ids = list(ctx.ids)
    on_browser_did_search_filter(ctx)
    assert ctx.ids == original_ids
