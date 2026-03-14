# Anki hook integration point
import sys
import os

DEBUG_LOG = os.path.expanduser("~/Desktop/hsm_debug.log")

def log(msg):
    with open(DEBUG_LOG, "a") as f:
        f.write(msg + "\n")

def init_addon():
    log(f"[hsm] init_addon called, aqt loaded: {'aqt' in sys.modules}")
    if "aqt" not in sys.modules:
        log(f"[hsm] aqt not loaded yet, skipping")
        return

    from .anki_integration import init_addon as init_browser
    from .editor_integration import init_editor

    init_browser()
    init_editor()
    log(f"[hsm] addon initialized successfully")

log(f"[hsm] __init__.py loading")
init_addon()
