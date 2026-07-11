"""Guard: docs containing Liquid-lookalike syntax must disable Liquid rendering.

The repo's docs are published via GitHub Pages (Jekyll). Jekyll's Liquid
templating eats ``{{ ... }}`` sequences EVEN INSIDE fenced code blocks, which
silently mangles rendered docs. Two real cases:

- JSDoc typedef braces (``@typedef {{ kind: "duration", ... }}``) in
  docs/terminal-calendar-ranges.md — fixed by hand in commit 87df3ff3.
- Anki template syntax (``{{Front}}`` / ``{{Back}}``) in
  docs/anki-knowledge-graph-architecture.md — the latent instance this test
  was born red against.

The fix is a YAML front-matter block at the very top of the file:

    ---
    render_with_liquid: false
    ---

This test makes the rule a gate instead of tribal knowledge: any docs/*.md
containing ``{{`` must declare ``render_with_liquid: false``.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"


def _front_matter(text: str) -> str:
    """Return the YAML front-matter block, or '' if the file has none."""
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    return text[4:end] if end != -1 else ""


def test_docs_with_liquid_lookalikes_disable_liquid_rendering():
    offenders = []
    for md in sorted(DOCS_DIR.glob("**/*.md")):
        text = md.read_text(encoding="utf-8")
        if "{{" not in text:
            continue
        if "render_with_liquid: false" not in _front_matter(text):
            offenders.append(str(md.relative_to(REPO_ROOT)))
    assert not offenders, (
        "These docs contain '{{' (Jekyll/Liquid will mangle them on GitHub "
        "Pages, even inside code fences) but lack 'render_with_liquid: false' "
        "front matter — add the front-matter block from "
        f"tests/test_docs_liquid_guard.py's docstring: {offenders}"
    )
