# -*- coding: utf-8 -*-
"""Wiring tests: fresh fake aqt/anki modules are installed into sys.modules
and the addon is reloaded so its top-level registration re-runs against them
(the pattern from docs/creating-an-addon.md). sys.modules is restored after
each test so other addons' tests still see the conftest mocks."""

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

STATE_NORMAL = 0
STATE_EMPTY = 1
STATE_DUPLICATE = 2

MID = 10
DECK_JA = 2
DECK_TAI = 3


def make_note_class(state):
    class FakeNote:
        next_state = state

        def __init__(self, id, mid, fields, col):
            self.id = id
            self.mid = mid
            self.fields = fields
            self.col = col

        def fields_check(self):
            return type(self).next_state

    return FakeNote


class RoutingDb:
    """Answers the two query shapes the addon issues."""

    def __init__(self, note_rows=(), card_dids=()):
        self.note_rows = list(note_rows)
        self.card_dids = list(card_dids)
        self.queries = []

    def all(self, sql, *params):
        self.queries.append((sql, params))
        if "FROM cards" in sql and "DISTINCT did" in sql:
            return [(did,) for did in self.card_dids]
        if "FROM notes" in sql:
            return list(self.note_rows)
        return []


def make_decks(names):
    """names: {did: 'Parent::Child'}. Duck-types col.decks."""

    class FakeDecks:
        def all_names_and_ids(self):
            return [SimpleNamespace(id=did, name=name) for did, name in names.items()]

        def by_name(self, name):
            for did, n in names.items():
                if n == name:
                    return {"id": did, "name": n}
            return None

        def current(self):
            did, name = next(iter(names.items()))
            return {"id": did, "name": name}

    return FakeDecks()


@pytest.fixture
def load_addon():
    saved = {}
    loaded = []

    def _load(state=STATE_DUPLICATE, config=None, note_rows=(), card_dids=(), deck_names=None):
        for name in ("aqt", "aqt.utils", "aqt.qt", "anki", "anki.notes"):
            saved.setdefault(name, sys.modules.get(name))

        aqt = types.ModuleType("aqt")
        aqt.gui_hooks = SimpleNamespace(
            add_cards_did_init=[],
            add_cards_did_change_deck=[],
            browser_menus_did_init=[],
        )
        mw = MagicMock()
        mw.addonManager.getConfig.return_value = config
        aqt.mw = mw
        utils = types.ModuleType("aqt.utils")
        utils.tooltip = MagicMock()
        qt = types.ModuleType("aqt.qt")
        qt.qconnect = MagicMock()

        anki = types.ModuleType("anki")
        notes_mod = types.ModuleType("anki.notes")
        note_class = make_note_class(state)
        notes_mod.Note = note_class
        anki.notes = notes_mod

        sys.modules.update(
            {
                "aqt": aqt,
                "aqt.utils": utils,
                "aqt.qt": qt,
                "anki": anki,
                "anki.notes": notes_mod,
            }
        )

        import deck_scoped_dupes

        mod = importlib.reload(deck_scoped_dupes)
        db = RoutingDb(note_rows=note_rows, card_dids=card_dids)
        decks = make_decks(deck_names or {DECK_JA: "言語::日語", DECK_TAI: "言語::台語"})
        col = SimpleNamespace(db=db, decks=decks)
        loaded.append((mod, note_class, col, db, aqt, utils))
        return SimpleNamespace(mod=mod, Note=note_class, col=col, db=db, aqt=aqt, utils=utils)

    yield _load

    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    import deck_scoped_dupes

    importlib.reload(deck_scoped_dupes)


