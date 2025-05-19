# Copyright (C) Joseph Yasmeh 2019-2020 <https://ankiweb.net/shared/info/2133933791>
# Copyright (C) Shigeyuki 2025 <http://patreon.com/Shigeyuki>"
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from aqt.deckbrowser import *
from .path_manager import MESSAGE_TEMPLATE, check_custom_text


def _renderStats_3(self:"DeckBrowser") -> str:
    try:
        config = self.mw.addonManager.getConfig(__name__)

        use_distinct = config.get("use_distinct_count", False)
        if use_distinct:
            count_clause = "count(DISTINCT cid)"
        else:
            count_clause = "count(cid)"

        sql_query = f"""
        SELECT
            {count_clause},
            sum(time)/1000
        FROM revlog
        WHERE id > ?
        """

        if hasattr(self.mw.col.sched, "day_cutoff"):
            day_cutoff = self.mw.col.sched.day_cutoff
        else:
            day_cutoff = self.mw.col.sched.dayCutoff

        cutoff_time = (day_cutoff - 86400) * 1000
        cards, thetime = self.mw.col.db.first(sql_query, cutoff_time)

        card_text = cards or 0
        thetime = thetime or 0

        try:
            time_text = self.mw.col.format_timespan(thetime, context=0)
            # print(time_text)
        except Exception as e:
            print(e)
            from anki.utils import fmtTimeSpan
            time_text = fmtTimeSpan(thetime, unit=1)

        if cards > 0:
            avg_seconds = thetime / cards
            # avg_text = f" ({avg_seconds:.1f}s/card)"
            avg_text = f"{avg_seconds:.1f}"
        else:
            avg_text = "0"

        custom_text = config.get("custom_text", MESSAGE_TEMPLATE) #type: str

        custom_text = check_custom_text(custom_text)

        studied_today = custom_text.format(
            card_text=card_text,
            time_text=time_text,
            avg_text=avg_text
        )

        studied_today = f"""<a href=#
        onclick="pycmd('shige_rewrite_study_cards_text'); return false;"
        style="color: inherit; text-decoration: none;">{studied_today}</a>"""
        return studied_today
    except Exception as e:
        print(e)
        return '<div id="studiedToday"><span>{}</span></div>'.format(
            self._render_data.studied_today
        )

orig__renderStats = DeckBrowser._renderStats
DeckBrowser._renderStats = _renderStats_3

def handleMyAddonConfig(handled, message, context):
    if message == "shige_rewrite_study_cards_text":
        from .shige_config.addon_config import setMyAddonConfig
        QTimer.singleShot(0, setMyAddonConfig)
        return (True, None)
    else:
        return handled

gui_hooks.webview_did_receive_js_message.append(handleMyAddonConfig)