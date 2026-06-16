import importlib
import sys
from unittest.mock import MagicMock


def _make_col(configs):
    col = MagicMock()
    col.decks.all_config.return_value = configs
    # Route both possible save APIs through one recorder.
    col.decks.update_config = MagicMock()
    col.decks.save = MagicMock()
    return col


def _load(mw):
    mock_aqt = MagicMock()
    mock_aqt.mw = mw
    mock_aqt.gui_hooks.profile_did_open = []
    mock_aqt.gui_hooks.sync_did_finish = []
    sys.modules['aqt'] = mock_aqt

    import no_leech_suspend

    importlib.reload(no_leech_suspend)
    return no_leech_suspend


def test_flips_suspend_to_tag_only():
    suspend = {"lapse": {"leechAction": 0}}
    already = {"lapse": {"leechAction": 1}}
    col = _make_col([suspend, already])
    mod = _load(MagicMock(col=col))

    changed = mod.disable_leech_suspend(col)

    assert changed == 1
    assert suspend["lapse"]["leechAction"] == mod.LEECH_TAGONLY
    # Only the preset that needed changing was saved.
    col.decks.update_config.assert_called_once_with(suspend)


def test_skips_configs_without_lapse():
    weird = {"name": "Default"}  # no "lapse" key
    col = _make_col([weird])
    mod = _load(MagicMock(col=col))

    assert mod.disable_leech_suspend(col) == 0
    col.decks.update_config.assert_not_called()


def test_falls_back_to_save_when_no_update_config():
    suspend = {"lapse": {"leechAction": 0}}
    col = _make_col([suspend])
    del col.decks.update_config  # older Anki: only decks.save exists
    mod = _load(MagicMock(col=col))

    mod.disable_leech_suspend(col)

    col.decks.save.assert_called_once_with(suspend)


def test_profile_hook_registered_and_applies():
    suspend = {"lapse": {"leechAction": 0}}
    col = _make_col([suspend])
    mod = _load(MagicMock(col=col))

    assert mod.on_profile_did_open in mod.gui_hooks.profile_did_open
    assert mod.on_sync_did_finish in mod.gui_hooks.sync_did_finish

    mod.on_profile_did_open()
    assert suspend["lapse"]["leechAction"] == mod.LEECH_TAGONLY


def test_profile_hook_safe_without_collection():
    mod = _load(MagicMock(col=None))
    mod.on_profile_did_open()  # must not raise


def test_unsuspend_leech_unsuspends_suspended_card():
    mod = _load(MagicMock(col=MagicMock()))
    card = MagicMock(id=42, queue=mod.QUEUE_TYPE_SUSPENDED)

    mod.unsuspend_leech(card)

    card.col.sched.unsuspend_cards.assert_called_once_with([42])


def test_unsuspend_leech_ignores_non_suspended_card():
    mod = _load(MagicMock(col=MagicMock()))
    card = MagicMock(id=7, queue=0)

    mod.unsuspend_leech(card)

    card.col.sched.unsuspend_cards.assert_not_called()