class TestFieldsCheckPatch:
    def test_wraps_fields_check_and_sets_sentinel(self, load_addon):
        env = load_addon()
        assert env.Note._deck_scoped_dupes_patched is True
        note = env.Note(0, MID, ["水"], env.col)
        assert callable(note.fields_check)

    def test_non_duplicate_states_pass_through_untouched(self, load_addon):
        env = load_addon(state=STATE_EMPTY)
        note = env.Note(0, MID, [""], env.col)
        assert note.fields_check() == STATE_EMPTY
        assert env.db.queries == []

    def test_new_note_dupe_in_target_deck_keeps_flag(self, load_addon):
        env = load_addon(note_rows=[(7, MID, "水\x1fwater")])
        env.mod.on_add_cards_did_init(
            SimpleNamespace(deck_chooser=SimpleNamespace(selected_deck_id=DECK_JA))
        )
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_new_note_dupe_only_in_other_deck_clears_flag(self, load_addon):
        env = load_addon(note_rows=[])
        env.mod.on_add_cards_did_init(
            SimpleNamespace(deck_chooser=SimpleNamespace(selected_deck_id=DECK_JA))
        )
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_NORMAL

    def test_new_note_without_add_cards_context_keeps_flag(self, load_addon):
        env = load_addon()
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE
        assert env.db.queries == []

    def test_existing_note_sharing_deck_keeps_flag(self, load_addon):
        env = load_addon(note_rows=[(7, MID, "水\x1fwater")], card_dids=[DECK_JA])
        note = env.Note(5, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_existing_note_with_no_shared_deck_clears_flag(self, load_addon):
        env = load_addon(note_rows=[], card_dids=[DECK_TAI])
        note = env.Note(5, MID, ["水"], env.col)
        assert note.fields_check() == STATE_NORMAL

    def test_existing_note_without_cards_keeps_flag(self, load_addon):
        env = load_addon(card_dids=[])
        note = env.Note(5, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_include_subdecks_config_expands_scope(self, load_addon):
        decks = {1: "言語", DECK_JA: "言語::日語", DECK_TAI: "言語::台語"}
        env = load_addon(config={"include_subdecks": True}, note_rows=[], deck_names=decks)
        env.mod.on_add_cards_did_change_deck(1)
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_NORMAL
        notes_queries = [q for q in env.db.queries if "FROM notes" in q[0]]
        assert notes_queries, "expected a notes query"
        params = notes_queries[0][1]
        assert set(params[2:]) == {1, DECK_JA, DECK_TAI}

    def test_exact_deck_only_by_default(self, load_addon):
        decks = {1: "言語", DECK_JA: "言語::日語"}
        env = load_addon(note_rows=[], deck_names=decks)
        env.mod.on_add_cards_did_change_deck(1)
        note = env.Note(0, MID, ["水"], env.col)
        note.fields_check()
        notes_queries = [q for q in env.db.queries if "FROM notes" in q[0]]
        assert set(notes_queries[0][1][2:]) == {1}


class TestHookRegistration:
    def test_gui_hooks_registered(self, load_addon):
        env = load_addon()
        hooks = env.aqt.gui_hooks
        assert env.mod.on_add_cards_did_init in hooks.add_cards_did_init
        assert env.mod.on_add_cards_did_change_deck in hooks.add_cards_did_change_deck
        assert env.mod.on_browser_menus_did_init in hooks.browser_menus_did_init

    def test_deck_tracking(self, load_addon):
        env = load_addon()
        addcards = SimpleNamespace(deck_chooser=SimpleNamespace(selected_deck_id=42))
        env.mod.on_add_cards_did_init(addcards)
        assert env.mod._add_cards_deck_id == 42
        env.mod.on_add_cards_did_change_deck(7)
        assert env.mod._add_cards_deck_id == 7


class TestBrowserFindDupes:
    def make_browser(self, env, search, rows):
        browser = MagicMock()
        browser.current_search.return_value = search
        browser.mw.col = SimpleNamespace(db=RoutingDb(note_rows=rows), decks=env.col.decks)
        return browser

    def test_menu_action_added(self, load_addon):
        env = load_addon()
        browser = MagicMock()
        env.mod.on_browser_menus_did_init(browser)
        browser.form.menu_Notes.addAction.assert_called_once()

    def test_narrows_browser_to_dupe_notes_in_deck(self, load_addon):
        env = load_addon()
        rows = [
            (1, MID, "水\x1fwater"),
            (2, MID, "<b>水</b>\x1fwater"),
            (3, MID, "火\x1ffire"),
        ]
        browser = self.make_browser(env, 'deck:"言語::日語"', rows)
        env.mod.find_dupes_in_current_deck(browser)
        browser.search_for.assert_called_once_with("nid:1,2")

    def test_current_keyword_resolves_current_deck(self, load_addon):
        env = load_addon()
        rows = [(1, MID, "水\x1fx"), (2, MID, "水\x1fy")]
        browser = self.make_browser(env, "deck:current", rows)
        env.mod.find_dupes_in_current_deck(browser)
        assert browser.search_for.called

    def test_no_deck_filter_shows_tooltip(self, load_addon):
        env = load_addon()
        browser = self.make_browser(env, "note:Basic", [])
        env.mod.find_dupes_in_current_deck(browser)
        assert env.utils.tooltip.called
        assert not browser.search_for.called

    def test_no_dupes_found_shows_tooltip(self, load_addon):
        env = load_addon()
        browser = self.make_browser(env, 'deck:"言語::日語"', [(1, MID, "水\x1fx")])
        env.mod.find_dupes_in_current_deck(browser)
        assert env.utils.tooltip.called
        assert not browser.search_for.called


OTHER_MID = 20


class TestCrossNotetypeDupes:
    def test_normal_upgraded_when_cross_notetype_dupe_in_deck(self, load_addon):
        env = load_addon(state=STATE_NORMAL, note_rows=[(7, OTHER_MID, "水\x1fwater")])
        env.mod.on_add_cards_did_change_deck(DECK_JA)
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_no_upgrade_when_cross_notetype_disabled(self, load_addon):
        env = load_addon(
            state=STATE_NORMAL,
            config={"cross_notetype_dupes": False},
            note_rows=[(7, OTHER_MID, "水\x1fwater")],
        )
        env.mod.on_add_cards_did_change_deck(DECK_JA)
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_NORMAL

    def test_duplicate_kept_via_cross_notetype_match(self, load_addon):
        # backend flagged a dupe in another deck (same notetype); the only
        # in-scope match is a different notetype
        env = load_addon(note_rows=[(7, OTHER_MID, "水\x1fwater")])
        env.mod.on_add_cards_did_change_deck(DECK_JA)
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_duplicate_cleared_when_only_cross_match_and_disabled(self, load_addon):
        env = load_addon(
            config={"cross_notetype_dupes": False},
            note_rows=[(7, OTHER_MID, "水\x1fwater")],
        )
        env.mod.on_add_cards_did_change_deck(DECK_JA)
        note = env.Note(0, MID, ["水"], env.col)
        assert note.fields_check() == STATE_NORMAL

    def test_empty_state_never_upgraded(self, load_addon):
        env = load_addon(state=STATE_EMPTY, note_rows=[(7, OTHER_MID, "水\x1fwater")])
        env.mod.on_add_cards_did_change_deck(DECK_JA)
        note = env.Note(0, MID, [""], env.col)
        assert note.fields_check() == STATE_EMPTY
        assert env.db.queries == []

    def test_existing_note_cross_notetype_dupe_upgrades(self, load_addon):
        env = load_addon(
            state=STATE_NORMAL,
            note_rows=[(7, OTHER_MID, "水\x1fwater")],
            card_dids=[DECK_JA],
        )
        note = env.Note(5, MID, ["水"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_browser_finder_groups_across_notetypes(self, load_addon):
        env = load_addon()
        rows = [
            (1, MID, "水\x1fwater"),
            (2, OTHER_MID, "水\x1fwater"),
        ]
        browser = TestBrowserFindDupes.make_browser(self, env, 'deck:"言語::日語"', rows)
        env.mod.find_dupes_in_current_deck(browser)
        browser.search_for.assert_called_once_with("nid:1,2")

    def test_browser_finder_per_notetype_when_disabled(self, load_addon):
        env = load_addon(config={"cross_notetype_dupes": False})
        rows = [
            (1, MID, "水\x1fwater"),
            (2, OTHER_MID, "水\x1fwater"),
        ]
        browser = TestBrowserFindDupes.make_browser(self, env, 'deck:"言語::日語"', rows)
        env.mod.find_dupes_in_current_deck(browser)
        assert env.utils.tooltip.called
        assert not browser.search_for.called


DECK_FIN = 6
FIN_DECKS = {DECK_FIN: "金融", DECK_JA: "言語::日語"}
CI_CONFIG = {"case_insensitive_decks": ["金融"]}


class TestCaseInsensitiveDecks:
    def test_case_variant_upgrades_in_listed_deck(self, load_addon):
        env = load_addon(
            state=STATE_NORMAL,
            config=CI_CONFIG,
            note_rows=[(7, MID, "NASDAQ\x1findex")],
            deck_names=FIN_DECKS,
        )
        env.mod.on_add_cards_did_change_deck(DECK_FIN)
        note = env.Note(0, MID, ["nasdaq"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_case_variant_ignored_in_unlisted_deck(self, load_addon):
        env = load_addon(
            state=STATE_NORMAL,
            config=CI_CONFIG,
            note_rows=[(7, MID, "NASDAQ\x1findex")],
            deck_names=FIN_DECKS,
        )
        env.mod.on_add_cards_did_change_deck(DECK_JA)
        note = env.Note(0, MID, ["nasdaq"], env.col)
        assert note.fields_check() == STATE_NORMAL

    def test_listed_parent_covers_subdeck(self, load_addon):
        decks = {8: "金融::股票", DECK_JA: "言語::日語"}
        env = load_addon(
            state=STATE_NORMAL,
            config=CI_CONFIG,
            note_rows=[(7, MID, "NASDAQ\x1findex")],
            deck_names=decks,
        )
        env.mod.on_add_cards_did_change_deck(8)
        note = env.Note(0, MID, ["nasdaq"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_duplicate_kept_via_case_variant(self, load_addon):
        env = load_addon(
            config=CI_CONFIG,
            note_rows=[(7, MID, "NASDAQ\x1findex")],
            deck_names=FIN_DECKS,
        )
        env.mod.on_add_cards_did_change_deck(DECK_FIN)
        note = env.Note(0, MID, ["nasdaq"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_existing_note_case_variant_upgrades(self, load_addon):
        env = load_addon(
            state=STATE_NORMAL,
            config=CI_CONFIG,
            note_rows=[(7, OTHER_MID, "NASDAQ\x1findex")],
            card_dids=[DECK_FIN],
            deck_names=FIN_DECKS,
        )
        note = env.Note(5, MID, ["nasdaq"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_cross_notetype_disabled_still_allows_same_type_ci(self, load_addon):
        config = {"case_insensitive_decks": ["金融"], "cross_notetype_dupes": False}
        env = load_addon(
            state=STATE_NORMAL,
            config=config,
            note_rows=[(7, MID, "NASDAQ\x1findex")],
            deck_names=FIN_DECKS,
        )
        env.mod.on_add_cards_did_change_deck(DECK_FIN)
        note = env.Note(0, MID, ["nasdaq"], env.col)
        assert note.fields_check() == STATE_DUPLICATE

    def test_browser_finder_groups_case_variants(self, load_addon):
        env = load_addon(config=CI_CONFIG, deck_names=FIN_DECKS)
        rows = [(1, MID, "Nasdaq\x1fx"), (2, MID, "NASDAQ\x1fy")]
        browser = TestBrowserFindDupes.make_browser(self, env, "deck:金融", rows)
        env.mod.find_dupes_in_current_deck(browser)
        browser.search_for.assert_called_once_with("nid:1,2")

    def test_browser_finder_case_sensitive_in_unlisted_deck(self, load_addon):
        env = load_addon(config=CI_CONFIG, deck_names=FIN_DECKS)
        rows = [(1, MID, "Nasdaq\x1fx"), (2, MID, "NASDAQ\x1fy")]
        browser = TestBrowserFindDupes.make_browser(self, env, 'deck:"言語::日語"', rows)
        env.mod.find_dupes_in_current_deck(browser)
        assert env.utils.tooltip.called
        assert not browser.search_for.called
