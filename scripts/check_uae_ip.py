import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime

# IP 专用 Google News 搜索（UAE区域）
UAE_IP_SEARCHES = [
    {"name": "Disney UAE", "url": "https://news.google.com/rss/search?q=Disney+store+UAE+Dubai&hl=en&gl=AE&ceid=AE:en"},
    {"name": "MINISO IP collaboration", "url": "https://news.google.com/rss/search?q=MINISO+IP+collaboration+collection+UAE&hl=en&gl=AE&ceid=AE:en"},
    {"name": "Sanrio/Hello Kitty UAE", "url": "https://news.google.com/rss/search?q=Sanrio+Hello+Kitty+Kuromi+UAE+Dubai&hl=en&gl=AE&ceid=AE:en"},
    {"name": "Anime/manga Gulf", "url": "https://news.google.com/rss/search?q=anime+manga+pop+culture+merchandise+Dubai+Gulf&hl=en&gl=AE&ceid=AE:en"},
    {"name": "Pokemon/Marvel GCC", "url": "https://news.google.com/rss/search?q=Pokemon+Marvel+Star+Wars+collaboration+GCC+Dubai&hl=en&gl=AE&ceid=AE:en"},
    {"name": "Toy trends UAE kids", "url": "https://news.google.com/rss/search?q=kids+toys+trends+Dubai+UAE+popular+characters&hl=en&gl=AE&ceid=AE:en"},
    {"name": "Licensed merchandise Gulf", "url": "https://news.google.com/rss/search?q=licensed+merchandise+collectible+toys+Dubai+UAE&hl=en&gl=AE&ceid=AE:en"},
    {"name": "Retail collaboration UAE", "url": "https://news.google.com/rss/search?q=retail+collaboration+limited+edition+launch+Dubai+UAE&hl=en&gl=AE&ceid=AE:en"},
]

def parse_rss(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title = item.find("title")
            link = item.find("link")
            source_el = item.find("source")
            items.append({
                "title": title.text.strip() if title is not None and title.text else "",
                "url": link.text if link is not None and link.text else "",
                "source_name": source_el.text if source_el is not None and source_el.text else "",
            })
    except Exception:
        pass
    return items

all_results = []
total_articles = 0

print("=== UAE IP/娱乐热点搜索 ===")
print()

for search in UAE_IP_SEARCHES:
    print(f"搜索: {search['name']}...", end=" ")
    try:
        resp = requests.get(search["url"], timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        items = parse_rss(resp.text)
        total_articles += len(items)
        print(f"{len(items)} 篇")
        for item in items:
            all_results.append({**item, "search_topic": search["name"]})
    except Exception as e:
        print(f"失败: {e}")

print()
print(f"总计: {total_articles} 篇")

# 找出最相关的
ip_signal_kw = [
    'MINISO', 'Disney', 'Sanrio', 'Hello Kitty', 'Pokemon', 'Marvel',
    'collection', 'collaboration', 'collab', 'limited edition', 'launch',
    'new store', 'flagship', 'opening', 'exclusive', 'partnership',
    'anime', 'manga', 'character', 'licensed', 'franchise',
    'plush', 'figure', 'blind box', 'collectible', 'toy',
]

print()
print("=== 🔥 重点IP信号 ===")
count = 0
seen = set()
for item in all_results:
    title = item["title"].lower()
    if title in seen:
        continue
    seen.add(title)
    signals = [kw for kw in ip_signal_kw if kw.lower() in title]
    if len(signals) >= 2:  # 至少匹配2个信号词
        count += 1
        print(f"\n📰 {item['title']}")
        print(f"   信号词: {', '.join(signals)}")
        print(f"   来源: {item['source_name']}")
        print(f"   搜索: {item['search_topic']}")

print(f"\n共发现 {count} 条高相关性IP新闻")

# 保存
today = datetime.now().strftime("%Y-%m-%d")
output_path = rf"d:\Trea study\TrendRadar\output\reports\uae_ip_{today}.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
        "date": today,
        "total_articles": total_articles,
        "high_signals": count,
        "all_results": all_results,
    }, f, ensure_ascii=False, indent=2, default=str)

print(f"\n数据已保存: {output_path}")
