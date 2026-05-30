import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sqlite3
conn = sqlite3.connect(r"d:\Trea study\TrendRadar\output\news\2026-05-07.db")
c = conn.cursor()
c.execute("""
    SELECT n.title, p.name as platform, n.rank, n.first_crawl_time, n.crawl_count
    FROM news_items n
    JOIN platforms p ON n.platform_id = p.id
    ORDER BY n.rank ASC
    LIMIT 25
""")
rows = c.fetchall()
conn.close()

print(f"{'='*60}")
print(f"                今日热点新闻 TOP 25")
print(f"{'='*60}\n")

for i, (title, platform, rank, time, count) in enumerate(rows, 1):
    rank_mark = f"(#{rank})" if rank and rank <= 5 else f"#{rank}" if rank else ""
    print(f" {i:2}. [{platform:8s} {rank_mark:8s}] {title}")

print(f"\n{'='*60}")
print(f"数据时间: 2026-05-07 01:08 | 共爬取 255 条新闻 | 覆盖 11 个平台")
