import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_rank


def _write_py(path, files):
    """files: {relpath: (num_statements, percent_covered)}."""
    data = {
        "files": {
            rel: {"summary": {"num_statements": stmts, "percent_covered": pct}}
            for rel, (stmts, pct) in files.items()
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_js(path, files):
    """files: {relpath: (total_statements, pct)}."""
    data = {
        rel: {"statements": {"total": stmts, "pct": pct}} for rel, (stmts, pct) in files.items()
    }
    data["total"] = {"statements": {"total": 0, "pct": 0}}
    path.write_text(json.dumps(data), encoding="utf-8")


def test_uncovered_property():
    # 100 statements at 30% covered => 70 uncovered.
    fc = coverage_rank.FileCoverage("a.js", 30.0, 100, "js")
    assert fc.uncovered == 70.0
    # A fully covered file has zero effort remaining.
    assert coverage_rank.FileCoverage("b.js", 100.0, 50, "js").uncovered == 0.0


def test_absolute_paths_are_relativized(capsys, tmp_path):
    # coverage.py emits absolute paths; they must be reported repo-root-relative.
    abs_path = os.path.join(coverage_rank.REPO_ROOT, "pkg", "mod.py")
    py = tmp_path / "py.json"
    _write_py(py, {abs_path: (10, 50.0)})
    coverage_rank.main(["--lang", "py", "--py-json", str(py)])
    out = capsys.readouterr().out
    assert "pkg/mod.py" in out
    assert coverage_rank.REPO_ROOT not in out


def _run(capsys, tmp_path, files_py, *extra):
    py = tmp_path / "py.json"
    _write_py(py, files_py)
    rc = coverage_rank.main(["--lang", "py", "--py-json", str(py), *extra])
    assert rc == 0
    out = capsys.readouterr().out
    # Return the file column in printed order, skipping the header row.
    order = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1].endswith(".py"):
            order.append(parts[1])
    return order, out


def test_quickwin_orders_by_fewest_uncovered_first(capsys, tmp_path):
    files = {
        "big.py": (100, 0.0),  # 100 uncovered
        "near.py": (100, 99.0),  # 1 uncovered
        "mid.py": (100, 90.0),  # 10 uncovered
    }
    order, _ = _run(capsys, tmp_path, files)  # quickwin is the default
    assert order == ["near.py", "mid.py", "big.py"]


def test_surface_orders_by_most_uncovered_first(capsys, tmp_path):
    files = {
        "big.py": (100, 0.0),
        "near.py": (100, 99.0),
        "mid.py": (100, 90.0),
    }
    order, _ = _run(capsys, tmp_path, files, "--order", "surface")
    assert order == ["big.py", "mid.py", "near.py"]


def test_coverage_order_by_lowest_percent(capsys, tmp_path):
    # A tiny 0% file beats a huge 90% file on percent, though it has less surface.
    files = {"tiny.py": (3, 0.0), "huge.py": (1000, 90.0)}
    order, _ = _run(capsys, tmp_path, files, "--order", "coverage")
    assert order == ["tiny.py", "huge.py"]


def test_threshold_filters_fully_covered(capsys, tmp_path):
    files = {"done.py": (10, 100.0), "todo.py": (10, 50.0)}
    order, out = _run(capsys, tmp_path, files)
    assert order == ["todo.py"]
    assert "done.py" not in out


def test_limit_truncates(capsys, tmp_path):
    files = {f"f{i}.py": (10, float(i)) for i in range(5)}
    order, _ = _run(capsys, tmp_path, files, "--limit", "2")
    assert len(order) == 2


def test_no_targets_message(capsys, tmp_path):
    files = {"done.py": (10, 100.0)}
    py = tmp_path / "py.json"
    _write_py(py, files)
    coverage_rank.main(["--lang", "py", "--py-json", str(py)])
    assert "Nothing to target" in capsys.readouterr().out


def test_excluded_and_zero_statement_files_skipped(capsys, tmp_path):
    files = {
        "real.py": (10, 50.0),
        "_vendor/dep.py": (10, 0.0),  # excluded path
        "empty.py": (0, 0.0),  # no measurable statements
    }
    order, _ = _run(capsys, tmp_path, files)
    assert order == ["real.py"]


def test_missing_coverage_files_note_and_skip(capsys, tmp_path):
    # Neither artifact exists -> a note per language on stderr, nothing to target.
    rc = coverage_rank.main(
        [
            "--py-json",
            str(tmp_path / "absent-py.json"),
            "--js-summary",
            str(tmp_path / "absent-js.json"),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "no Python coverage" in captured.err
    assert "no JS coverage" in captured.err
    assert "Nothing to target" in captured.out


def test_js_skips_total_excluded_and_zero_statement(capsys, tmp_path):
    js = tmp_path / "js.json"
    _write_js(
        js,
        {
            "real.js": (10, 50.0),
            "node_modules/dep.js": (10, 0.0),  # excluded path
            "empty.js": (0, 0.0),  # no measurable statements
        },
    )
    rc = coverage_rank.main(["--lang", "js", "--js-summary", str(js)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "real.js" in out
    assert "node_modules/dep.js" not in out
    assert "empty.js" not in out


def test_js_and_py_merge_and_rank_together(capsys, tmp_path):
    py = tmp_path / "py.json"
    js = tmp_path / "js.json"
    _write_py(py, {"a.py": (100, 90.0)})  # 10 uncovered
    _write_js(js, {"b.js": (100, 98.0)})  # 2 uncovered -> ranks first under quickwin
    rc = coverage_rank.main(["--py-json", str(py), "--js-summary", str(js)])
    assert rc == 0
    out = capsys.readouterr().out
    a_idx, b_idx = out.index("a.py"), out.index("b.js")
    assert b_idx < a_idx


def test_main_raises_system_exit(capsys, tmp_path):
    import runpy
    from unittest.mock import patch

    import pytest

    with patch('sys.argv', ['coverage_rank.py', '--lang', 'unknown']):
        with pytest.raises(SystemExit) as exc:
            runpy.run_module('tools.coverage_rank', run_name='__main__')
        assert exc.value.code != 0
