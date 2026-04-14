import sys
from unittest.mock import MagicMock

sys.modules['aqt'] = MagicMock()
sys.modules['aqt.browser'] = MagicMock()
sys.modules['aqt.qt'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.webview'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()
