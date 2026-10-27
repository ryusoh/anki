"""Tests for tools/check_bot_pr_hygiene.py — the Jules bot PR hygiene gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_bot_pr_hygiene import _is_stray_artifact, find_violations, main

BOT_NAME = 'google-labs-jules[bot]'
BOT_EMAIL = '161369871+google-labs-jules[bot]@users.noreply.github.com'


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=repo, capture_output=True, check=True)


def _commit(repo: Path, message: str, bot: bool = True, allow_empty: bool = False) -> None:
    name = BOT_NAME if bot else 'Dev'
    email = BOT_EMAIL if bot else 'dev@example.com'
    args = ['-c', f'user.email={email}', '-c', f'user.name={name}', 'commit', '-m', message]
    if allow_empty:
        args.append('--allow-empty')
    _git(repo, *args)


def _write_and_commit(repo: Path, path: str, content: str, message: str, bot: bool = True) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _git(repo, 'add', path)
    _commit(repo, message, bot=bot)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A git repo with one human commit on main and a bot branch checked out."""
    _git(tmp_path, 'init', '-b', 'main')
    (tmp_path / 'README.md').write_text('x\n')
    _git(tmp_path, 'add', 'README.md')
    _commit(tmp_path, 'init', bot=False)
    _git(tmp_path, 'checkout', '-b', 'bot-branch')
    return tmp_path


def test_clean_bot_test_addition_passes(repo: Path) -> None:
    _write_and_commit(
        repo, 'addon/tests/test_new.py', 'def test_x():\n    assert True\n', 'add tests'
    )
    assert find_violations(repo, 'main') == []


def test_bot_test_deletion_flagged(repo: Path) -> None:
    _write_and_commit(
        repo, 'addon/tests/test_new.py', 'def test_x():\n    assert True\n', 'add tests'
    )
    _write_and_commit(repo, 'addon/tests/test_new.py', 'def test_x():\n    pass\n', 'rewrite tests')
    violations = find_violations(repo, 'main')
    assert any('test deletion' in v and 'addon/tests/test_new.py' in v for v in violations)


def test_bot_root_test_file_deletion_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'tools/test_widget.py', 'a = 1\nb = 2\n', 'add tool test')
    _write_and_commit(repo, 'tools/test_widget.py', 'a = 1\n', 'trim tool test')
    violations = find_violations(repo, 'main')
    assert any('test deletion' in v for v in violations)


def test_bot_production_deletion_not_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'addon/core.py', 'a = 1\nb = 2\n', 'add prod code')
    _write_and_commit(repo, 'addon/core.py', 'a = 1\n', 'trim prod code')
    assert find_violations(repo, 'main') == []


def test_bot_lockfile_deletion_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'package-lock.json', '{"name": "anki"}\n', 'add lockfile')
    (repo / 'package-lock.json').unlink()
    _git(repo, 'add', 'package-lock.json')
    _commit(repo, 'drop lockfile')
    violations = find_violations(repo, 'main')
    assert any('lockfile deletion' in v for v in violations)


def test_bot_lockfile_modification_not_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'package-lock.json', '{"name": "anki"}\n', 'add lockfile')
    _write_and_commit(repo, 'package-lock.json', '{"name": "anki", "v": 2}\n', 'bump lockfile')
    assert find_violations(repo, 'main') == []


def test_human_lockfile_deletion_not_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'package-lock.json', '{"name": "anki"}\n', 'add lockfile')
    (repo / 'package-lock.json').unlink()
    _git(repo, 'add', 'package-lock.json')
    _commit(repo, 'human drops lockfile', bot=False)
    assert find_violations(repo, 'main') == []


def test_bot_empty_commit_flagged(repo: Path) -> None:
    _commit(repo, 'responding to feedback', allow_empty=True)
    violations = find_violations(repo, 'main')
    assert any('empty commit' in v for v in violations)


def test_bot_zero_content_file_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'dummy_file.txt', '', 'add placeholder')
    violations = find_violations(repo, 'main')
    assert any('placeholder' in v and 'dummy_file.txt' in v for v in violations)


def test_bot_stray_artifact_flagged(repo: Path) -> None:
    _write_and_commit(repo, 'pr_body.txt', 'Some PR body text\n', 'perf(js): test')
    violations = find_violations(repo, 'main')
    assert any('stray artifact' in v and 'pr_body.txt' in v for v in violations)


@pytest.mark.parametrize(
    'path',
    [
        'verify_output.txt',
        'output.txt',
        'docs/pytest_output.txt',
        'eslint_out.json',
        'eslint_warn_out.json',
        'debug.log',
        'logs/run.LOG',
        'pr_title.txt',
        'commit_message.txt',
        'commit-message.txt',
        'commit_msg.txt',
        'patch.diff',
        'diff.patch',
        'patch_prior.py',
        'fix_typo.cjs',
        'fix.py',
        'pnpm-lock.yaml',
        'yarn.lock',
        'frontend/bun.lockb',
    ],
)
def test_bot_stray_scratch_artifacts_flagged(repo: Path, path: str) -> None:
    _write_and_commit(repo, path, 'scratch content\n', 'chore: verification run')
    violations = find_violations(repo, 'main')
    assert any('stray artifact' in v and path in v for v in violations)


@pytest.mark.parametrize(
    'path',
    [
        'output.md',
        'js/output.js',
        'logs.txt',
        'data/output_dir/result.txt',
        'tools/fix_jp_pinyin_front.py',
        'package-lock.json',
    ],
)
def test_bot_non_stray_output_names_pass(repo: Path, path: str) -> None:
    _write_and_commit(repo, path, 'real content\n', 'feat: add module')
    assert find_violations(repo, 'main') == []


