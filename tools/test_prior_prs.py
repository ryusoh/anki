"""Tests for tools/prior_prs.py — prior-PR listing and Jules lane stats."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prior_prs import (  # noqa: E402
    KNOWN_LANES,
    attribute_lane,
    compute_stats,
    format_prs,
    format_stats,
    is_jules_pr,
)


def _jules_pr(number: int, state: str, branch: str, labels: list[str] | None = None) -> dict:
    return {
        'number': number,
        'state': state,
        'title': f'pr {number}',
        'headRefName': branch,
        'author': {'login': 'app/google-labs-jules'},
        'labels': [{'name': name} for name in (labels or [])],
    }


def test_format_includes_number_state_labels_and_title() -> None:
    prs = [
        {'number': 5, 'state': 'OPEN', 'title': 'fix(ui): x', 'labels': [{'name': 'dup'}]},
        {'number': 4, 'state': 'CLOSED', 'title': 'perf(heatmap): y', 'labels': []},
    ]
    out = format_prs(prs)
    assert '#5' in out
    assert 'open' in out
    assert '[dup]' in out
    assert '#4' in out
    assert 'closed' in out
    assert '[' not in out.splitlines()[1]  # no label brackets on the unlabelled PR


def test_format_handles_empty_list() -> None:
    assert format_prs([]) == ''


def test_is_jules_pr_matches_bot_author_only() -> None:
    assert is_jules_pr(_jules_pr(1, 'OPEN', 'bolt-x'))
    assert not is_jules_pr({'author': {'login': 'ryusoh'}})
    assert not is_jules_pr({})


def test_attribute_lane_from_branch_name() -> None:
    assert attribute_lane(_jules_pr(1, 'OPEN', 'typist-service-worker-123')) == 'typist'
    assert attribute_lane(_jules_pr(2, 'OPEN', 'bolt/valid-decks-set-123')) == 'bolt'
    assert (
        attribute_lane(_jules_pr(3, 'OPEN', 'testpilot/graph-export-coverage-123')) == 'testpilot'
    )
    assert attribute_lane(_jules_pr(4, 'OPEN', 'fix/ispeech-net-reset-todo-123')) == 'unattributed'


def test_known_lanes_match_jules_persona_files() -> None:
    personas = {p.stem for p in (Path(__file__).resolve().parent.parent / '.jules').glob('*.md')}
    assert set(KNOWN_LANES) == personas


def test_compute_stats_groups_jules_prs_and_close_reasons() -> None:
    prs = [
        _jules_pr(1, 'MERGED', 'bolt-faster-1'),
        _jules_pr(2, 'CLOSED', 'bolt-slower-2', ['close:ugly']),
        _jules_pr(3, 'OPEN', 'bolt-wip-3'),
        _jules_pr(4, 'MERGED', 'mystery-branch-4'),
        {'number': 5, 'state': 'CLOSED', 'author': {'login': 'ryusoh'}, 'labels': []},
    ]
    stats = compute_stats(prs)
    bolt = stats['lanes']['bolt']
    assert (bolt['open'], bolt['merged'], bolt['closed']) == (1, 1, 1)
    assert bolt['reasons'] == {'close:ugly': 1}
    assert stats['lanes']['unattributed']['merged'] == 1
    # The human-authored PR is excluded from the totals.
    total = stats['total']
    assert (total['open'], total['merged'], total['closed']) == (1, 2, 1)
    assert total['reasons'] == {'close:ugly': 1}


def test_format_stats_renders_rates_and_reasons() -> None:
    stats = compute_stats(
        [
            _jules_pr(1, 'MERGED', 'bolt-x-1'),
            _jules_pr(2, 'CLOSED', 'bolt-y-2', ['close:dup']),
            _jules_pr(3, 'OPEN', 'typist-z-3'),
        ]
    )
    out = format_stats(stats)
    assert 'bolt' in out
    assert '50%' in out  # 1 merged of 2 decided
    assert 'n/a' in out  # typist has no decided PRs
    assert 'TOTAL' in out
    assert 'close:dup=1' in out


def test_format_stats_empty() -> None:
    out = format_stats(compute_stats([]))
    assert 'TOTAL' in out
    assert 'close reasons' not in out


def test_main_file_not_found(monkeypatch, capsys):
    import subprocess

    from prior_prs import main

    def mock_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", mock_run)
    with pytest.raises(SystemExit) as exc:
        main(["--limit", "10"])
    assert exc.value.code != 0
    captured = capsys.readouterr()
    assert "gh CLI not found" in captured.err


def test_main_called_process_error(monkeypatch, capsys):
    import subprocess

    from prior_prs import main

    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "cmd", stderr="some error")

    monkeypatch.setattr(subprocess, "run", mock_run)
    with pytest.raises(SystemExit) as exc:
        main(["--limit", "10"])
    assert exc.value.code != 0
    captured = capsys.readouterr()
    assert "gh pr list failed: some error" in captured.err


def test_fetch_prs_not_list(monkeypatch):
    import subprocess

    from prior_prs import fetch_prs

    class FakeResult:
        stdout = '{"some": "dict"}'

    def mock_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert fetch_prs(10) == []


def test_fetch_prs_none_items(monkeypatch):
    import subprocess

    from prior_prs import fetch_prs

    class FakeResult:
        stdout = '[[1], null, {"a": 1}]'

    def mock_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert fetch_prs(10) == [{"a": 1}]


def test_label_names_invalid_format():
    from prior_prs import _label_names

    pr = {"labels": ["string", {"invalid": True}, {"name": "bug"}]}
    assert _label_names(pr) == "bug"


def test_compute_stats_open_merged_closed():
    from prior_prs import compute_stats

    prs = [
        {
            "author": {"login": "google-labs-jules"},
            "state": "unknown_state",
            "headRefName": "bolt-1",
        },
        {
            "author": {"login": "google-labs-jules"},
            "state": "closed",
            "headRefName": "testpilot-1",
            "labels": [{"name": "close:duplicate"}],
        },
    ]
    stats = compute_stats(prs)
    assert stats["lanes"]["bolt"]["open"] == 0
    assert stats["lanes"]["testpilot"]["closed"] == 1
    assert stats["lanes"]["testpilot"]["reasons"] == {"close:duplicate": 1}


def test_format_stats_empty_reasons():
    from prior_prs import format_stats

    stats = {
        "lanes": {"testpilot": {"open": 1, "merged": 0, "closed": 0, "reasons": {}}},
        "total": {"open": 1, "merged": 0, "closed": 0, "reasons": {}},
    }
    out = format_stats(stats)
    assert "close reasons:" not in out


def test_main_stats_valid(monkeypatch, capsys):
    import subprocess

    from prior_prs import main

    class FakeResult:
        stdout = '[{"author": {"login": "google-labs-jules"}, "state": "open", "headRefName": "testpilot-1"}]'

    def mock_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    main(["--stats"])
    captured = capsys.readouterr()
    assert "testpilot" in captured.out


def test_main_normal_valid(monkeypatch, capsys):
    import subprocess

    from prior_prs import main

    class FakeResult:
        stdout = (
            '[{"number": 123, "state": "open", "title": "test title", "labels": [{"name": "bug"}]}]'
        )

    def mock_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    main([])
    captured = capsys.readouterr()
    assert "#123   open  test title  [bug]" in captured.out


def test_accept_rate():
    from prior_prs import _accept_rate

    assert _accept_rate({"merged": 0, "closed": 0}) == "  n/a"
    assert _accept_rate({"merged": 1, "closed": 1}) == "   50%"


def test_fetch_prs_not_list_of_dict(monkeypatch):
    import subprocess

    from prior_prs import fetch_prs

    class FakeResult:
        stdout = '[1, "string", {"number": 1}]'

    def mock_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert fetch_prs(10) == [{"number": 1}]


def test_label_names_no_labels():
    from prior_prs import _label_names

    assert _label_names({}) == ""


def test_is_jules_pr_no_author():
    from prior_prs import is_jules_pr

    assert not is_jules_pr({})


def test_attribute_lane_unattributed():
    from prior_prs import attribute_lane

    assert attribute_lane({"headRefName": "random"}) == "unattributed"


def test_main_as_script(monkeypatch, capsys):
    import runpy
    import subprocess
    from unittest.mock import MagicMock

    monkeypatch.setattr("sys.argv", ["prior_prs.py", "--limit", "1"])

    mock_run = MagicMock()
    mock_run.return_value.stdout = "[]"
    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        runpy.run_module("prior_prs", run_name="__main__")
    except SystemExit as e:
        assert e.code == 0


def test_fetch_prs_no_gh(monkeypatch, capsys):
    import subprocess

    from prior_prs import main

    def mock_run(*args, **kwargs):
        raise FileNotFoundError("No such file or directory: 'gh'")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("sys.argv", ["prior_prs.py"])

    import pytest

    with pytest.raises(SystemExit):
        main()

    assert "gh CLI not found" in capsys.readouterr().err
