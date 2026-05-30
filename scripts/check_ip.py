import json

with open(r'd:\Trea study\TrendRadar\output\reports\uae_news_2026-05-07.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ip_kw = [
    'Disney', 'Marvel', 'Sanrio', 'Pokemon', 'Hello Kitty', 'Kuromi', 'My Melody',
    'Cinnamoroll', 'Naruto', 'One Piece', 'Dragon Ball', 'Demon Slayer',
    'Spy Family', 'Haikyuu', 'Slam Dunk', 'Detective Conan', 'Jujutsu Kaisen',
    'Genshin', 'Honkai', 'Barbie', 'Transformers', 'Harry Potter', 'Star Wars',
    'Minions', 'Frozen', 'Toy Story', 'Pixar', 'Warner Bros', 'Universal Studios',
    'Spider-Man', 'Iron Man', 'Avengers', 'Batman', 'Superman',
    'Snoopy', 'Peanuts', 'Winnie the Pooh', 'Mickey Mouse', 'Donald Duck',
    'Bluey', 'Paw Patrol', 'Peppa Pig', 'Thomas the Tank Engine',
    'Capybara', 'Chiikawa', 'Line Friends', 'BT21', 'Miffy', 'Molang',
    'animation', 'anime', 'manga', 'character', 'collaboration', 'collab',
    'licensed', 'franchise', 'IP partnership', 'brand partnership',
    'pop culture', 'merchandise', 'collectible', 'limited edition',
]

matched = []
for feed_name, items in data.get('feeds', {}).items():
    for item in items:
        title = item.get('title', '').lower()
        for kw in ip_kw:
            if kw.lower() in title:
                matched.append({
                    'title': item['title'],
                    'source': item.get('source_name', ''),
                    'kw': kw,
                    'feed': feed_name
                })
                break

print(f'IP相关匹配: {len(matched)} 条 / 共 {data["total_articles"]} 篇')
print()

if matched:
    for m in matched:
        print(f'  [{m["kw"]}] {m["title"]}')
        print(f'         来源: {m["source"]} ({m["feed"]})')
        print()
else:
    print('未匹配到任何IP相关新闻。')
    print()
    print('可能是以下原因:')
    print('  1. 当前 RSS 源侧重经济/商业新闻，不包含IP娱乐新闻')
    print('  2. 需要添加娱乐/流行文化/动漫类 RSS 源')
    print('  3. IP 合作新闻通常在专业媒体而非综合新闻中出现')
