"""
零售品类社交媒体热度监控简报生成器
=====================================
功能：读取 TrendRadar 热搜数据，按品类关键词匹配，生成每日监控简报
数据源：热搜数据库 + RSS 数据库（含 UAE 新闻源）
配置：config/retail_keywords.yaml
输出：output/reports/retail_monitor_YYYY-MM-DD.md
"""
import sqlite3
import yaml
import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "news"
RSS_DIR = BASE_DIR / "output" / "rss"
REPORT_DIR = BASE_DIR / "output" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def load_config():
    with open(BASE_DIR / "config" / "retail_keywords.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_keywords(config):
    """从配置中提取所有品类关键词（展开嵌套结构）"""
    categories = {}
    for cat_name, cat_info in config["monitoring_categories"].items():
        keywords = cat_info.get("搜索关键词", [])
        if isinstance(keywords, dict):
            flat_kw = []
            for group_name, kw_list in keywords.items():
                flat_kw.extend(kw_list)
            categories[cat_name] = flat_kw
        else:
            categories[cat_name] = keywords
    return categories

def heat_score(rank, thresholds):
    if rank <= 3: return thresholds.get("1-3", 10)
    if rank <= 10: return thresholds.get("4-10", 6)
    if rank <= 20: return thresholds.get("11-20", 3)
    return 1

def query_hotlist_db(db_path, keywords):
    """从热搜数据库查询匹配项"""
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    results = {}
    for kw in keywords:
        try:
            cur.execute(
                "SELECT title, platform_id, rank, crawl_count FROM news_items WHERE title LIKE ? ORDER BY rank",
                (f"%{kw}%",)
            )
            for row in cur.fetchall():
                key = (row[0], row[1])
                if key not in results or row[2] < results[key]["rank"]:
                    results[key] = {"title": row[0], "platform": row[1], "rank": row[2], "count": row[3]}
        except Exception:
            pass
    conn.close()
    return results

def query_rss_db(db_path, keywords):
    """从 RSS 数据库查询匹配项"""
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    results = {}
    for kw in keywords:
        try:
            cur.execute(
                "SELECT title, feed_id, published_at, url FROM rss_items WHERE title LIKE ? ORDER BY published_at DESC",
                (f"%{kw}%",)
            )
            for row in cur.fetchall():
                key = (row[0], row[1])
                results[key] = {"title": row[0], "source": row[1], "published": row[2], "url": row[3]}
        except Exception:
            pass
    conn.close()
    return results

def calculate_scores(categories_kw, hotlist_db, rss_db, score_config):
    """计算各品类热度"""
    rank_weights = score_config["rank_weight"]
    results = []
    for cat_name, keywords in categories_kw.items():
        # 热搜数据
        hotlist_results = query_hotlist_db(hotlist_db, keywords)
        h_total = sum(heat_score(v["rank"], rank_weights) for v in hotlist_results.values())
        # RSS 数据
        rss_results = query_rss_db(rss_db, keywords)
        r_total = len(rss_results) * 4

        total = h_total + r_total
        results.append({
            "category": cat_name,
            "heat": total,
            "hotlist_hits": len(hotlist_results),
            "rss_hits": len(rss_results),
            "hotlist_items": list(hotlist_results.values()),
            "rss_items": list(rss_results.values()),
        })
    results.sort(key=lambda x: x["heat"], reverse=True)
    return results

def classify_alert(heat, thresholds_config):
    """根据热度分类预警级别"""
    red_t, yellow_t = thresholds_config["red_alert"], thresholds_config["yellow_alert"]
    red_n = int(re.search(r">(\d+)", red_t).group(1))
    yellow_n = int(re.search(r">(\d+)", yellow_t).group(1))
    if heat > red_n: return ("red", "🔴")
    if heat > yellow_n: return ("yellow", "🟡")
    return ("green", "🟢")

def generate_report(date_str, scores, categories_kw, thresholds_config):
    """生成 Markdown 简报"""
    # 读取 UAE News 数据
    uae_json_path = REPORT_DIR / f"uae_news_{date_str}.json"
    uae_data = None
    if os.path.exists(uae_json_path):
        with open(uae_json_path, "r", encoding="utf-8") as f:
            uae_data = json.load(f)

    lines = []
    lines.append(f"# 🔥 零售品类社媒热度监控简报")
    lines.append(f"**日期：{date_str}**")
    sources = "热搜榜单 + Google News UAE RSS"
    lines.append(f"**数据源：{sources}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 热度总览")
    lines.append("")
    lines.append("| 品类 | 热度 | 热搜命中 | RSS命中 | 信号 |")
    lines.append("|------|------|---------|---------|------|")
    for r in scores:
        level, emoji = classify_alert(r["heat"], thresholds_config)
        bar = "█" * min(r["heat"] // 3, 10)
        lines.append(f'| {r["category"]} | {r["heat"]} {bar} | {r["hotlist_hits"]} | {r["rss_hits"]} | {emoji} {level} |')
    lines.append("")
    lines.append("---")
    lines.append("")

    # 高热度信号
    high = [r for r in scores if r["heat"] > 10]
    if high:
        lines.append("## 🔴🟡 需关注信号（中文热搜）")
        lines.append("")
        for r in high:
            lines.append(f"### {r['category']}（热度 {r['heat']}）")
            lines.append("")
            if r["hotlist_items"]:
                lines.append("| 标题 | 平台 | 排名 | 库存含义 |")
                lines.append("|------|------|------|---------|")
                for item in r["hotlist_items"][:5]:
                    lines.append(f'| {item["title"]} | {item["platform"]} | #{item["rank"]} | 关注相关品类需求变化 |')
                lines.append("")
            lines.append("---")
            lines.append("")
    else:
        lines.append("## 🔴🟡 需关注信号")
        lines.append("*中文热搜端今日无高热度零售信号*")
        lines.append("")
        lines.append("---")
        lines.append("")

    # UAE 地区专属信号
    if uae_data and uae_data.get("matched_count", 0) > 0:
        lines.append("## 🌍 UAE 地区零售监控")
        lines.append(f"**抓取文章：{uae_data['total_articles']} 篇 | 零售相关：{uae_data['matched_count']} 篇**")
        lines.append("")

        if "matched_by_category" in uae_data:
            for cat_name, items in uae_data["matched_by_category"].items():
                lines.append(f"### {cat_name}（{len(items)} 条）")
                lines.append("| 标题 | 来源 | 对库存运营的含义 |")
                lines.append("|------|------|-----------------|")
                for item in items[:5]:
                    implication = get_uae_implication(cat_name, item["title"], item.get("matched_keyword", ""))
                    lines.append(f'| [{item["title"]}]({item.get("url", "")}) | {item.get("source_name", item.get("source", ""))} | {implication} |')
                lines.append("")
        lines.append("---")
        lines.append("")

    # 正常品类
    normal = [r for r in scores if r["heat"] <= 10]
    if normal:
        lines.append("## 🟢 正常品类（中文热搜端）")
        lines.append(f"以下品类今日无异常热搜信号：{', '.join(r['category'] for r in normal)}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 品类关键词覆盖
    lines.append("## 📋 今日监控覆盖")
    total_kw = sum(len(kw) for kw in categories_kw.values())
    lines.append(f"**{len(categories_kw)} 个品类 | ~{total_kw} 个关键词**")
    lines.append("")
    lines.append("---")
    lines.append(f"*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} | TrendRadar 零售监控系统 v1.0*")

    return "\n".join(lines)

def get_uae_implication(category, title, keyword):
    """根据 UAE 新闻类别生成库存运营含义"""
    implications = {
        "商业零售": "UAE 零售市场动态 → 关注各门店客流趋势和品类结构调整",
        "经济政策": "宏观经济信号 → 影响消费者购买力和库存预算",
        "人口与旅游": "人口/旅游变化 → 直接影响门店客流量，调整备货量",
        "物流与供应": "物流/供应链信号 → 影响补货周期和运输成本",
        "竞争与市场": "竞品/市场动态 → 关注份额变化和差异化选品机会",
        "天气与季节": "天气/季节事件 → 驱动季节性品类需求变化",
        "汇率与成本": "汇率/成本变动 → 影响进口成本和定价策略",
    }
    return implications.get(category, "关注相关变化对库存策略的影响")

def main():
    config = load_config()
    categories_kw = load_keywords(config)
    score_config = config["hot_score"]
    thresholds_config = config["alert_thresholds"]

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    hotlist_db = OUTPUT_DIR / f"{today}.db"
    if not os.path.exists(hotlist_db):
        hotlist_db = OUTPUT_DIR / f"{yesterday}.db"

    rss_db = RSS_DIR / f"{today}.db"
    if not os.path.exists(rss_db):
        rss_db = RSS_DIR / f"{yesterday}.db"

    print(f"热搜数据库: {hotlist_db} (存在: {os.path.exists(hotlist_db)})")
    print(f"RSS 数据库: {rss_db} (存在: {os.path.exists(rss_db)})")

    scores = calculate_scores(categories_kw, str(hotlist_db), str(rss_db), score_config)

    report = generate_report(today, scores, categories_kw, thresholds_config)

    report_path = REPORT_DIR / f"retail_monitor_{today}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n简报已生成: {report_path}")
    print(f"\n=== 热度排行 ===")
    for r in scores:
        level, emoji = classify_alert(r["heat"], thresholds_config)
        print(f"  {emoji} {r['category']:10s} 热度={r['heat']:>3d}  热搜命中={r['hotlist_hits']}  RSS命中={r['rss_hits']}")

if __name__ == "__main__":
    main()
