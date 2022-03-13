from anki.hooks import wrap
from aqt.addcards import AddCards
from anki.stats import CollectionStats
from aqt.utils import showInfo
from anki.notes import Note
import aqt
import anki

import json
import time
import sqlite3
from sqlite3 import Error
import os
import pathlib
import sys


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def myInit(self, mw):
    self.start = time.time()


def convert_time(seconds):  # converts time to minutes / hours if needed
    seconds = float(seconds)
    if seconds >= 3600:
        return str(round(seconds / 3600, 2)) + "" + "時"
    elif seconds >= 60:
        return str(round(seconds / 60, 2)) + "" + "分"
    else:
        return str(round(seconds, 2)) + "" + "秒"


def addCardToDB(self, note):
    t = round(time.time() - self.start, 2)
    t = min(t, maxCreationTime)

    cursor.execute('''INSERT INTO times(note, time, deck) VALUES (?, ?, ?)''', [
                   note.id, t, self.deckChooser.selectedId()])
    db.commit()
    self.start = time.time()
    return note


def myTodayStats(self, _old):
    lims = "WHERE note > %d" % ((self.col.sched.dayCutoff - 86400) * 1000)
    if not self.wholeCollection:
        deckId = self._limit()
        lims += " AND " + ("deck in " + deckId)

    todays_time_adding = cursor.execute(
        '''SELECT time FROM times %s''' % lims).fetchall()
    tot = sum([i[0] for i in todays_time_adding])

    b = "<br>" + "今日カードを{}で作成しています".format(
        str(convert_time(tot)))
    return _old(self) + b


def addGraph(self, _old):

    colLearn = "#00F"  # colour of bars
    start, days, chunk = self.get_start_end_chunk()
    lims = []
    if days is not None:
        lims.append("note > " +
                    str((aqt.mw.col.sched.dayCutoff - (days * chunk * 86400)) * 1000))
    # adds an extra condition depending on the scope of the data
    if not self.wholeCollection:
        deckId = self._limit()

        lims.append("deck in " + deckId)
    if len(lims) == 2:
        lim = "WHERE " + " AND ".join(lims)
    elif len(lims) == 1:
        lim = "WHERE " + lims[0]
    else:
        lim = ""
    # lim is actually the last argument, it is just passed differently (%s)
    # rounds time in minutes to 2 d.p, might change this later on
    cursor.execute("""
select
(cast((note/1000.0 - ?) / 86400.0 as int))/? as day,
round(sum(time/60), 2)
from times %s
group by day order by day"""
                   % lim, [self.col.sched.dayCutoff, chunk]
                   )
    data = cursor.fetchall()

    if not data:
        return ""
    conf = dict(
        xaxis=dict(tickDecimals=0, max=0.5),
        yaxes=[dict(min=0), dict(position="right", min=0)],
    )
    if days is not None:
        conf["xaxis"]["min"] = -days + 0.5

    def plot(id, data, ylabel, ylabel2):
        return self._graph(
            id, data=data, conf=conf, xunit=chunk, ylabel=ylabel, ylabel2=ylabel2
        )
    repdata, repsum = self._splitRepData(data, ((1, colLearn, ""),))
    # sys.stderr.write(str(repdata) + "\n")
    txt = self._title(_("カード作る時間"), _(
        "カードの作成に費やした時間"))
    txt += plot("added", repdata, ylabel=_("分"),
                ylabel2=_("累積時間 (分間)〔折れ線グラフ〕"))
    tot = sum([i[1] for i in data]) * 60  # convert minutes -> seconds

    i = []
    self._line(i, _("合計"), convert_time(tot))
    txt += self._lineTbl(i)

    return _old(self) + self._section("<center>%s</center>" % txt)

    # finds path to test.db and opens it
__here__ = pathlib.Path(__file__).resolve().parent
db_file = str(__here__ / 'user_files' / "test.db")
db = create_connection(db_file)

# creates the table if it doesn't exist and commits
cursor = db.cursor()
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS times(note INTEGER, time INTEGER, deck INTEGER)''')
db.commit()

# finds the maxCreationTime variable from the json file
config = aqt.mw.addonManager.getConfig(__name__)
maxCreationTime = config['maxCreationTime']

AddCards.__init__ = wrap(AddCards.__init__, myInit)
AddCards.addNote = wrap(AddCards.addNote, addCardToDB)
CollectionStats.todayStats = wrap(
    CollectionStats.todayStats, myTodayStats, "around")

# to get the graph in the correct position, i add the graph to the section
# where the 'cards added' graph is returned

CollectionStats.introductionGraph = wrap(
    CollectionStats.introductionGraph, addGraph, "around")
