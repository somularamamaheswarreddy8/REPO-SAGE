import sqlite3
conn = sqlite3.connect('reposage.db')
c = conn.cursor()
for row in c.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name LIKE '%feedback%'"):
    print(row[0])
    print(row[1])
