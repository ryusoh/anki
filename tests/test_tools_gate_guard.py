import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.gate_guard import main, worktree_fingerprint


def init_git(repo):
    os.chdir(repo)
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    Path("init.txt").write_text("init")
    subprocess.run(["git", "add", "init.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "init"], check=True)


def test_gate_guard_snapshot(tmp_path):
    init_git(tmp_path)
    Path("test.txt").write_text("hello")
    subprocess.run(["git", "add", "test.txt"], check=True)

    with patch("sys.argv", ["gate_guard", "snapshot", "--repo", str(tmp_path)]):
        with patch("sys.stdout"):
            assert main() == 0


def test_gate_guard_check_unchanged(tmp_path):
    init_git(tmp_path)
    Path("test.txt").write_text("hello")
    subprocess.run(["git", "add", "test.txt"], check=True)

    fp = worktree_fingerprint(tmp_path)
    with patch("sys.argv", ["gate_guard", "check", fp, "--repo", str(tmp_path)]):
        with patch("sys.stderr"):
            assert main() == 1


def test_gate_guard_check_changed(tmp_path):
    init_git(tmp_path)
    Path("test.txt").write_text("hello")
    subprocess.run(["git", "add", "test.txt"], check=True)

    fp = worktree_fingerprint(tmp_path)
    Path("test.txt").write_text("world")

    with patch("sys.argv", ["gate_guard", "check", fp, "--repo", str(tmp_path)]):
        with patch("sys.stderr"):
            assert main() == 0


def test_gate_guard_git_not_found(tmp_path):
    os.chdir(tmp_path)

    with patch("tools.gate_guard.worktree_fingerprint", side_effect=FileNotFoundError):
        with patch("sys.argv", ["gate_guard", "snapshot"]):
            with pytest.raises(SystemExit):
                main()


def test_gate_guard_git_error(tmp_path):
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True)

    with patch("sys.argv", ["gate_guard", "snapshot"]):
        with patch(
            "tools.gate_guard._git",
            side_effect=subprocess.CalledProcessError(1, ["git"], b"", b"error msg"),
        ):
            with pytest.raises(SystemExit):
                main()


def test_gate_guard_untracked_file_error(tmp_path):
    init_git(tmp_path)
    Path("untracked.txt").write_text("hello")

    with patch("pathlib.Path.read_bytes", side_effect=OSError):
        fp = worktree_fingerprint(tmp_path)
        assert isinstance(fp, str)
        assert len(fp) == 64


def test_gate_guard_main_execution():
    with patch("sys.argv", ["gate_guard", "snapshot"]):
        import runpy

        try:
            with patch("sys.stdout"):
                runpy.run_module("tools.gate_guard", run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0
