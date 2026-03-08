from aqt.main import AnkiQt
from aqt import mw

# Save the original setWindowTitle method
original_set_window_title = AnkiQt.setWindowTitle

def custom_set_window_title(self, title):
    # Always set the title to an empty string to hide it
    original_set_window_title(self, "")

# Monkey patch the method on the AnkiQt class
AnkiQt.setWindowTitle = custom_set_window_title

# If the main window is already initialized, clear its current title
if mw:
    mw.setWindowTitle("")
