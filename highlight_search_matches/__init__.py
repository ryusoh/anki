# Anki hook integration point
import os
import sys

try:
    from aqt import mw
except ImportError:
    mw = None

DEBUG_LOG = os.path.expanduser("~/Desktop/hsm_debug.log")


def log(msg):
    # Only log if debug is enabled in config
    try:
        import aqt

        current_mw = getattr(aqt, "mw", None)
    except ImportError:
        current_mw = None

    if current_mw:
        try:
            config = current_mw.addonManager.getConfig(__name__)
            if not config or (hasattr(config, "get") and not config.get("debug", False)):
                return
        except Exception as e:
            # If we can't get config, default to not logging
            import logging

            logging.getLogger(__name__).debug(f"Failed to get config: {e}")
            return
    else:
        # If not running in Anki context, only allow logging if running in a test suite
        if "pytest" not in sys.modules:
            return

    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(msg + "\n")
    except Exception as e:
        import logging

        logging.getLogger(__name__).debug(f"Failed to write to debug log: {e}")


def init_addon():
    log(f"[hsm] init_addon called, aqt loaded: {'aqt' in sys.modules}")
    if "aqt" not in sys.modules:
        log("[hsm] aqt not loaded yet, skipping")
        return

    from .anki_integration import init_addon as init_browser
    from .editor_integration import init_editor

    init_browser()
    init_editor()
    log("[hsm] addon initialized successfully")


log("[hsm] __init__.py loading")
init_addon()
