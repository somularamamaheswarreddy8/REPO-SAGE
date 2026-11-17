import sqlite3

conn = sqlite3.connect('reposage.db')
c = conn.cursor()
rows = c.execute("SELECT file_path FROM repository_files WHERE repository_id=1").fetchall()
print("repository_files for repo 1 count:", len(rows))
for r in rows[:15]:
    print(r[0])
