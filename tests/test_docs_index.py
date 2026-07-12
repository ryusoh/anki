"""Guard: every docs/*.md file must be linked from docs/README.md.

Before docs/README.md existed, docs/ accumulated three overlapping rollup
docs (PROJECT_SUMMARY.md, SETUP.md, QUICK_REFERENCE.md) that duplicated —
and drifted from — focused guides that already existed (deck-aliases.md,
r2-upload-guide.md, incremental-staging.md, ...) because nothing made the
existing docs discoverable. This test keeps docs/README.md an accurate map:
add a new docs/*.md file, link it from the index in the same change, or this
fails.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
INDEX = DOCS_DIR / "README.md"


def test_every_doc_is_linked_from_the_index():
    index_text = INDEX.read_text(encoding="utf-8")
    orphans = sorted(
        p.name
        for p in DOCS_DIR.glob("*.md")
        if p.name != "README.md" and f"]({p.name})" not in index_text
    )
    assert not orphans, (
        "These docs/*.md files aren't linked from docs/README.md — add a "
        f"line for them (or delete them if they're stale): {orphans}"
    )


def test_index_does_not_link_a_missing_doc():
    index_text = INDEX.read_text(encoding="utf-8")
    existing = {p.name for p in DOCS_DIR.glob("*.md")}
    dangling = sorted(
        line.strip()
        for line in index_text.splitlines()
        if "](" in line
        and line.strip().startswith("- [")
        and line.split("](", 1)[1].split(")")[0] not in existing
    )
    assert not dangling, f"docs/README.md links to files that don't exist: {dangling}"
