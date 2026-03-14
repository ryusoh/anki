# Add-on initialization

import traceback
from .search import build_tier1_query

def on_browser_did_search(search_context):
    """
    Hook to perform two-tiered reordering of search results:
    Tier 1: Matches in the Front field (appears first)
    Tier 2: Matches in other fields (appears second)
    Both tiers preserve Anki's original sort order.
    """
    try:
        query = search_context.search
        if not query:
            return

        # Build a query that strictly looks for our normal terms in the Front field
        tier_1_query = build_tier1_query(query)

        # If no normal terms exist, the tier 1 query is empty, and standard behavior applies
        if not tier_1_query:
            return

        col = search_context.browser.col
        is_notes_mode = search_context.browser.table.is_notes_mode()

        # Determine the set of IDs that match the Tier 1 query
        if is_notes_mode:
            # col.find_notes correctly accepts one argument: the query string
            tier_1_ids = set(col.find_notes(tier_1_query))
        else:
            # col.find_cards accepts the query string
            tier_1_ids = set(col.find_cards(tier_1_query))

        # context.ids contains the originally matched items, already perfectly sorted by Anki!
        all_sorted_ids = search_context.ids

        if not all_sorted_ids:
            return

        # Split the sorted items into the two tiers, maintaining the existing order
        tier_1 = []
        tier_2 = []

        for item_id in all_sorted_ids:
            if item_id in tier_1_ids:
                tier_1.append(item_id)
            else:
                tier_2.append(item_id)

        # Reassign to context.ids so the browser table displays them in our tiered order
        # search_context.ids is a Sequence[ItemId] in Anki, typically a list, but assigning a list is standard practice.
        search_context.ids = tier_1 + tier_2

    except Exception as e:
        # Log the error but continue execution by falling back to standard search
        print(f"[prioritize_front_field_search] API Error executing two-tiered sort: {e}")
        traceback.print_exc()

def init():
    try:
        # Instead of hooking will_search (which forces us to do the search and sorting ourselves),
        # we hook did_search, allowing Anki to do the heavy lifting of executing the search and sorting it.
        # We simply reorder the already-sorted IDs into our two tiers.
        from aqt.gui_hooks import browser_did_search
        browser_did_search.append(on_browser_did_search)
    except ImportError:
        pass

init()
