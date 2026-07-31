# -*- coding: utf-8 -*-
"""Pin that vendor updates are disabled for our awesome_tts fork."""

import json
from pathlib import Path


def test_meta_update_disabled():
    """awesome_tts/meta.json must have update_enabled false.

    The repo is symlinked into Anki's addons21; a vendor update from AnkiWeb
    would silently overwrite our local fork. Regression test for spec §2.1.
    """
    meta = Path(__file__).resolve().parents[1] / "meta.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    assert data.get("update_enabled") is False, "vendor updates must be disabled"
