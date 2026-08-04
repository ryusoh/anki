---
name: batch-card-edit
description: Batch-rewrite or tidy card fields across a whole Anki deck via AnkiConnect (field moves, format fixes). Use when the user wants the same field transform applied to many cards.
---

# Batch Card Edit

Rewriting card fields across a whole deck without breaking the collection.
Reference implementation: `tools/fix_jp_pinyin_front.py` and
`tools/test_fix_jp_pinyin_front.py` (front-collapse mode + `--tidy` mode).

## Safety rules (non-negotiable)

- **Never write to `collection.anki2` with sqlite.** Writes go through
  AnkiConnect only (Anki must be running). Reads may use a temp copy of the
  collection — `tools/dump_field.py` shows the pattern.
- **Dry-run first, always.** The user pulls the `--apply` trigger on their
  live collection; you verify and hand over the command.
- **Runs must be idempotent.** An interrupted apply is re-run; already-fixed
  notes must plan zero changes.
- **Batch writers over AnkiConnect must be robust.** A single
  `RemoteDisconnected` killed a 6k-note run at note ~3000, and a silent
  10-minute write phase reads as "stuck". So: chunk `notesInfo` (~500 ids per
  request), retry transient connection drops with backoff, and print progress
  every N writes.

## The loop (TDD)

1. **Inspect real field HTML first** — `python3 tools/dump_field.py
--contains '<text>'`. Never guess field shape: decks mix leaf-`<div>`
   lines, `<br>` lines, and nested wrapper divs, sometimes within one deck.
2. **Failing test first**, next to the tool (`tools/test_<name>.py`), using
   captured real HTML as fixtures. Then implement the transform as a pure
   function (field text in → new text / `None` for "leave alone").
3. **Offline sweep before anything live** —
   `python3 tools/sweep_transform.py <module>:<func> --limit 0` runs the
   transform over every note in a collection copy. Require 0 errors and 0
   idempotency violations.
4. **Live dry-run** via AnkiConnect `findNotes` → `notesInfo`; audit the plan
   for anomalies (emptied fields, lost `[sound:]` refs, unexpected chars,
   per-deck counts).
5. **`make fmt-py` and `make precommit SKIP=1` green.**
6. **Hand the user the `--apply` command(s)**, one per deck. Report expected
   duration (~35 writes/sec) so a long run isn't mistaken for a hang.

## Deck-name gotchas

See `docs/deck-aliases.md` "Deck-name storage gotchas": 粤語 is U+7CA4 (not
U+7CB5 — visually identical, matches nothing), sqlite `decks.name` uses
U+001F separators vs `::` in AnkiConnect, and current collections keep deck
names in the `decks` table (`col.decks` JSON is empty). Build queries from
`deckNames` output instead of typing CJK deck names.

## Known card-shape variants (言語 decks)

Pinned by tests in `tools/test_fix_jp_pinyin_front.py`:

- 拼音練習 sentence cards: front = Chinese line / spaced target-language line /
  拼音練習・發音・音標 practice block. The target line is always the second
  line; collapse fronts to it with spacing stripped.
- **台語 backs already embed a copy of the front** (practice block included) —
  check `MARKER in back` before prepending anything, or you duplicate it.
- Line separators vary per card: leaf `<div>`s or `<br>` — handle both.
- Pre-existing defects in backs: `[sound:]` refs glued to text (put them on
  their own line) and trailing empty-div nests / `<br>` tails (strip them).
  呉語 and 英語 have no 拼音練習 cards; they are vocab decks with their own
  glued-sound tails.
