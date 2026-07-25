"""Shared aqt.editor test double for the strip_html_tags test modules.

on_js_message gates on isinstance(context, Editor), so the Editor class
installed in the aqt.editor mock must be ONE shared class. If each test
module installed its own, whichever module imported strip_html_tags first
would bind its Editor inside the addon, and the other module's fake editors
would fail the isinstance check (order-dependent breakage).
"""

import sys
from unittest.mock import MagicMock


class Editor:
    pass


sys.modules['aqt'] = MagicMock()
mock_editor_mod = MagicMock()
mock_editor_mod.Editor = Editor
sys.modules['aqt.editor'] = mock_editor_mod
