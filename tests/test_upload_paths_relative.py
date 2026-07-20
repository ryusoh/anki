"""Regression guard: R2 upload scripts must resolve repo paths relative to __file__.

Historically `graph/upload_public.py` hard-coded
`/Users/lz/Library/Application Support/Anki2/addons21`, which broke tests when
worktrees changed and was brittle in CI. A previous fix made it resolve paths
relative to `__file__`. This test pins that behavior so it does not regress.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_PUBLIC = REPO_ROOT / "graph" / "upload_public.py"
UPLOAD_TO_R2 = REPO_ROOT / "data" / "anki" / "upload-to-r2"
ANKI_PATH = "/Users/lz/Library/Application Support/Anki2/addons21"


def test_upload_public_uses_repo_relative_paths():
    text = UPLOAD_PUBLIC.read_text(encoding="utf-8")
    assert ANKI_PATH not in text, (
        f"{UPLOAD_PUBLIC} must not hard-code the Anki add-ons path; "
        "resolve paths relative to __file__ / repo root"
    )
    assert "REPO_ROOT = Path(__file__).resolve().parents[1]" in text


def test_upload_to_r2_staging_dir_falls_back_to_script_location():
    text = UPLOAD_TO_R2.read_text(encoding="utf-8")
    assert ANKI_PATH not in text, f"{UPLOAD_TO_R2} must not hard-code the Anki add-ons path"
    # The fallback uses script_dir.parent / "cloudflare", not the Anki path.
    assert 'script_dir = Path(__file__).parent' in text
    assert 'script_dir.parent / "cloudflare"' in text


def test_upload_public_module_loads_without_hardcoded_anki_path():
    """Running upload_public.py --help should work without the Anki path existing."""
    result = subprocess.run(
        [sys.executable, str(UPLOAD_PUBLIC), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    # The script has no --help handler, so it proceeds to upload and exits 0
    # even with nothing to upload. The important thing is it does not fail
    # because of a missing hardcoded Anki add-ons directory.
    assert result.returncode == 0, result.stderr


def test_upload_to_r2_module_loads_without_hardcoded_anki_path():
    """Running upload-to-r2 --help should work without the Anki path existing."""
    result = subprocess.run(
        [sys.executable, str(UPLOAD_TO_R2), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Upload full private Anki content to Cloudflare R2" in result.stdout
