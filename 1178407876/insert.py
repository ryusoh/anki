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


__here__ = pathlib.Path(__file__).resolve().parent
db_file = str(__here__ / 'user_files' / "test.db")
db = create_connection(db_file)

# creates the table if it doesn't exist and commits
cursor = db.cursor()
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS times(note INTEGER, time INTEGER, deck INTEGER)''')
db.commit()

cursor.execute(
    '''INSERT INTO times (note, time, deck) VALUES (?, 989, 1591391354321)''', [1593619446912 + (86400 * 1000 * -27)])
cursor.execute(
    '''INSERT INTO times (note, time, deck) VALUES (?, 2380, 1591391354321)''', [1593619446912 + (86400 * 1000 * -28)])
cursor.execute(
    '''INSERT INTO times (note, time, deck) VALUES (?, 1678, 1591391354321)''', [1593619446912 + (86400 * 1000 * -29)])
cursor.execute(
    '''INSERT INTO times (note, time, deck) VALUES (?, 2003, 1591391354321)''', [1593619446912 + (86400 * 1000 * -30)])

db.commit()
