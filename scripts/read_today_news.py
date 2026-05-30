import sqlite3
import os

DB_PATH = r"d:\Trea study\TrendRadar\output\news\2026-05-12.db"
RSS_DB_PATH = r"d:\Trea study\TrendRadar\output\rss\2026-05-12.db"


def read_news():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM news_items")
    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT n.title, n.platform_id, p.name as platform_name, n.rank, n.last_crawl_time
        FROM news_items n
        LEFT JOIN platforms p ON n.platform_id = p.id
        ORDER BY n.rank ASC, n.last_crawl_time DESC
        LIMIT 50
    """
    )
    rows = cursor.fetchall()

    print("=" * 70)
    print("  TrendRadar 今日热点新闻 (2026-05-12)")
    print(f"  共 {total} 条 | 展示 Top 50 (按排名)")
    print("=" * 70)
    for i, row in enumerate(rows, 1):
        rank_str = f" #{row['rank']}" if row["rank"] else ""
        pname = row["platform_name"] or row["platform_id"]
        print(f"{i:2}. [{pname}{rank_str}] {row['title']}")

    conn.close()


def read_rss():
    if not os.path.exists(RSS_DB_PATH):
        print("\n  暂无今日 RSS 数据")
        return

    conn = sqlite3.connect(RSS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM rss_items")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT title, feed_id, published FROM rss_items ORDER BY published DESC LIMIT 20"
        )
        rows = cursor.fetchall()

        print("\n" + "=" * 70)
        print(f"  RSS 订阅今日更新 (共 {total} 条)")
        print("=" * 70)
        for i, row in enumerate(rows, 1):
            print(f"{i:2}. [{row['feed_id']}] {row['title']}")
    except Exception as e:
        print(f"\n  RSS 读取失败: {e}")
    finally:
        conn.close()


def read_topics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT p.name, COUNT(*) as cnt
            FROM news_items n
            LEFT JOIN platforms p ON n.platform_id = p.id
            GROUP BY n.platform_id, p.name
            ORDER BY cnt DESC
        """
        )
        rows = cursor.fetchall()

        print("\n" + "=" * 70)
        print("  各平台新闻数量统计")
        print("=" * 70)
        for row in rows:
            print(f"  {row[0]}: {row[1]} 条")

        cursor.execute(
            """
            SELECT n.title, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT p.name) as platforms
            FROM news_items n
            LEFT JOIN platforms p ON n.platform_id = p.id
            GROUP BY n.title
            HAVING cnt > 1
            ORDER BY cnt DESC
            LIMIT 15
        """
        )
        cross = cursor.fetchall()
        if cross:
            print("\n" + "=" * 70)
            print("  跨平台热门话题（多平台同时报道）")
            print("=" * 70)
            for i, row in enumerate(cross, 1):
                print(f"  {i}. {row[0]} (出现{row[1]}次: {row[2]})")
    except Exception as e:
        print(f"\n  话题统计失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    read_news()
    read_rss()
    read_topics()
