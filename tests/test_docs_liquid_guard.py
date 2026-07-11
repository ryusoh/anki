"""Guard: markdown published by GitHub Pages must not contain bare ``{{``.

The repo is published via GitHub Pages (actions/jekyll-build-pages), which
runs **Jekyll 3.10**. Jekyll pipes every non-dot-directory markdown file
through Liquid, EVEN INSIDE fenced/inline code, and:

- an unterminated-looking ``{{`` (e.g. JSDoc ``@typedef`` braces) hard-fails
  the whole Pages build with ``Liquid syntax error: Variable '{{' was not
  properly terminated`` — this broke the build twice on 2026-07-11
  (docs/terminal-calendar-ranges.md, then docs/delegation-specs.md);
- a well-formed one (e.g. Anki's template fields) renders as an empty Liquid
  variable, silently mangling the published page.

**``render_with_liquid: false`` front matter does NOT help**: it is a
Jekyll 4.0 feature and Jekyll 3.10 silently ignores it (first fix attempt,
reverted — see commit b6a68a24). The only mitigation that works on this
Pages setup is wrapping the brace-bearing span in raw tags::

    {% raw %}{{ ... }}{% endraw %}

or rewording prose to avoid literal double braces. This test enforces that:
after stripping raw-tag regions, no tracked, Pages-visible markdown file may
contain ``{{``. (Dot-directories like .agents/ and .claude/ are invisible to
Jekyll and exempt.)
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_REGION = re.compile(r"{%\s*raw\s*%}.*?{%\s*endraw\s*%}", re.DOTALL)


def _pages_visible_markdown():
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for rel in out.splitlines():
        # Jekyll skips files under dot-directories (.agents/, .claude/, ...).
        if any(part.startswith(".") for part in Path(rel).parts[:-1]):
            continue
        yield rel


def test_pages_markdown_has_no_bare_liquid_braces():
    offenders = []
    for rel in _pages_visible_markdown():
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        if "{{" in RAW_REGION.sub("", text):
            offenders.append(rel)
    assert not offenders, (
        "These Pages-visible markdown files contain a bare '{{' — Jekyll "
        "3.10 Liquid will crash the Pages build (or silently mangle the "
        "page), and render_with_liquid front matter does NOT work on "
        "Jekyll 3. Wrap the span in {% raw %}...{% endraw %} or reword: "
        f"{offenders}"
    )
