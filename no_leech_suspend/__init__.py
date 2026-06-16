# -*- coding: utf-8 -*-

"""
Anki Add-on: No Leech Suspend

Stops Anki from automatically suspending cards. Anki only auto-suspends a card
when it becomes a "leech" (lapsed too many times) and the deck preset's leech
action is "Suspend Card". This add-on flips every preset's leech action to
"Tag Only", so the card is still tagged ``leech`` but never suspended. The flag
is re-applied whenever a profile is opened and after every sync, and a backup
hook unsuspends any leech that still slips through on the legacy scheduler.
"""

from aqt import gui_hooks, mw

# anki.consts.LEECH_TAGONLY — tag the card as a leech but never suspend it.
# (LEECH_SUSPEND is 0.) Hard-coded so the module imports cleanly under the test
# harness, which mocks the ``anki`` package.
LEECH_TAGONLY = 1

# anki.consts.QUEUE_TYPE_SUSPENDED — a card sitting in the suspended queue.
QUEUE_TYPE_SUSPENDED = -1


def _save_config(decks, conf):
    """Persist a modified deck preset across Anki versions."""
    saver = getattr(decks, "update_config", None) or getattr(decks, "save", None)
    if saver is not None:
        saver(conf)


def disable_leech_suspend(col):
    """Set every deck preset's leech action to tag-only. Returns count changed."""
    changed = 0
    for conf in col.decks.all_config():
        lapse = conf.get("lapse")
        if lapse is None:
            continue
        if lapse.get("leechAction") != LEECH_TAGONLY:
            lapse["leechAction"] = LEECH_TAGONLY
            _save_config(col.decks, conf)
            changed += 1
    return changed


def on_profile_did_open():
    """Apply the tag-only policy once the collection is loaded."""
    if mw is not None and mw.col is not None:
        disable_leech_suspend(mw.col)


def on_sync_did_finish():
    """Re-apply after sync, in case a preset arrived from another device."""
    if mw is not None and mw.col is not None:
        disable_leech_suspend(mw.col)


def unsuspend_leech(card):
    """Backup for the legacy scheduler: undo a suspend the moment it happens."""
    col = getattr(card, "col", None)
    if col is None:
        return
    if getattr(card, "queue", None) == QUEUE_TYPE_SUSPENDED:
        col.sched.unsuspend_cards([card.id])


gui_hooks.profile_did_open.append(on_profile_did_open)
gui_hooks.sync_did_finish.append(on_sync_did_finish)

# The legacy (v2) scheduler fires anki.hooks.card_did_leech after suspending.
# Importing lazily keeps the module importable if the hook is unavailable.
try:
    from anki.hooks import card_did_leech

    card_did_leech.append(unsuspend_leech)
except (ImportError, AttributeError):
    pass
