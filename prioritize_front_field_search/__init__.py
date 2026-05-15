# Add-on initialization

import traceback
from .search import extract_terms, score_front_match

def _fetch_front_fields(col, all_sorted_ids, is_notes_mode):
    note_data = {}
    model_cache = {}
    chunk_size = 900

    for i in range(0, len(all_sorted_ids), chunk_size):
        chunk = all_sorted_ids[i:i + chunk_size]
        id_list = ",".join(map(str, chunk))

        if is_notes_mode:
            rows = col.db.all(f"select id, mid, flds from notes where id in ({id_list})")
        else:
            rows = col.db.all(f"select c.id, n.mid, n.flds from cards c join notes n on c.nid = n.id where c.id in ({id_list})")

        for item_id, mid, flds in rows:
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
                note_data[item_id] = flds_list[idx]

    return note_data

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

        terms = extract_terms(query)
        if not terms:
            return

        all_sorted_ids = search_context.ids
        if not all_sorted_ids:
            return

        col = search_context.browser.col
        is_notes_mode = search_context.browser.table.is_notes_mode()

        # Fetch Front field data for all initially matched items
        note_data = _fetch_front_fields(col, all_sorted_ids, is_notes_mode)
        
        tier_1 = []
        tier_2 = []
        score_map = {}

        for item_id in all_sorted_ids:
            front_text = note_data.get(item_id, "")
            score = sum(score_front_match(front_text, term) for term in terms)
            if score > 0:
                tier_1.append(item_id)
                score_map[item_id] = score
            else:
                tier_2.append(item_id)

        # Sort Tier 1 descending by score, maintaining stable sort
        if tier_1:
            tier_1 = sorted(tier_1, key=lambda x: score_map[x], reverse=True)

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
