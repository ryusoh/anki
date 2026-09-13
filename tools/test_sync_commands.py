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


def test_ensure_skills_symlink_creates_link(tmp_path):
    link_path = tmp_path / ".claude" / "skills"
    sync_commands.ensure_skills_symlink(str(link_path))
    assert link_path.is_symlink()
    assert os.readlink(str(link_path)) == os.path.join("..", ".agents", "skills")
    # Idempotent call
    sync_commands.ensure_skills_symlink(str(link_path))
    assert link_path.is_symlink()

from sync_commands import check, format_generated_commands, generate, parse_markdown, ensure_skills_symlink, main
import pytest

def test_parse_markdown_no_frontmatter():
    yaml_data, body = parse_markdown("just body")
    assert yaml_data == {}
    assert body == "just body"

def test_parse_markdown_with_frontmatter():
    yaml_data, body = parse_markdown("---\ndescription: test\n---\nbody text")
    assert yaml_data == {"description": "test"}
    assert body == "body text"

def test_generate_replaces_args(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: my desc\nargument-hint: \"[hint]\"\n---\nbody {{args}}")

    target_dir = tmp_path / "commands"
    generate(str(skills_dir), str(target_dir))

    command_file = target_dir / "my_skill.md"
    assert command_file.exists()
    content = command_file.read_text()
    assert "description: my desc" in content
    assert "argument-hint: \"[hint]\"" in content
    assert "body $ARGUMENTS" in content

def test_generate_handles_quotes_in_arg_hint(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nargument-hint: '\"<val>\"'\n---\nbody")

    target_dir = tmp_path / "commands"
    generate(str(skills_dir), str(target_dir))

    command_file = target_dir / "my_skill.md"
    content = command_file.read_text()
    assert "argument-hint: '\"<val>\"'" in content

def test_generate_cleans_target_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    target_dir = tmp_path / "commands"
    target_dir.mkdir()
    (target_dir / "stale.md").write_text("old")

    generate(str(skills_dir), str(target_dir))
    assert not (target_dir / "stale.md").exists()

def test_check_returns_false_if_target_missing(tmp_path):
    assert not check(str(tmp_path / "skills"), str(tmp_path / "missing"))

def test_check_returns_false_on_drift(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: my desc\n---\nbody")

    target_dir = tmp_path / "commands"
    target_dir.mkdir()
    (target_dir / "my_skill.md").write_text("wrong content")

    assert not check(str(skills_dir), str(target_dir))

def test_check_returns_true_on_match(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: my desc\n---\nbody")

    target_dir = tmp_path / "commands"
    generate(str(skills_dir), str(target_dir))

    assert check(str(skills_dir), str(target_dir))

def test_format_generated_commands_empty_dir(tmp_path):
    target_dir = tmp_path / "commands"
    target_dir.mkdir()
    format_generated_commands(str(target_dir)) # should not crash

def test_format_generated_commands_no_npx(tmp_path, monkeypatch, capsys):
    target_dir = tmp_path / "commands"
    target_dir.mkdir()
    (target_dir / "test.md").write_text("test")

    import subprocess
    def mock_run(*args, **kwargs):
        raise FileNotFoundError("npx not found")
    monkeypatch.setattr(subprocess, "run", mock_run)

    format_generated_commands(str(target_dir))
    assert "Warning: npx not found" in capsys.readouterr().out

def test_format_generated_commands_prettier_fails(tmp_path, monkeypatch, capsys):
    target_dir = tmp_path / "commands"
    target_dir.mkdir()
    (target_dir / "test.md").write_text("test")

    import subprocess
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "cmd", stderr="syntax error")
    monkeypatch.setattr(subprocess, "run", mock_run)

    format_generated_commands(str(target_dir))
    assert "Warning: prettier failed" in capsys.readouterr().out

def test_ensure_skills_symlink(tmp_path):
    target_link = tmp_path / "claude" / "skills"
    ensure_skills_symlink(str(target_link))
    assert target_link.is_symlink()
    assert os.readlink(str(target_link)) == "../.agents/skills"

def test_ensure_skills_symlink_exists(tmp_path):
    target_link = tmp_path / "claude" / "skills"
    target_link.parent.mkdir(parents=True)
    target_link.write_text("dummy")
    ensure_skills_symlink(str(target_link))
    assert target_link.read_text() == "dummy"

def test_main_generate(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["sync_commands.py"])

    def mock_generate(s, t): print("mock_generate")
    def mock_symlink(): print("mock_symlink")

    import sync_commands
    monkeypatch.setattr(sync_commands, "generate", mock_generate)
    monkeypatch.setattr(sync_commands, "ensure_skills_symlink", mock_symlink)

    main()
    out = capsys.readouterr().out
    assert "mock_generate" in out
    assert "mock_symlink" in out
    assert "Successfully synchronized" in out

def test_main_check_pass(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["sync_commands.py", "--check"])

    def mock_check(s, t): return True
    import sync_commands
    monkeypatch.setattr(sync_commands, "check", mock_check)

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    assert "sync-check: .claude/commands is up to date" in capsys.readouterr().out

def test_main_check_fail(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["sync_commands.py", "--check"])

    def mock_check(s, t): return False
    import sync_commands
    monkeypatch.setattr(sync_commands, "check", mock_check)

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    assert "sync-check FAIL" in capsys.readouterr().out
