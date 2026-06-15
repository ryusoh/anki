import os

from typing import Any, Dict, Optional, Union

from aqt import mw

addon_path = os.path.dirname(__file__)
addonfoldername = os.path.basename(addon_path)


def gc(arg: str = "", fail: Any = False) -> Any:
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        if arg:
            return conf.get(arg, fail)
        else:
            return conf
    return fail


userOption: Optional[Dict[str, Any]] = None


def _getUserOption(refresh: bool) -> None:
    global userOption
    if userOption is None or refresh:
        userOption = mw.addonManager.getConfig(__name__)


def getUserOption(
    key: Optional[str] = None, default: Any = None, refresh: bool = False
) -> Any:
    _getUserOption(refresh)
    if userOption is None:
        return default if key is not None else {}
    if key is None:
        return userOption
    return userOption.get(key, default)


def writeConfig(configToWrite: Optional[Dict[str, Any]] = None) -> None:
    if configToWrite is None:
        configToWrite = userOption
    if configToWrite is not None:
        mw.addonManager.writeConfig(__name__, configToWrite)


def getDefaultConfig() -> Dict[str, Any]:
    addon = __name__.split(".")[0]
    return mw.addonManager.addonConfigDefaults(addon) or {}
