import re
from aqt import mw
from aqt.gui_hooks import browser_did_fetch_row
from aqt.browser import Browser
from .core import extract_search_terms, highlight_text

STYLE_CSS = """
<style>
.search-highlight {
    border-bottom: 2px solid #00bcd4;
    background-color: rgba(0, 188, 212, 0.15);
    border-radius: 2px;
    font-weight: 600;
}
</style>
"""

def on_browser_did_fetch_row(item: object, is_notes_mode: bool, row: object, active_columns: list[str]) -> None:
    """
    Hook into Anki's browser to modify the rendered cell text.
    """
    browser = mw.app.activeWindow()
    if not isinstance(browser, Browser):
        return

    # aqt.browser.SearchBox inherits from QLineEdit, so we can just call text()
    query = browser.form.searchEdit.text()

    terms = extract_search_terms(query)

    if not terms:
        return

    for cell in item.cells:
        if cell.text:
            cell.text = highlight_text(cell.text, terms)
            # Inject CSS style inline if we modified the text
            # To avoid injecting it multiple times, we can just append it to the first matching cell
            if '<span class="search-highlight">' in cell.text and '<style>' not in cell.text:
                 cell.text += STYLE_CSS

def init_addon():
    browser_did_fetch_row.append(on_browser_did_fetch_row)
