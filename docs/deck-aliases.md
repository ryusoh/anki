# Deck Aliases

Quick reference for deck aliases.

## Aliases

| Alias    | Deck Name | Language    | Notes  |
| -------- | --------- | ----------- | ------ |
| `J`, `1` | 言語日語  | Japanese    | 50,193 |
| `C`, `2` | 言語粤語  | Cantonese   | 34,463 |
| `E`, `3` | 言語英語  | English     | 29,610 |
| `S`, `4` | 言語呉語  | Wu/Shanghai | 18,600 |
| `T`, `5` | 言語台語  | Taiwanese   | 15,163 |
| `F`, `6` | 金融      | Finance     | 13,147 |

## Usage

```bash
# With aliases
python3 graph/analyze.py --deck J
python3 graph/analyze.py --deck 1
python3 graph/analyze.py --deck C
python3 graph/analyze.py --deck F  # Both finance decks

# With Makefile
make graph-deck DECK=J
make graph-deck DECK=C
make graph-deck DECK=E
make graph-deck DECK=F
```

## Examples

```bash
# Analyze Japanese deck
make graph-deck DECK=J

# Analyze Cantonese deck
make graph-deck DECK=C

# Analyze both finance decks
make graph-deck DECK=F
```

## Why Aliases?

Deck names are in Chinese/Japanese characters which are:

- Hard to type in terminal
- Easy to mistype
- Require IME switching

Aliases are **fast and memorable**:

- **J** = Japanese
- **C** = Cantonese
- **E** = English
- **S** = Shanghai (Wu)
- **T** = Taiwanese
- **F** = Finance

## Deck-name storage gotchas

- **粤語 is U+7CA4 (`粤`), not U+7CB5 (`粵`).** The two glyphs render
  identically, but the real deck name uses U+7CA4 — a query typed with 粵
  (U+7CB5) silently matches zero notes. Don't type CJK deck names; build
  queries from AnkiConnect `deckNames` output.
- **Hierarchy separator differs by interface.** In the sqlite `decks` table,
  `name` uses U+001F (`言語␟日語`); AnkiConnect and the Anki UI use `::`
  (`言語::日語`).
- **Current collections keep decks in the `decks` table** (`SELECT id, name
FROM decks`). The legacy `col.decks` JSON column is empty — querying it
  fails with a JSON decode error.
