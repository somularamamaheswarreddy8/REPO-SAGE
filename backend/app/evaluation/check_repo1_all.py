import sqlite3
conn = sqlite3.connect('reposage.db')
c = conn.cursor()
rows = c.execute("SELECT commit_sha, count(*) FROM code_chunks WHERE repository_id=1 GROUP BY commit_sha").fetchall()
print("Repo 1 commits in code_chunks:", rows)
rows_all = c.execute("SELECT id, commit_sha, file_path FROM code_chunks WHERE repository_id=1 LIMIT 10").fetchall()
print("Sample rows:", rows_all)
