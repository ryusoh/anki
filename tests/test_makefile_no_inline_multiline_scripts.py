"""Regression guard: no backslash-continued interpreter scripts in Makefile recipes.

macOS's bundled GNU make is 3.81 (2006); CI runs make 4.x. They split recipe
lines differently: 3.81 collapses `\\<newline><tab>` into a single line, while
4.x preserves the backslash+newline per POSIX. Outside quotes the shell then
removes them (harmless) — but INSIDE quotes they stay literal, so an inline
script like

    @node -e ' \\
        const pinned = ...; \\
    '

is one valid JS line under local make 3.81 and a multi-line SyntaxError
("Expected unicode escape") under CI's make 4.x. This bit the jsdom-pin guard
on 2026-07-14: green through every local run, red on the first CI run to see
it. The fix class is "put the script in a file" (tools/check_jsdom_pin.mjs);
this test bans the whole pattern so it can't come back with a different
script.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"

# A recipe line that (1) invokes an interpreter with an inline-script flag,
# (2) opens a quote, and (3) ends with a backslash continuation before the
# quote closes on the same line.
_INLINE_CONTINUED = re.compile(
    r"""^\t.*                        # recipe line
        (?:node\s+(?:-e|--eval)|python3?\s+-c|sh\s+-c|perl\s+-e|ruby\s+-e)
        \s+(['"])(?:(?!\1).)*        # opening quote never closed on this line
        \\$                          # ...because the line ends in a continuation
    """,
    re.VERBOSE,
)


def test_no_interpreter_script_is_backslash_continued_inside_quotes():
    offenders = [
        f"line {i}: {line.rstrip()}"
        for i, line in enumerate(MAKEFILE.read_text().splitlines(), start=1)
        if _INLINE_CONTINUED.search(line)
    ]
    assert not offenders, (
        "Makefile has inline interpreter script(s) continued with backslash "
        "inside quotes — make 3.81 (local) collapses these to one line but "
        "make 4.x (CI) keeps the backslashes and the script is a syntax "
        "error. Move the script into a file under tools/ instead:\n" + "\n".join(offenders)
    )
