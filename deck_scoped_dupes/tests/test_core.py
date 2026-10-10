# -*- coding: utf-8 -*-
"""Pin the pure comparison helpers against Anki's real dupe semantics.

The reference is Anki 25.02.5's rslib/src/text.rs
(strip_html_preserving_media_filenames → strip_html → decode_entities) and
pylib anki/utils.py field_checksum (first 8 hex digits of the sha1 of the
stripped first field), verified against a real collection's notes.csum.
"""

from deck_scoped_dupes import core


class TestStripForCompare:
    def test_plain_text_unchanged(self):
        assert core.strip_for_compare("fire") == "fire"

    def test_tags_removed_without_inserting_spaces(self):
        assert core.strip_for_compare("<b>ab</b><i>cd</i>") == "abcd"

    def test_block_tags_removed(self):
        assert core.strip_for_compare("<div>line1</div><div>line2</div>") == "line1line2"

    def test_img_tag_becomes_filename_with_spaces(self):
        assert core.strip_for_compare('<img src="foo.jpg">') == " foo.jpg "

    def test_img_single_quoted_src(self):
        assert core.strip_for_compare("<img src='a b.png'>") == " a b.png "

    def test_img_unquoted_src(self):
        assert core.strip_for_compare("<img src=x.gif>") == " x.gif "

    def test_sound_ref_kept_verbatim(self):
        assert core.strip_for_compare("word[sound:x.mp3]") == "word[sound:x.mp3]"

    def test_entities_decoded(self):
        assert core.strip_for_compare("a&amp;b&lt;c") == "a&b<c"

    def test_nbsp_becomes_plain_space(self):
        assert core.strip_for_compare("a&nbsp;b") == "a b"

    def test_style_and_script_blocks_removed(self):
        assert core.strip_for_compare("<style>.a{color:red}</style>x<script>1</script>y") == "xy"

    def test_html_comments_removed(self):
        assert core.strip_for_compare("a<!-- note -->b") == "ab"

    def test_nfc_normalization(self):
        decomposed = "が"  # U+304B U+3099
        assert core.strip_for_compare(decomposed) == "が"

    def test_crlf_and_multiline_tags(self):
        assert core.strip_for_compare("<div\n>line<br>\nnext") == "line\nnext"


class TestFieldChecksum:
    def test_ascii(self):
        # int(sha1("fire").hexdigest()[:8], 16), computed independently
        assert core.field_checksum("fire") == 497565732

    def test_cjk(self):
        assert core.field_checksum("水") == 2415653266


class TestFirstField:
    def test_single_field(self):
        assert core.first_field("only") == "only"

    def test_splits_on_unit_separator(self):
        assert core.first_field("front\x1fback\x1fextra") == "front"


class TestParseDeckFilter:
    def test_quoted_name_with_spaces_and_subdecks(self):
        assert core.parse_deck_filter('deck:"言語::日語" added:1') == "言語::日語"

    def test_unquoted_name(self):
        assert core.parse_deck_filter("deck:金融") == "金融"

    def test_current_keyword(self):
        assert core.parse_deck_filter("deck:current") == "current"

    def test_ignores_negated_deck_term(self):
        assert core.parse_deck_filter('-deck:"言語"') is None

    def test_prefers_positive_term_when_both_present(self):
        assert core.parse_deck_filter('-deck:"A" deck:"B"') == "B"

    def test_no_deck_term(self):
        assert core.parse_deck_filter("note:Basic added:1") is None

    def test_does_not_match_longer_words(self):
        assert core.parse_deck_filter("somedeck:x") is None

    def test_quoted_name_with_inner_spaces(self):
        assert core.parse_deck_filter('deck:"My Deck"') == "My Deck"


class TestExpandSubdecks:
    ALL = [
        (1, "言語"),
        (2, "言語::日語"),
        (3, "言語::日語::N5"),
        (4, "言語::台語"),
        (5, "金融"),
    ]

    def test_exact_only_by_default(self):
        assert core.expand_subdecks({2}, self.ALL, include_subdecks=False) == {2}

    def test_includes_descendants_when_enabled(self):
        assert core.expand_subdecks({1}, self.ALL, include_subdecks=True) == {1, 2, 3, 4}

    def test_does_not_match_sibling_prefix(self):
        assert core.expand_subdecks({2}, self.ALL, include_subdecks=True) == {2, 3}


