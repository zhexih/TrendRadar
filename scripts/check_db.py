import sqlite3
conn = sqlite3.connect(r"d:\Trea study\TrendRadar\output\news\2026-05-07.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables:", [t[0] for t in tables])
for t in tables:
    tn = t[0]
    c.execute(f'SELECT * FROM "{tn}" LIMIT 1')
    cols = [d[0] for d in c.description]
    print(f"\n[{tn}] columns:", cols)
    row = c.fetchone()
    if row:
        for i, (col, val) in enumerate(zip(cols, row)):
            val_str = str(val)
            if len(val_str) > 80:
                val_str = val_str[:80] + "..."
            print(f"  {col}: {val_str}")
conn.close()
