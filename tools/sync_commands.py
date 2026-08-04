"""Sync skills from .agents/skills to .claude/commands.

`.agents/skills/<name>/SKILL.md` is the canonical source — the open Agent
Skills format, read natively by Antigravity, Kimi, and Codex.
`.claude/commands/*.md` is generated from it for Claude Code. Edit the SKILL.md
files, never the generated commands; `make sync-check` fails in the gate if the
generated copy is stale. The check mode regenerates into a temp dir and diffs —
the precommit gate runs targets in parallel, so a check that deleted and
rebuilt `.claude/commands/` in place raced concurrent readers (markdownlint
hit ENOENT on a file it had just been handed) and flaked CI.
"""

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Tuple

# Constants
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(WORKSPACE_ROOT, ".agents", "skills")
COMMANDS_DIR = os.path.join(WORKSPACE_ROOT, ".claude", "commands")


def parse_markdown(content: str) -> Tuple[Dict[str, str], str]:
    """Parse SKILL.md frontmatter and body."""
    yaml_data: Dict[str, str] = {}
    body = ""

    # Split by frontmatter delimiters
    parts = content.split("---", 2)
    if len(parts) >= 3:
        yaml_block = parts[1]
        body = parts[2].strip()
        for line in yaml_block.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                yaml_data[key.strip()] = val.strip().strip('"').strip("'")
    else:
        body = content.strip()

    return yaml_data, body


def generate(skills_dir: str, target_dir: str) -> None:
    """Regenerate commands from the canonical .agents/skills sources."""
    # Ensure target directory exists and is clean
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(skills_dir):
        for entry in sorted(os.listdir(skills_dir)):
            skill_dir = os.path.join(skills_dir, entry)
            skill_md_path = os.path.join(skill_dir, "SKILL.md")
            if not os.path.isdir(skill_dir) or not os.path.exists(skill_md_path):
                continue

            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            yaml_data, body = parse_markdown(content)
            description = yaml_data.get("description", "")
            arg_hint = yaml_data.get("argument-hint", "")

            # Agent Skills use {{args}} placeholders; Claude uses $ARGUMENTS.
            body = body.replace("{{args}}", "$ARGUMENTS")

            command_path = os.path.join(target_dir, f"{entry}.md")
            with open(command_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(f"description: {description}\n")
                if arg_hint:
                    # Quote as a YAML string: values often start with `[`/`<`,
                    # which a bare scalar would parse as an array/tag, not a string.
                    safe_hint = arg_hint.replace("\\", "\\\\").replace('"', '\\"')
                    f.write(f'argument-hint: "{safe_hint}"\n')
                f.write("---\n\n")
                f.write(body)
                f.write("\n")

    format_generated_commands(target_dir)


def check(skills_dir: str, commands_dir: str) -> bool:
    """True if commands_dir matches a fresh regeneration; never mutates it."""
    if not os.path.isdir(commands_dir):
        return False
    with tempfile.TemporaryDirectory() as tmp:
        generate(skills_dir, tmp)
        comparison = filecmp.dircmp(commands_dir, tmp)
        return not (comparison.left_only or comparison.right_only or comparison.diff_files)


def format_generated_commands(target_dir: str) -> None:
    """Format generated commands with prettier so output matches `make fmt`.

    Without this, the prettier pass in `make fmt` reformats the generated
    Markdown after it lands, so a fresh sync always shows phantom drift against
    the committed files. Mirror the Makefile's invocation (--ignore-path
    .gitignore) to keep sync idempotent. Degrade gracefully if prettier/npx is
    unavailable (script stays stdlib-only).
    """
    try:
        subprocess.run(
            ["npx", "prettier", "--write", "--ignore-path", ".gitignore", target_dir],
            cwd=WORKSPACE_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Warning: npx not found; skipping prettier formatting of generated commands.")
    except subprocess.CalledProcessError as exc:
        print(f"Warning: prettier failed on generated commands:\n{exc.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 0 if .claude/commands is up to date, 1 on drift (read-only)",
    )
    args = parser.parse_args()
    if args.check:
        if check(SKILLS_DIR, COMMANDS_DIR):
            print("sync-check: .claude/commands is up to date")
            sys.exit(0)
        print(
            "sync-check FAIL: .claude/commands is stale — regenerate with "
            "python3 tools/sync_commands.py and commit the result."
        )
        sys.exit(1)
    generate(SKILLS_DIR, COMMANDS_DIR)
    print("Successfully synchronized Agent Skills to Claude commands.")


if __name__ == "__main__":
    main()
