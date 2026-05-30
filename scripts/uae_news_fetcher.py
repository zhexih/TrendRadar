"""
UAE 地区新闻数据抓取器（独立运行，不依赖 TrendRadar 服务）
=========================================================
功能：抓取 Google News UAE 区域 RSS，按零售品类关键词筛选
输出：output/reports/uae_news_YYYY-MM-DD.json + 集成到监控简报
"""
import requests
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "output" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# UAE 新闻 RSS 源
UAE_RSS_FEEDS = [
    {
        "id": "google-news-uae-en",
        "name": "Google News UAE",
        "url": "https://news.google.com/rss?hl=en-US&gl=AE&ceid=AE:en"
    },
    {
        "id": "google-news-uae-business",
        "name": "阿联酋商业新闻",
        "url": "https://news.google.com/rss/search?q=UAE+business+retail+economy&hl=en-US&gl=AE&ceid=AE:en"
    },
    {
        "id": "google-news-dubai-retail",
        "name": "迪拜零售新闻",
        "url": "https://news.google.com/rss/search?q=Dubai+shopping+retail+mall+consumer&hl=en-US&gl=AE&ceid=AE:en"
    },
    {
        "id": "google-news-gulf-business",
        "name": "海湾经济新闻",
        "url": "https://news.google.com/rss/search?q=Gulf+UAE+retail+market+trend&hl=en-US&gl=AE&ceid=AE:en"
    },
]

# UAE 零售监控关键词（与 YAML 配置同步）
UAE_KEYWORDS = {
    "商业零售": ["Dubai Mall", "Mall of the Emirates", "Dubai shopping", "UAE retail",
                "UAE consumer spending", "UAE mall", "Dubai Festival City", "Yas Mall",
                "Marina Mall", "Ibn Battuta Mall", "City Centre Deira", "City Centre Mirdif"],
    "经济政策": ["UAE economy", "Dubai economy", "UAE GDP", "UAE inflation",
                "UAE interest rate", "UAE Central Bank", "UAE budget", "UAE trade"],
    "人口与旅游": ["Dubai tourism", "Dubai visitors", "UAE tourism", "Dubai population",
                  "UAE expat", "Dubai travel", "Dubai airport", "DXB", "Dubai hotel"],
    "物流与供应": ["Dubai logistics", "Jebel Ali", "UAE supply chain",
                  "UAE shipping", "Dubai port", "UAE import", "UAE export", "Dubai cargo"],
    "竞争与市场": ["MINISO", "Daiso", "Muji", "UAE dollar store",
                  "UAE lifestyle retail", "Dubai retail competition"],
    "天气与季节": ["UAE weather", "Dubai temperature", "UAE heatwave",
                  "Dubai rain", "UAE sandstorm", "Dubai summer", "UAE flood"],
    "汇率与成本": ["AED exchange rate", "AED to USD", "UAE dollar peg",
                  "UAE fuel price", "UAE labor cost", "UAE minimum wage"],
}

def parse_rss(xml_text):
    """解析 RSS XML，提取文章列表"""
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            source = item.find("source")

            items.append({
                "title": title.text if title is not None else "",
                "url": link.text if link is not None else "",
                "published": pub_date.text if pub_date is not None else "",
                "source_name": source.text if source is not None else "",
            })
    except ET.ParseError as e:
        print(f"  XML 解析错误: {e}")
    return items

def fetch_feed(feed_config):
    """抓取单个 RSS 源"""
    print(f"  抓取: {feed_config['name']}...", end=" ")
    try:
        resp = requests.get(feed_config["url"], timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        items = parse_rss(resp.text)
        print(f"获取 {len(items)} 条")
        return items
    except requests.Timeout:
        print("超时")
        return []
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return []

def match_keywords(items, keywords_dict):
    """按关键词匹配并分类"""
    results = {}
    for cat_name, keywords in keywords_dict.items():
        matched = []
        for item in items:
            title_lower = item["title"].lower()
            for kw in keywords:
                if kw.lower() in title_lower:
                    if item not in matched:
                        matched.append({**item, "matched_keyword": kw})
                        break
        if matched:
            results[cat_name] = matched
    return results

def generate_summary(all_items, matched_results):
    """生成摘要"""
    today = datetime.now().strftime("%Y-%m-%d")
    total_all = sum(len(items) for items in all_items.values())
    total_matched = sum(len(items) for items in matched_results.values())

    lines = []
    lines.append("## 🌍 UAE 地区零售监控")
    lines.append(f"**抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}**")
    lines.append(f"**总文章数：{total_all} | 零售相关：{total_matched}**")
    lines.append("")

    if matched_results:
        for cat_name, items in matched_results.items():
            lines.append(f"### {cat_name}（{len(items)} 条匹配）")
            lines.append("| 标题 | 来源 | 匹配词 |")
            lines.append("|------|------|--------|")
            for item in items[:5]:
                source = item.get("source_name", "") or item.get("source", "")
                lines.append(f'| [{item["title"]}]({item["url"]}) | {source} | {item["matched_keyword"]} |')
            lines.append("")
    else:
        lines.append("*今日未匹配到零售相关的 UAE 本地新闻*")
        lines.append("")

    return "\n".join(lines)

def main():
    print("=== UAE 新闻数据抓取器 ===")
    print()

    all_news = {}
    for feed in UAE_RSS_FEEDS:
        items = fetch_feed(feed)
        if items:
            all_news[feed["name"]] = items

    print()

    # 按关键词匹配
    flat_all = []
    for source, items in all_news.items():
        for item in items:
            flat_all.append({**item, "source": source})

    matched = match_keywords(flat_all, UAE_KEYWORDS)

    total_matched = sum(len(v) for v in matched.values())
    print(f"总计获取 {len(flat_all)} 篇，零售相关匹配 {total_matched} 篇")
    print()

    # 保存 JSON
    today = datetime.now().strftime("%Y-%m-%d")
    data = {
        "date": today,
        "fetch_time": datetime.now().isoformat(),
        "total_articles": len(flat_all),
        "matched_count": total_matched,
        "feeds": {source: items for source, items in all_news.items()},
        "matched_by_category": {cat: items for cat, items in matched.items()},
    }
    json_path = REPORT_DIR / f"uae_news_{today}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON 已保存: {json_path}")

    # 生成摘要
    summary = generate_summary(all_news, matched)
    summary_path = REPORT_DIR / f"uae_summary_{today}.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"摘要已保存: {summary_path}")

if __name__ == "__main__":
    main()
