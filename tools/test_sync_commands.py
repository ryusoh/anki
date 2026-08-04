import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import sync_commands

SKILL_FIXTURE = """---
name: demo
description: Demo skill
argument-hint: "[branch]"
---

Body line with {{args}} placeholder.
"""


def _make_skills(tmp_path):
    skills = tmp_path / "skills"
    (skills / "demo").mkdir(parents=True)
    (skills / "demo" / "SKILL.md").write_text(SKILL_FIXTURE, encoding="utf-8")
    return skills


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_generate_writes_command_with_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_commands, "format_generated_commands", lambda d: None)
    skills = _make_skills(tmp_path)
    out = tmp_path / "commands"
    sync_commands.generate(str(skills), str(out))
    content = _read(out / "demo.md")
    assert "description: Demo skill" in content
    assert 'argument-hint: "[branch]"' in content
    assert "$ARGUMENTS placeholder." in content
    assert "{{args}}" not in content


def test_check_true_when_in_sync(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_commands, "format_generated_commands", lambda d: None)
    skills = _make_skills(tmp_path)
    commands = tmp_path / "commands"
    sync_commands.generate(str(skills), str(commands))
    assert sync_commands.check(str(skills), str(commands)) is True


def test_check_false_on_drift_and_does_not_mutate(tmp_path, monkeypatch):
    # The gate runs targets in parallel; a check that deletes/regenerates
    # .claude/commands races readers (markdownlint) and causes ENOENT flakes.
    monkeypatch.setattr(sync_commands, "format_generated_commands", lambda d: None)
    skills = _make_skills(tmp_path)
    commands = tmp_path / "commands"
    sync_commands.generate(str(skills), str(commands))
    drifted = commands / "demo.md"
    drifted.write_text("stale contents\n", encoding="utf-8")
    assert sync_commands.check(str(skills), str(commands)) is False
    assert _read(drifted) == "stale contents\n"


def test_check_false_when_commands_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_commands, "format_generated_commands", lambda d: None)
    skills = _make_skills(tmp_path)
    assert sync_commands.check(str(skills), str(tmp_path / "nope")) is False
