"""Tests for tools/check_thinking_comments.py (the thinking-check gate).

Sample violations live in string literals, never in real comments, so this
file stays clean under the gate itself.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_thinking_comments import (
    find_violations,
    iter_tracked_sources,
    scan_abandoned_tests,
    scan_js_comments,
    scan_js_empty_tests,
    scan_python_comments,
    thinking_in_comment,
)


def test_iter_sources_includes_untracked_not_ignored(monkeypatch):
    # The gate must scan NEW files pre-commit: a tracked-only ls-files let a
    # detector's own self-matching comment pass locally and fail CI once
    # committed. Pin the exact flags (same pattern as Makefile PY_TEST_SUITES).
    calls = []

    class FakeResult:
        stdout = "a/tracked.py\na/tracked.py\nb/new.js\n"

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeResult()

    monkeypatch.setattr("check_thinking_comments.subprocess.run", fake_run)
    assert list(iter_tracked_sources()) == ["a/tracked.py", "b/new.js"]
    cmd = calls[0]
    assert "--cached" in cmd and "--others" in cmd and "--exclude-standard" in cmd


FLAGGED_COMMENTS = [
    "Wait, if core is empty",
    "wait! that breaks",
    "Ah, that explains it",
    "Hmm this is odd",
    "huh",
    "Oh wait, no",
    "oh no this cannot be",
    "Oops wrong branch",
    "Nope, try again",
    "Hold on, is this right",
    "Actually, just pass empty string",
    "How about a command in the trie",
    "Let's check `handleCommand`",
    "lets look at what's in the map",
    "Let me think about this",
    "Let's assume the user provides an rgba string",
    "for simplicity let's rely on globalAlpha",
    "If we just use globalAlpha, it might be easier.",
    "This is tricky without a full color parser.",
    "To hit line 238, core must be empty",
    "blocks to reach line 746.",  # mid-comment coverage note
]

CLEAN_COMMENTS = [
    "Retry after the backoff interval",
    "wait for the DOM before binding",  # "wait" without trailing punctuation is prose
    "It groups by table, so counting works",
    "Expands to 'due' via the switchShortcuts map",
    "Matches the legacy behaviour of upstream",
    "Assume the API returns JSON",  # states a precondition, no first person
    "It lets the caller decide",  # "lets" the verb, not "let's"
]


def test_flagged_comments_detected():
    for text in FLAGGED_COMMENTS:
        assert thinking_in_comment(text), f"should flag: {text!r}"


def test_clean_comments_not_flagged():
    for text in CLEAN_COMMENTS:
        assert not thinking_in_comment(text), f"false positive: {text!r}"


def test_python_comment_flagged_with_lineno():
    src = "x = 1\n# Wait, this cannot be right\ny = 2\n"
    assert list(scan_python_comments(src)) == [(2, "Wait, this cannot be right")]


def test_python_string_contents_are_not_comments():
    src = 'MSG = "Wait, if core is empty"\n'
    assert list(scan_python_comments(src)) == []


def test_python_unparseable_source_skipped():
    assert list(scan_python_comments("def broken(:\n")) == []


def test_abandoned_module_level_test_flagged():
    src = "def test_nothing():\n    pass\n"
    assert list(scan_abandoned_tests(src)) == [(1, "test_nothing")]


def test_abandoned_docstring_only_test_flagged():
    src = 'def test_nothing():\n    """TODO: write this."""\n'
    assert list(scan_abandoned_tests(src)) == [(1, "test_nothing")]


def test_abandoned_ellipsis_test_flagged():
    src = "def test_nothing():\n    ...\n"
    assert list(scan_abandoned_tests(src)) == [(1, "test_nothing")]


def test_abandoned_method_in_test_class_flagged():
    src = "class TestThing:\n    def test_nothing(self):\n        pass\n"
    assert list(scan_abandoned_tests(src)) == [(2, "test_nothing")]


def test_nested_helper_not_flagged():
    # pytest never collects closures; a `test_func` helper exercising a
    # decorator is legitimate (enhance_main_window/tests/test_debug.py).
    src = "def test_real():\n    def test_func():\n        pass\n    assert test_func() is None\n"
    assert list(scan_abandoned_tests(src)) == []


def test_real_test_not_flagged():
    src = "def test_real():\n    assert 1 + 1 == 2\n"
    assert list(scan_abandoned_tests(src)) == []


def test_non_collectable_pass_bodies_not_flagged():
    src = "def helper():\n    pass\n\n\nclass Plain:\n    def test_x(self):\n        pass\n"
    assert list(scan_abandoned_tests(src)) == []


def test_js_line_comment_flagged():
    hits = list(scan_js_comments("const x = 1;\n// Wait, is this right?\n"))
    assert hits == [(2, "Wait, is this right?")]


def test_js_block_comment_and_interior_flagged():
    src = "/* Ah, now I see */\n/*\n * Hmm not sure\n */\n"
    hits = list(scan_js_comments(src))
    assert [line for line, _ in hits] == [1, 3]


def test_js_url_not_treated_as_comment():
    src = 'const u = "https://example.com/wait,x";\n'
    assert list(scan_js_comments(src)) == []


def test_js_clean_comment_not_flagged():
    src = "// Retry after the backoff interval\n"
    assert list(scan_js_comments(src)) == []


def test_js_empty_arrow_test_flagged():
    src = "it('does nothing', () => {});\n"
    assert list(scan_js_empty_tests(src)) == [(1, "does nothing")]


def test_js_empty_function_test_flagged():
    src = 'test("nothing", function () {\n});\n'
    assert list(scan_js_empty_tests(src)) == [(1, "nothing")]


def test_js_comment_only_body_flagged():
    src = "it('planned', () => {\n  // cover the edge case later\n});\n"
    assert list(scan_js_empty_tests(src)) == [(1, "planned")]


def test_js_real_test_not_flagged():
    src = "it('works', () => { assert.ok(true); });\n"
    assert list(scan_js_empty_tests(src)) == []


def test_js_multiline_title_and_async_flagged():
    src = "it(`async\nnothing`, async () => {\n});\n"
    assert list(scan_js_empty_tests(src)) == [(1, "async\nnothing")]


def test_repo_tree_is_clean():
    # The gate is also exercised here so a violation fails the test suite even
    # when someone runs pytest without the make target.
    assert list(find_violations(iter_tracked_sources())) == []
