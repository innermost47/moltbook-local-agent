import sqlite3

conn = sqlite3.connect("mock_moltbook.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, title, content, author_id FROM posts LIMIT 10"
).fetchall()
for r in rows:
    print(f'ID: {r["id"]}')
    print(f'Title: {r["title"]}')
    print(f'Content: {str(r["content"])[:100] if r["content"] else "EMPTY"}')
    print(f'Author: {r["author_id"]}')
    print("---")
conn.close()