class TestDupeGroups:
    def test_groups_by_stripped_first_field_per_notetype(self):
        rows = [
            (1, 10, "水\x1fwater"),
            (2, 10, "<b>水</b>\x1fwater"),
            (3, 20, "水\x1fwater"),  # different notetype: not a dupe
            (4, 10, "火\x1ffire"),
        ]
        assert core.dupe_groups(rows) == [("水", [1, 2])]

    def test_ignores_empty_first_fields(self):
        rows = [(1, 10, "\x1fx"), (2, 10, "<br>\x1fy")]
        assert core.dupe_groups(rows) == []

    def test_needs_two_to_group(self):
        rows = [(1, 10, "水\x1fx"), (2, 10, "火\x1fy")]
        assert core.dupe_groups(rows) == []


class FakeDb:
    """Duck-typed stand-in for anki.db.DBProxy: records queries, returns rows."""

    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def all(self, sql, *params):
        self.queries.append((sql, params))
        return self.rows


class TestDecksOfNote:
    def test_returns_distinct_deck_ids(self):
        db = FakeDb([(2,), (3,)])
        assert core.decks_of_note(db, 99) == [2, 3]
        sql, params = db.queries[0]
        assert "from cards" in sql.lower()
        assert params == (99,)


class TestFindDeckDupes:
    """find_deck_dupes returns the notetype ids of in-scope duplicate notes,
    so callers can distinguish same-notetype from cross-notetype dupes."""

    def test_returns_mid_of_same_deck_match(self):
        db = FakeDb([(7, 10, "<b>水</b>\x1fwater")])
        assert core.find_deck_dupes(db, 1, "水", {2}) == {10}
        sql, params = db.queries[0]
        # checksum of the stripped field, other notes only, cards in scope;
        # no notetype constraint so cross-notetype dupes are visible
        assert params == (core.field_checksum("水"), 1, 2)

    def test_includes_other_notetypes(self):
        db = FakeDb([(7, 20, "水\x1fwater")])
        assert core.find_deck_dupes(db, 1, "水", {2}) == {20}

    def test_collects_all_matching_mids(self):
        db = FakeDb([(7, 10, "水\x1fa"), (8, 20, "<i>水</i>\x1fb")])
        assert core.find_deck_dupes(db, 1, "水", {2}) == {10, 20}

    def test_empty_when_fields_differ_after_strip(self):
        db = FakeDb([(7, 10, "氺\x1fwater")])
        assert core.find_deck_dupes(db, 1, "水", {2}) == set()

    def test_empty_with_no_scope_decks(self):
        db = FakeDb([(7, 10, "水\x1fwater")])
        assert core.find_deck_dupes(db, 1, "水", set()) == set()
        assert db.queries == []

    def test_empty_for_blank_first_field(self):
        db = FakeDb([(7, 10, "  \x1fwater")])
        assert core.find_deck_dupes(db, 1, "<br>", {2}) == set()
        assert db.queries == []

    def test_media_filename_equivalence_counts(self):
        db = FakeDb([(7, 10, '<img src="a.png">\x1fx')])
        assert core.find_deck_dupes(db, 1, "<img src=a.png>", {2}) == {10}


class TestDupeGroupsCrossNotetype:
    def test_groups_across_notetypes_when_disabled(self):
        rows = [
            (1, 10, "水\x1fwater"),
            (2, 20, "<b>水</b>\x1fwater"),
            (3, 30, "火\x1ffire"),
        ]
        assert core.dupe_groups(rows, per_notetype=False) == [("水", [1, 2])]

    def test_default_still_per_notetype(self):
        rows = [(1, 10, "水\x1fx"), (2, 20, "水\x1fy")]
        assert core.dupe_groups(rows) == []
