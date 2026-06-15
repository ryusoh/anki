from anki.utils import int_time
from aqt import mw

from .consts import *
from .debug import debug

# Associate [column name][deck id name] to some value corresponding to
# the number of card of this deck in this column
values = dict()


def computeValues():
    debug("Compute values")
    cutoff = int_time() + mw.col.get_config('collapseTime')
    today = mw.col.sched.today
    tomorrow = today + 1
    yesterdayLimit = (mw.col.sched.day_cutoff - 86400) * 1000
    debug(f"Yesterday limit is {yesterdayLimit}")
    queriesCardCount = [(f"flag {i}", f"(flags & 7) == {i}", "", "") for i in range(5)] + [
        ("due tomorrow", f"queue in ({QUEUE_REV},{QUEUE_DAY_LRN}) and due = {tomorrow}", "", ""),
        ("learning now from today", f"queue = {QUEUE_LRN} and due <= {cutoff}", "", ""),
        ("learning today from past", f"queue = {QUEUE_DAY_LRN} and due <= {today}", "", ""),
        ("learning later today", f"queue = {QUEUE_LRN} and due > {cutoff}", "", ""),
        ("learning future", f"queue = {QUEUE_DAY_LRN} and due > {today}", "", ""),
        ("learning today repetition from today", f"queue = {QUEUE_LRN}", "left/1000", ""),
        ("learning today repetition from past", f"queue = {QUEUE_DAY_LRN}", "left/1000", ""),
        ("learning repetition from today", f"queue = {QUEUE_LRN}", "mod%1000", ""),
        ("learning repetition from past", f"queue = {QUEUE_DAY_LRN}", "mod%1000", ""),
        ("review due", f"queue = {QUEUE_REV} and due <= {today}", "", ""),
        ("reviewed today", f"queue = {QUEUE_REV} and due>0 and due-ivl = {today}", "", ""),
        (
            "repeated today",
            f"revlog.id>{yesterdayLimit}",
            "",
            "revlog inner join cards on revlog.cid = cards.id",
        ),
        ("repeated", "", "", "revlog inner join cards on revlog.cid = cards.id"),
        ("unseen", f"queue = {QUEUE_NEW_CRAM}", "", ""),
        ("buried", f"queue = {QUEUE_USER_BURIED}  or queue = {QUEUE_SCHED_BURIED}", "", ""),
        ("suspended", f"queue = {QUEUE_SUSPENDED}", "", ""),
        ("cards", "", "", ""),
        ("undue", f"queue = {QUEUE_REV} and due >  {today}", "", ""),
        ("mature", f"queue = {QUEUE_REV} and ivl >= 21", "", ""),
        ("young", f"queue = {QUEUE_REV} and 0<ivl and ivl <21", "", ""),
    ]

    # Group queries by table
    queries_by_table = {}
    for name, condition, addend, table in queriesCardCount:
        if not table:
            table = "cards"
        if table not in queries_by_table:
            queries_by_table[table] = []
        queries_by_table[table].append((name, condition, addend))
        values[name] = dict()

    for table, query_list in queries_by_table.items():
        select_parts = ["did"]
        for _idx, (_name, condition, addend) in enumerate(query_list):
            expr = addend if addend else "1"
            if condition:
                select_parts.append(f"SUM(CASE WHEN {condition} THEN {expr} ELSE NULL END)")
            else:
                select_parts.append(f"SUM({expr})")

        query = f"SELECT {', '.join(select_parts)} FROM {table} GROUP BY did"
        results = mw.col.db.all(query)
        debug(f"""For table {table}: query "{query}".""")

        for row in results:
            did = row[0]
            for idx, (name, _condition, _addend) in enumerate(query_list):
                val = row[idx + 1]
                if val is not None and val > 0:
                    debug(f"In deck {did} there are {val} cards of kind {name}")
                    values[name][did] = val


times = dict()


def computeTime():
    times.clear()
    for did, time in mw.col.db.all(
        f"select did,min(case when queue = {QUEUE_LRN} then due else null end) from cards group by did"
    ):
        times[did] = time
