# -*- coding: utf-8 -*-

"""
Anki Add-on: Hide Deck Browser Expand/Collapse Icons & Center Layout
Hides the +/- symbols and quantitatively centers content within the original pane width.
"""

from aqt import gui_hooks

def on_webview_will_set_content(web_content, context):
    """Inject CSS to hide icons and balance the layout while keeping the original width."""
    if context.__class__.__name__ != "DeckBrowser":
        return
    
    css = """
    <style>
    /* 1. Hide the +/- icons but keep their space for indentation */
    .collapse {
        visibility: hidden !important;
        pointer-events: none !important;
    }

    /* 2. Restore Original Table Size and Quantitative Centering:
       Based on standard Anki layouts, we restore the fixed-width feel 
       without letting it expand to the full window. 
       We use a fixed max-width to keep it 'original' sized. */
    
    #recont {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        margin-top: 20px !important;
    }

    table {
        /* This is the typical 'original' width for the deck pane */
        width: 550px !important; 
        margin: 0 auto !important;
        border-collapse: collapse !important;
        border: none !important;
    }

    /* 3. Refined Internal Spacing for Symmetry:
       We use fixed pixel padding to ensure quantitative symmetry 
       regardless of window resizing. */
    
    .decktd {
        padding-left: 15px !important; /* Space from left edge */
        padding-right: 20px !important;
        text-align: left !important;
        border: none !important;
    }

    .count {
        text-align: right !important;
        padding-left: 20px !important;
        padding-right: 10px !important;
        white-space: nowrap !important;
        border: none !important;
    }
    
    /* Balance the right-most Cog icon with the left-most deck padding */
    .optstds {
        padding-left: 10px !important;
        padding-right: 15px !important; /* Symmetrical space from right edge */
        border: none !important;
    }

    /* Remove all structural box lines */
    tr, td, th {
        border: none !important;
        outline: none !important;
    }
    </style>
    """
    web_content.head += css

gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
