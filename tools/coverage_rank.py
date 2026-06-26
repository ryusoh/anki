#!/usr/bin/env python3
"""Rank source files by test coverage, lowest first.

Mirrors the fund repo's ``scripts.agents.coverage_rank`` so the Testpilot routine
can pick the genuinely least-covered files deterministically instead of eyeballing a
truncated terminal table (and re-testing files already at 100%).

It reads coverage artifacts produced by ``make coverage-rank``:

* Python  -> ``coverage/py.json``  (``python3 -m coverage json``)
* JS      -> ``coverage/js/coverage-summary.json`` (c8 ``json-summary`` reporter)

Files already at/above the threshold (default 100%) and files with no measurable
statements are skipped. Usage::

    python3 tools/coverage_rank.py --limit 5
    python3 tools/coverage_rank.py --lang py --limit 10 --threshold 95
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PY_JSON = os.path.join("coverage", "py.json")
DEFAULT_JS_SUMMARY = os.path.join("coverage", "js", "coverage-summary.json")

# Defensive excludes; the coverage tooling already drops most of these, but a stray
# vendored or generated file should never be offered as a target.
EXCLUDE_SUBSTRINGS = ("/_vendor/", "/libaddon/", "/node_modules/", "/vendor/")


@dataclass
class FileCoverage:
    path: str
    percent: float
    statements: int
    lang: str


def _rel(path: str) -> str:
    """Return a repo-root-relative, forward-slash path."""
    if os.path.isabs(path):
        path = os.path.relpath(path, REPO_ROOT)
    return path.replace(os.sep, "/")


def _excluded(path: str) -> bool:
    probe = "/" + path
    return any(token in probe for token in EXCLUDE_SUBSTRINGS)


def load_python(py_json: str) -> list[FileCoverage]:
    if not os.path.exists(py_json):
        print(f"note: no Python coverage at {py_json} (run `make coverage-rank`)", file=sys.stderr)
        return []
    with open(py_json, encoding="utf-8") as fh:
        data = json.load(fh)
    out: list[FileCoverage] = []
    for raw_path, entry in data.get("files", {}).items():
        summary = entry.get("summary", {})
        statements = int(summary.get("num_statements", 0))
        if statements <= 0:
            continue
        path = _rel(raw_path)
        if _excluded(path):
            continue
        out.append(FileCoverage(path, float(summary.get("percent_covered", 0.0)), statements, "py"))
    return out


def load_js(js_summary: str) -> list[FileCoverage]:
    if not os.path.exists(js_summary):
        print(f"note: no JS coverage at {js_summary} (run `make coverage-rank`)", file=sys.stderr)
        return []
    with open(js_summary, encoding="utf-8") as fh:
        data = json.load(fh)
    out: list[FileCoverage] = []
    for raw_path, entry in data.items():
        if raw_path == "total" or not isinstance(entry, dict):
            continue
        statements = int(entry.get("statements", {}).get("total", 0))
        if statements <= 0:
            continue
        path = _rel(raw_path)
        if _excluded(path):
            continue
        percent = float(entry.get("statements", {}).get("pct", 0.0))
        out.append(FileCoverage(path, percent, statements, "js"))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank source files by coverage, lowest first.")
    parser.add_argument("--lang", choices=("py", "js", "all"), default="all")
    parser.add_argument("--limit", type=int, default=0, help="Show only the N lowest (0 = all).")
    parser.add_argument(
        "--threshold",
        type=float,
        default=100.0,
        help="Skip files at or above this coverage percent (default 100).",
    )
    parser.add_argument("--py-json", default=DEFAULT_PY_JSON)
    parser.add_argument("--js-summary", default=DEFAULT_JS_SUMMARY)
    args = parser.parse_args(argv)

    files: list[FileCoverage] = []
    if args.lang in ("py", "all"):
        files += load_python(
            os.path.join(REPO_ROOT, args.py_json)
            if not os.path.isabs(args.py_json)
            else args.py_json
        )
    if args.lang in ("js", "all"):
        files += load_js(
            os.path.join(REPO_ROOT, args.js_summary)
            if not os.path.isabs(args.js_summary)
            else args.js_summary
        )

    ranked = sorted(
        (f for f in files if f.percent < args.threshold),
        key=lambda f: (f.percent, f.path),
    )
    if args.limit > 0:
        ranked = ranked[: args.limit]

    if not ranked:
        print("No files below the coverage threshold. Nothing to target.")
        return 0

    width = max(len(f.path) for f in ranked)
    print(f"{'COVERAGE':>9}  {'FILE':<{width}}  STMTS  LANG")
    for f in ranked:
        print(f"{f.percent:8.1f}%  {f.path:<{width}}  {f.statements:>5}  {f.lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
