# Add-on initialization

import traceback
from .search import build_tier1_query, extract_terms, sort_tier1_by_score

def on_browser_did_search(search_context):
    """
    Hook to perform two-tiered reordering of search results:
    Tier 1: Matches in the Front field (appears first)
    Tier 2: Matches in other fields (appears second)
    Both tiers preserve Anki's original sort order.
    
    Within Tier 1, we further rank matches:
    - Exact match (highest)
    - Word match
    - Partial match (single word)
    - Non-word partial match (lowest in Tier 1)
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
            tier_1_ids_set = set(col.find_notes(tier_1_query))
        else:
            # col.find_cards accepts the query string
            tier_1_ids_set = set(col.find_cards(tier_1_query))

        # context.ids contains the originally matched items, already perfectly sorted by Anki!
        all_sorted_ids = search_context.ids

        if not all_sorted_ids:
            return

        # Split the sorted items into the two tiers, maintaining the existing order
        tier_1 = []
        tier_2 = []

        for item_id in all_sorted_ids:
            if item_id in tier_1_ids_set:
                tier_1.append(item_id)
            else:
                tier_2.append(item_id)

        # Further rank Tier 1 results if there are any
        if tier_1:
            terms = extract_terms(query)
            if terms:
                # Fetch Front field data for all items in tier_1
                note_data = {}
                model_cache = {}
                
                # SQLite limit for IN clause is usually 999 or 1000
                chunk_size = 900
                for i in range(0, len(tier_1), chunk_size):
                    chunk = tier_1[i:i + chunk_size]
                    id_list = ",".join(map(str, chunk))
                    
                    if is_notes_mode:
                        # IDs are note IDs
                        rows = col.db.all(f"select id, mid, flds from notes where id in ({id_list})")
                        for nid, mid, flds in rows:
                            if mid not in model_cache:
                                model_cache[mid] = col.models.get(mid)
                            model = model_cache[mid]
                            
                            idx = 0
                            if model:
                                for f in model['flds']:
                                    if f['name'] == "Front":
                                        idx = f['ord']
                                        break
                            
                            flds_list = flds.split('\x1f')
                            if idx < len(flds_list):
                                note_data[nid] = flds_list[idx]
                    else:
                        # IDs are card IDs
                        rows = col.db.all(f"select c.id, n.mid, n.flds from cards c join notes n on c.nid = n.id where c.id in ({id_list})")
                        for cid, mid, flds in rows:
                            if mid not in model_cache:
                                model_cache[mid] = col.models.get(mid)
                            model = model_cache[mid]
                            
                            idx = 0
                            if model:
                                for f in model['flds']:
                                    if f['name'] == "Front":
                                        idx = f['ord']
                                        break
                            
                            flds_list = flds.split('\x1f')
                            if idx < len(flds_list):
                                note_data[cid] = flds_list[idx]
                
                tier_1 = sort_tier1_by_score(tier_1, note_data, terms)

        # Reassign to context.ids so the browser table displays them in our tiered order
        search_context.ids = tier_1 + tier_2

    except Exception as e:
        # Log the error but continue execution by falling back to standard search
        print(f"[prioritize_front_field_search] API Error executing two-tiered sort: {e}")
        traceback.print_exc()

def init():
    try:
        from aqt.gui_hooks import browser_did_search
        browser_did_search.append(on_browser_did_search)
    except ImportError:
        pass

init()
