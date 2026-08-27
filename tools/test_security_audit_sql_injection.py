import sqlite3

def test_insert_reviews_sql_injection():
    # Setup
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE revlog (
            id INTEGER PRIMARY KEY,
            cid INTEGER,
            usn INTEGER,
            ease INTEGER,
            ivl INTEGER,
            lastIvl INTEGER,
            factor INTEGER,
            time INTEGER,
            type INTEGER
        )
    ''')

    # Attack payload to drop the table
    reviews = [
        [1, 2, 3, 4, 5, 6, 7, 8, '9); DROP TABLE revlog; --']
    ]

    # Vulnerable implementation simulation
    sql_vuln = 'insert into revlog(id,cid,usn,ease,ivl,lastIvl,factor,time,type) values '
    for row in reviews:
        sql_vuln += '(%s),' % ','.join(map(str, row))
    sql_vuln = sql_vuln[:-1]

    # VULNERABILITY ASSERTION: The executescript succeeds and the table is dropped.
    conn.executescript(sql_vuln)
    try:
        conn.execute("SELECT * FROM revlog")
        vuln_success = False
    except sqlite3.OperationalError as e:
        vuln_success = 'no such table: revlog' in str(e)
    assert vuln_success, "Vulnerability check failed: table should have been dropped."

    # Setup again
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE revlog (
            id INTEGER PRIMARY KEY,
            cid INTEGER,
            usn INTEGER,
            ease INTEGER,
            ivl INTEGER,
            lastIvl INTEGER,
            factor INTEGER,
            time INTEGER,
            type INTEGER
        )
    ''')

    # Patched implementation simulation
    sql_patched = 'insert into revlog(id,cid,usn,ease,ivl,lastIvl,factor,time,type) values '
    sql_patched += ','.join(['(?,?,?,?,?,?,?,?,?)'] * len(reviews))
    flat_params = [item for row in reviews for item in row]

    # PATCH ASSERTION: The parameterization handles the injection gracefully
    conn.execute(sql_patched, flat_params)

    # Table should still exist
    conn.execute("SELECT * FROM revlog")
