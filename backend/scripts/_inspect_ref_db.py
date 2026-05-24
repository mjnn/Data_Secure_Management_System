import sqlite3
import sys

path = sys.argv[1]
con = sqlite3.connect(path)
cur = con.cursor()
for (name,) in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall():
    print("TABLE", name)
    for row in cur.execute(f"PRAGMA table_info({name})").fetchall():
        print(" ", row)
    n = cur.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print("  rows:", n)
    print()
