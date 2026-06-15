from aqt import mw
from aqt.main import AnkiQt

# Prevent infinite recursion if the addon is reloaded
if not hasattr(AnkiQt, "_hide_window_title_patched"):
    # Save the original setWindowTitle method
    original_set_window_title = AnkiQt.setWindowTitle

    def custom_set_window_title(self, title):
        # Always set the title to an empty string to hide it
        original_set_window_title(self, "")

    # Monkey patch the method on the AnkiQt class
    AnkiQt.setWindowTitle = custom_set_window_title
    AnkiQt._hide_window_title_patched = True

# If the main window is already initialized, clear its current title
if mw:
    mw.setWindowTitle("")
