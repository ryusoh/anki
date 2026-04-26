# Anki hook integration point
import sys
import os

try:
    from aqt import mw
except ImportError:
    mw = None

DEBUG_LOG = os.path.expanduser("~/Desktop/hsm_debug.log")

def log(msg):
    # Only log if debug is enabled in config
    if mw:
        try:
            config = mw.addonManager.getConfig(__name__)
            if not (config and config.get("debug", False)):
                return
        except:
            # If we can't get config, default to not logging
            return
    else:
        # If not running in Anki context (e.g. some tests), allow logging
        # unless it's explicitly disabled by an environment variable or similar
        # but for simplicity, let's just allow it for now if mw is None
        # so tests don't break.
        pass

    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(msg + "\n")
    except:
        pass

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
