"""Guardrail test ensuring critical dependencies in requirements.txt cannot be
accidentally removed by automated cleanup routines (e.g. Janitor).

Pins packages that Anki bundles at runtime but which standalone pytest / CI
runners require (such as beautifulsoup4 for bs4 imports in auto_mathjax and
auto_wiktionary), preventing "ghost green" local runs from turning CI red.
"""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"

# Critical dependencies required outside Anki's bundled desktop binary
CRITICAL_DEPENDENCIES = {
    "beautifulsoup4": {"bs4"},
    "jsonschema": {"jsonschema"},
    "networkx": {"networkx"},
    "scipy": {"scipy"},
    "edge-tts": {"edge_tts"},
    "pytest": {"pytest"},
    "pytest-cov": {"pytest_cov"},
}


def _parse_declared_packages(req_path: Path) -> dict[str, str]:
    """Return dict of normalized package name -> raw declaration line."""
    packages = {}
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        pkg_name = re.split(r"[<>=!~]", line)[0].strip().lower()
        packages[pkg_name] = line
    return packages


def test_requirements_file_exists():
    assert REQUIREMENTS_FILE.is_file(), "requirements.txt must exist at repo root"


def test_critical_dependencies_declared():
    declared = _parse_declared_packages(REQUIREMENTS_FILE)
    for pkg in CRITICAL_DEPENDENCIES:
        assert pkg in declared, (
            f"'{pkg}' must remain declared in requirements.txt. "
            f"It provides top-level module(s) {CRITICAL_DEPENDENCIES[pkg]} required for "
            f"standalone pytest/CI runs. Do not remove it as dead code!"
        )


def test_bs4_usage_in_addons_is_backed_by_beautifulsoup4():
    """Verify that any add-on importing bs4 has beautifulsoup4 declared."""
    declared = _parse_declared_packages(REQUIREMENTS_FILE)
    assert (
        "beautifulsoup4" in declared
    ), "beautifulsoup4 is missing from requirements.txt despite active bs4 imports"

    bs4_users = []
    addon_dirs = [
        REPO_ROOT / "auto_mathjax",
        REPO_ROOT / "auto_wiktionary",
        REPO_ROOT / "awesome_tts",
    ]
    for addon_dir in addon_dirs:
        for py_file in addon_dir.rglob("*.py"):
            if "_vendor" in py_file.parts or "libaddon" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if "bs4" in text:
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, ast.ImportFrom)
                            and node.module
                            and node.module.split(".")[0] == "bs4"
                        ):
                            bs4_users.append(str(py_file.relative_to(REPO_ROOT)))
                            break
                        elif isinstance(node, ast.Import):
                            if any(alias.name.split(".")[0] == "bs4" for alias in node.names):
                                bs4_users.append(str(py_file.relative_to(REPO_ROOT)))
                                break
                except SyntaxError:
                    pass

    assert bs4_users, "Expected active bs4 imports in add-ons"
