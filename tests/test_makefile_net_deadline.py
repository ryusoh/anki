"""Regression guard: precommit-fix's backgrounded network jobs must be deadlined.

Observed 2026-07-13 on a limited-bandwidth link: the backgrounded R2 upload
and public graph push trickled indefinitely (their clients' per-request
timeouts never fire while bytes still flow), and the recipe's `wait` hung
"forever" after the graph-local log. These tests pin the fix: every
backgrounded NETWORK job is wrapped in tools/run_with_deadline.py with the
NET_DEADLINE cap, so a stalled upload turns into exit 124 → BG_FAIL → a loud
non-zero exit instead of a hang. graph-local stays unwrapped on purpose — it
is local compute and must not be killed by a network deadline.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"

NETWORK_JOB_PIDS = {"BG_R2_PID": "fetch-r2-skip-fetch", "BG_GRAPHPUSH_PID": "graph-push"}


def _precommit_fix_recipe() -> str:
    match = re.search(r"^precommit-fix:.*\n((?:\t.*\n)+)", MAKEFILE.read_text(), re.M)
    assert match, "precommit-fix recipe not found in Makefile"
    return match.group(1)


def test_net_deadline_variable_is_defined_and_overridable():
    assert re.search(r"^NET_DEADLINE \?=", MAKEFILE.read_text(), re.M), (
        "NET_DEADLINE ?= default missing from Makefile — the network-job "
        "deadline must exist and stay overridable per invocation"
    )


def test_backgrounded_network_jobs_run_under_the_deadline_wrapper():
    recipe = _precommit_fix_recipe()
    for pid_var, target in NETWORK_JOB_PIDS.items():
        launches = [line for line in recipe.splitlines() if f"& {pid_var}=" in line]
        assert launches, f"backgrounded launch for {target} ({pid_var}) not found"
        for line in launches:
            assert "run_with_deadline.py" in line and "$(NET_DEADLINE)" in line, (
                f"backgrounded network job `{target}` is not wrapped in "
                f"tools/run_with_deadline.py --seconds $(NET_DEADLINE) — on a "
                f"limited uplink it can trickle for hours and the recipe's "
                f"`wait` hangs forever: {line.strip()!r}"
            )


def test_local_graph_export_is_not_deadlined():
    recipe = _precommit_fix_recipe()
    launches = [line for line in recipe.splitlines() if "& BG_GRAPHLOCAL_PID=" in line]
    assert launches, "backgrounded graph-local launch not found"
    for line in launches:
        assert "run_with_deadline.py" not in line, (
            "graph-local is local compute — a network deadline would kill "
            "legitimate long exports"
        )
