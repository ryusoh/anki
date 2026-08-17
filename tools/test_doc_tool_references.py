"""Verify that tool and script files referenced in agent docs and skills exist on disk.

Ensures automated cleanup bots (e.g. Janitor) and refactors never delete
standalone CLI tools or helper scripts that are referenced by agent workflows,
skills, or documentation.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Regex pattern to extract tools/, scripts/, or bin/ script paths from markdown text
SCRIPT_REF_PATTERN = re.compile(
    r"(?:python3\s+|node\s+|`|\b)((?:tools|scripts|bin)/[a-zA-Z0-9_\-/\.]+\.(?:py|sh|c|mjs|cjs))"
)


def _collect_markdown_files() -> list[Path]:
    """Collect AGENTS.md, .jules persona docs, and agent skill definitions."""
    md_files = [REPO_ROOT / "AGENTS.md"]

    jules_dir = REPO_ROOT / ".jules"
    if jules_dir.is_dir():
        md_files.extend(jules_dir.glob("*.md"))

    skills_dir = REPO_ROOT / ".agents" / "skills"
    if skills_dir.is_dir():
        md_files.extend(skills_dir.rglob("*.md"))

    return [f for f in md_files if f.is_file()]


def test_documented_tool_scripts_exist():
    """All scripts in tools/, scripts/, or bin/ referenced by agent docs must exist on disk."""
    md_files = _collect_markdown_files()
    assert md_files, "No markdown documentation files found to validate."

    missing_refs = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        matches = SCRIPT_REF_PATTERN.findall(content)

        for match in matches:
            script_path = REPO_ROOT / match
            if not script_path.exists():
                missing_refs.append(
                    f"{md_file.relative_to(REPO_ROOT)} references missing script: {match}"
                )

    assert (
        not missing_refs
    ), f"Found {len(missing_refs)} missing script reference(s) in documentation:\n" + "\n".join(
        missing_refs
    )


def test_core_infrastructure_tools_exist():
    """Explicitly verify critical infrastructure tools exist."""
    core_tools = [
        "tools/gate_guard.py",
        "tools/check_thinking_comments.py",
        "tools/sync_commands.py",
        "tools/coverage_rank.py",
        "tools/dump_field.py",
        "tools/node_test_runner.mjs",
        "tools/security_audit.py",
        "tools/git_push_retry.py",
        "tools/run_with_deadline.py",
    ]

    missing = [tool for tool in core_tools if not (REPO_ROOT / tool).is_file()]
    assert not missing, f"Core infrastructure tools missing: {missing}"
