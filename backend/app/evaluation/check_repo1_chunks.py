import sqlite3
conn = sqlite3.connect('reposage.db')
c = conn.cursor()
rows = c.execute("SELECT id, file_path, symbol_name, start_line, end_line, content FROM code_chunks WHERE repository_id=1 AND commit_sha='215abaff7efbf964400c835b2efed856742fc20a'").fetchall()
for r in rows:
    print(r[0], r[1], r[2], f"L{r[3]}-L{r[4]}")
    print(r[5][:80])
    print("-" * 30)