def test_bot_suppressions_addition_flagged(repo: Path) -> None:
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{"js/foo.js": {"complexity": {"count": 1}}}\n',
        'refactor(js): add suppression',
    )
    violations = find_violations(repo, 'main')
    assert any('complexity ratchet violation' in v and 'added suppression' in v for v in violations)


def test_bot_suppressions_increase_flagged(repo: Path) -> None:
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{"js/foo.js": {"complexity": {"count": 1}}}\n',
        'init suppressions',
        bot=False,
    )
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{"js/foo.js": {"complexity": {"count": 2}}}\n',
        'refactor(js): increase count',
        bot=True,
    )
    violations = find_violations(repo, 'main')
    assert any(
        'complexity ratchet violation' in v and 'increased suppression count' in v
        for v in violations
    )


def test_bot_suppressions_prune_allowed(repo: Path) -> None:
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{"js/foo.js": {"complexity": {"count": 1}}}\n',
        'init suppressions',
        bot=False,
    )
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{}\n',
        'refactor(js): cut complexity',
        bot=True,
    )
    assert find_violations(repo, 'main') == []


def test_bot_non_refactor_suppression_touch_flagged(repo: Path) -> None:
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{"js/foo.js": {"complexity": {"count": 1}}}\n',
        'init suppressions',
        bot=False,
    )
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{}\n',
        'perf(js): optimize loops',
        bot=True,
    )
    violations = find_violations(repo, 'main')
    assert any('lane violation' in v and 'refactor' in v for v in violations)


def test_human_test_deletion_ignored(repo: Path) -> None:
    _write_and_commit(repo, 'addon/tests/test_new.py', 'a = 1\nb = 2\n', 'add tests', bot=False)
    _write_and_commit(repo, 'addon/tests/test_new.py', 'a = 1\n', 'rewrite tests', bot=False)
    _write_and_commit(repo, 'pr_body.txt', 'notes\n', 'add notes', bot=False)
    _write_and_commit(
        repo,
        'eslint-suppressions.json',
        '{"js/foo.js": {"complexity": {"count": 1}}}\n',
        'human suppression',
        bot=False,
    )
    _commit(repo, 'human empty commit', bot=False, allow_empty=True)
    assert find_violations(repo, 'main') == []


def test_main_returns_1_with_violations(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _commit(repo, 'empty', allow_empty=True)
    assert main(['--repo', str(repo), '--base', 'main']) == 1
    assert 'empty commit' in capsys.readouterr().out


def test_main_returns_0_when_clean(repo: Path) -> None:
    _write_and_commit(repo, 'addon/tests/test_new.py', 'x = 1\n', 'add tests')
    assert main(['--repo', str(repo), '--base', 'main']) == 0


def test_main_returns_0_on_empty_range(repo: Path) -> None:
    _git(repo, 'checkout', 'main')
    assert main(['--repo', str(repo), '--base', 'main']) == 0


def test_main_returns_2_on_missing_base(repo: Path) -> None:
    assert main(['--repo', str(repo), '--base', 'no-such-ref']) == 2


def test_all_stray_artifact_patterns_are_gitignored() -> None:
    """Ensure every artifact pattern rejected by check_bot_pr_hygiene is covered by .gitignore.

    This prevents drift between the hygiene gate and git's staging layer, ensuring
    agents mechanically cannot stage forbidden scratch or verification files.
    """
    repo_root = Path(__file__).resolve().parent.parent
    sample_artifacts = [
        'pr_body.txt',
        'pr_description.txt',
        'pr_title.txt',
        'commit_message.txt',
        'commit-message.txt',
        'commit_msg.txt',
        'precommit.log',
        'verify.log',
        'temp_notes.tmp',
        'scratch.scratch',
        'test.swp',
        'output.txt',
        'verify_output.txt',
        'eslint_out.json',
        'test_output.json',
        'all_errors.txt',
        'tsc_errors.txt',
        'all_warnings.txt',
        'patch.diff',
        'diff.patch',
        'test_analyze_gaps.py.orig',
        'merge_conflict.rej',
        'notes.bak',
        'pnpm-lock.yaml',
        'yarn.lock',
        'bun.lock',
        'bun.lockb',
    ]
    for path in sample_artifacts:
        assert _is_stray_artifact(path), f'{path} should be detected as stray'
        res = subprocess.run(['git', 'check-ignore', '-q', path], cwd=repo_root)
        assert res.returncode == 0, f'{path} is a stray artifact but not covered by .gitignore'


def test_bot_inline_complexity_disable_flagged(repo: Path) -> None:
    _write_and_commit(
        repo,
        'js/foo.js',
        'function f() {\n  return 1;\n}\n',
        'feat(js): add foo',
    )
    _write_and_commit(
        repo,
        'js/foo.js',
        '// eslint-disable-next-line complexity\nfunction f() {\n  return 1;\n}\n',
        'fix(js): silence complexity',
    )
    violations = find_violations(repo, 'main')
    assert any('inline suppression' in v for v in violations)


def test_bot_other_inline_disable_allowed(repo: Path) -> None:
    _write_and_commit(
        repo,
        'js/foo.js',
        '// eslint-disable-next-line no-undef\nfunction f() {\n  return 1;\n}\n',
        'fix(js): silence no-undef',
    )
    assert find_violations(repo, 'main') == []


def test_human_inline_complexity_disable_ignored(repo: Path) -> None:
    _write_and_commit(
        repo,
        'js/foo.js',
        '// eslint-disable-next-line complexity\nfunction f() {\n  return 1;\n}\n',
        'fix(js): silence complexity',
        bot=False,
    )
    assert find_violations(repo, 'main') == []
