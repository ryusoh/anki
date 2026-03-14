# Anki hook integration point
import sys

def init_addon():
    if "aqt" not in sys.modules:
        return

    from .anki_integration import init_addon as init_browser
    from .editor_integration import init_editor

    init_browser()
    init_editor()

init_addon()
