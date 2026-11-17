import sqlite3
conn = sqlite3.connect('reposage.db')
c = conn.cursor()
rows = c.execute("SELECT DISTINCT commit_sha, count(*) FROM code_chunks WHERE repository_id=1 GROUP BY commit_sha").fetchall()
print("Repo 1 commits in code_chunks:", rows)
r = c.execute("SELECT indexed_commit_sha FROM repositories WHERE id=1").fetchone()
print("Repo 1 indexed_commit_sha in repositories table:", r[0])
