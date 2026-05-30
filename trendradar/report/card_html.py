# coding=utf-8
"""
卡片式热点播报 HTML 渲染模块

每条新闻以独立卡片展示，支持自动定时刷新、搜索过滤、平台筛选、暗色模式。
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from trendradar.report.helpers import html_escape
from trendradar.ai.formatter import render_ai_analysis_html_rich


def render_card_html_content(
    report_data: Dict,
    total_titles: int,
    mode: str = "current",
    update_info: Optional[Dict] = None,
    *,
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    display_mode: str = "keyword",
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
    show_new_section: bool = True,
    card_config: Optional[Dict] = None,
) -> str:
    if region_order is None:
        region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
    if card_config is None:
        card_config = {}

    auto_refresh_minutes = card_config.get("auto_refresh_minutes", 5)
    cards_per_page = card_config.get("cards_per_page", 50)
    show_ai_summary = card_config.get("show_ai_summary", True)
    default_theme = card_config.get("theme", "light")

    now = get_time_func() if get_time_func else datetime.now()

    all_cards = _collect_all_cards(report_data, rss_items, standalone_data, display_mode)

    if cards_per_page > 0:
        all_cards = all_cards[:cards_per_page]

    platform_list = sorted(set(c["source_name"] for c in all_cards))

    cards_html = _render_cards(all_cards)
    platform_filter_html = _render_platform_filter(platform_list)
    ai_html = render_ai_analysis_html_rich(ai_analysis) if (ai_analysis and show_ai_summary) else ""

    return _build_full_html(
        cards_html=cards_html,
        platform_filter_html=platform_filter_html,
        ai_html=ai_html,
        total_cards=len(all_cards),
        total_titles=total_titles,
        mode=mode,
        now=now,
        auto_refresh_minutes=auto_refresh_minutes,
        default_theme=default_theme,
        update_info=update_info,
    )


def _collect_all_cards(
    report_data: Dict,
    rss_items: Optional[List[Dict]],
    standalone_data: Optional[Dict],
    display_mode: str,
) -> List[Dict]:
    cards = []

    for stat in report_data.get("stats", []):
        keyword = stat.get("word", "")
        for title_data in stat.get("titles", []):
            card = _title_data_to_card(title_data, keyword)
            cards.append(card)

    if rss_items:
        for stat in rss_items:
            keyword = stat.get("word", "")
            for title_data in stat.get("titles", []):
                card = _title_data_to_card(title_data, keyword)
                card["source_type"] = "rss"
                cards.append(card)

    if standalone_data:
        for platform in standalone_data.get("platforms", []):
            platform_name = platform.get("name", platform.get("id", ""))
            for item in platform.get("items", []):
                card = _standalone_item_to_card(item, platform_name)
                cards.append(card)
        for feed in standalone_data.get("rss_feeds", []):
            feed_name = feed.get("name", feed.get("id", ""))
            for item in feed.get("items", []):
                card = _standalone_rss_item_to_card(item, feed_name)
                cards.append(card)

    cards.sort(key=lambda c: (c.get("min_rank", 9999), -c.get("count", 1)))

    return cards


def _title_data_to_card(title_data: Dict, keyword: str) -> Dict:
    ranks = title_data.get("ranks", [])
    min_rank = min(ranks) if ranks else 9999
    max_rank = max(ranks) if ranks else 0

    rank_text = ""
    if min_rank == max_rank and min_rank < 9999:
        rank_text = str(min_rank)
    elif min_rank < 9999:
        rank_text = f"{min_rank}-{max_rank}"

    if min_rank <= 3:
        rank_level = "top"
    elif min_rank <= 10:
        rank_level = "high"
    elif min_rank < 9999:
        rank_level = "normal"
    else:
        rank_level = ""

    return {
        "title": title_data.get("title", ""),
        "url": title_data.get("mobile_url") or title_data.get("url", ""),
        "source_name": title_data.get("source_name", ""),
        "keyword": keyword,
        "rank_text": rank_text,
        "rank_level": rank_level,
        "min_rank": min_rank,
        "time_display": title_data.get("time_display", ""),
        "count": title_data.get("count", 1),
        "is_new": title_data.get("is_new", False),
        "source_type": "hotlist",
    }


def _standalone_item_to_card(item: Dict, platform_name: str) -> Dict:
    ranks = item.get("ranks", [])
    rank = item.get("rank", 0)
    min_rank = min(ranks) if ranks else (rank if rank > 0 else 9999)

    rank_text = ""
    if min_rank < 9999:
        max_rank = max(ranks) if ranks else rank
        rank_text = str(min_rank) if min_rank == max_rank else f"{min_rank}-{max_rank}"

    if min_rank <= 3:
        rank_level = "top"
    elif min_rank <= 10:
        rank_level = "high"
    elif min_rank < 9999:
        rank_level = "normal"
    else:
        rank_level = ""

    first_time = item.get("first_time", "")
    last_time = item.get("last_time", "")
    time_display = ""
    if first_time and last_time and first_time != last_time:
        time_display = f"{first_time}~{last_time}"
    elif first_time:
        time_display = first_time

    return {
        "title": item.get("title", ""),
        "url": item.get("url") or item.get("mobileUrl", ""),
        "source_name": platform_name,
        "keyword": "",
        "rank_text": rank_text,
        "rank_level": rank_level,
        "min_rank": min_rank,
        "time_display": time_display,
        "count": item.get("count", 1),
        "is_new": False,
        "source_type": "standalone",
    }


def _standalone_rss_item_to_card(item: Dict, feed_name: str) -> Dict:
    published_at = item.get("published_at", "")
    time_display = ""
    if published_at:
        try:
            from datetime import datetime as dt
            if "T" in published_at:
                dt_obj = dt.fromisoformat(published_at.replace("Z", "+00:00"))
                time_display = dt_obj.strftime("%m-%d %H:%M")
            else:
                time_display = published_at
        except Exception:
            time_display = published_at

    return {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "source_name": feed_name,
        "keyword": "",
        "rank_text": "",
        "rank_level": "",
        "min_rank": 9999,
        "time_display": time_display,
        "count": 1,
        "is_new": False,
        "source_type": "rss",
    }


def _render_cards(cards: List[Dict]) -> str:
    if not cards:
        return '<div class="empty-state">📭 暂无热点数据</div>'

    html = '<div class="card-grid">'
    for card in cards:
        html += _render_single_card(card)
    html += '</div>'
    return html


def _render_single_card(card: Dict) -> str:
    escaped_title = html_escape(card["title"])
    escaped_source = html_escape(card["source_name"])
    escaped_keyword = html_escape(card.get("keyword", ""))
    escaped_url = html_escape(card["url"]) if card["url"] else ""
    escaped_time = html_escape(card.get("time_display", ""))

    rank_html = ""
    if card.get("rank_text"):
        level = card.get("rank_level", "")
        rank_html = f'<span class="rank-badge {level}">#{card["rank_text"]}</span>'

    new_badge = '<span class="new-badge">NEW</span>' if card.get("is_new") else ""

    keyword_html = ""
    if escaped_keyword:
        keyword_html = f'<span class="keyword-tag">{escaped_keyword}</span>'

    count_html = ""
    if card.get("count", 1) > 1:
        count_html = f'<span class="count-info">{card["count"]}次</span>'

    time_html = ""
    if escaped_time:
        time_html = f'<span class="time-info">{escaped_time}</span>'

    title_html = escaped_title
    if escaped_url:
        title_html = f'<a href="{escaped_url}" target="_blank" class="card-title-link">{escaped_title}</a>'

    return f"""
    <div class="news-card" data-source="{escaped_source}" data-keyword="{escaped_keyword}">
        <div class="card-header">
            {rank_html}
            <span class="source-label">{escaped_source}</span>
            {new_badge}
        </div>
        <div class="card-title">{title_html}</div>
        <div class="card-footer">
            {time_html}
            {count_html}
            {keyword_html}
        </div>
    </div>"""


def _render_platform_filter(platforms: List[str]) -> str:
    if not platforms:
        return ""

    html = '<div class="filter-bar">'
    html += '<button class="filter-btn active" data-source="all">全部</button>'
    for name in platforms:
        escaped = html_escape(name)
        html += f'<button class="filter-btn" data-source="{escaped}">{escaped}</button>'
    html += '</div>'
    return html


def _build_full_html(
    cards_html: str,
    platform_filter_html: str,
    ai_html: str,
    total_cards: int,
    total_titles: int,
    mode: str,
    now: datetime,
    auto_refresh_minutes: int,
    default_theme: str,
    update_info: Optional[Dict],
) -> str:
    mode_display = {"current": "当前榜单", "incremental": "增量分析", "daily": "全天汇总"}.get(mode, "热点播报")
    update_time = now.strftime("%Y-%m-%d %H:%M:%S")
    theme_class = "dark-mode" if default_theme == "dark" else ""

    update_info_html = ""
    if update_info:
        update_info_html = f'<span class="update-notice">发现新版本 {update_info["remote_version"]}，当前 {update_info["current_version"]}</span>'

    ai_section_html = ""
    if ai_html:
        ai_section_html = f"""
        <div class="ai-section">
            <div class="ai-section-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <span class="ai-section-title">🤖 AI 分析</span>
                <span class="ai-toggle">▼</span>
            </div>
            <div class="ai-section-body">{ai_html}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>热点播报 - TrendRadar</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
            background: #f0f2f5;
            color: #1a1a1a;
            line-height: 1.5;
            min-height: 100vh;
        }}

        body.dark-mode {{
            background: #0f172a;
            color: #e2e8f0;
        }}

        .top-bar {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }}

        body.dark-mode .top-bar {{
            background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 100%);
        }}

        .top-bar-inner {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .top-bar-left {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .top-bar-title {{
            font-size: 20px;
            font-weight: 700;
        }}

        .top-bar-meta {{
            font-size: 13px;
            opacity: 0.9;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .refresh-countdown {{
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-variant-numeric: tabular-nums;
        }}

        .top-bar-right {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .search-input {{
            padding: 8px 14px;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            background: rgba(255,255,255,0.15);
            color: white;
            font-size: 14px;
            width: 200px;
            outline: none;
            backdrop-filter: blur(10px);
        }}

        .search-input::placeholder {{ color: rgba(255,255,255,0.6); }}
        .search-input:focus {{ border-color: rgba(255,255,255,0.6); background: rgba(255,255,255,0.25); }}

        .icon-btn {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }}

        .icon-btn:hover {{ background: rgba(255,255,255,0.3); }}

        .main-content {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px 24px;
        }}

        .stats-bar {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 16px;
            font-size: 14px;
            color: #6b7280;
        }}

        body.dark-mode .stats-bar {{ color: #94a3b8; }}

        .stats-bar strong {{ color: #4f46e5; }}
        body.dark-mode .stats-bar strong {{ color: #818cf8; }}

        .filter-bar {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            padding: 6px 14px;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            background: white;
            color: #6b7280;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .filter-btn:hover {{ border-color: #4f46e5; color: #4f46e5; }}
        .filter-btn.active {{ background: #4f46e5; color: white; border-color: #4f46e5; }}

        body.dark-mode .filter-btn {{
            background: #1e293b;
            border-color: #334155;
            color: #94a3b8;
        }}
        body.dark-mode .filter-btn:hover {{ border-color: #818cf8; color: #818cf8; }}
        body.dark-mode .filter-btn.active {{ background: #4f46e5; color: white; border-color: #4f46e5; }}

        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px;
        }}

        .news-card {{
            background: white;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 10px;
            animation: fadeIn 0.3s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .news-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }}

        body.dark-mode .news-card {{
            background: #1e293b;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        body.dark-mode .news-card:hover {{
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .rank-badge {{
            font-size: 12px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 10px;
            color: white;
            min-width: 28px;
            text-align: center;
        }}

        .rank-badge.top {{ background: linear-gradient(135deg, #dc2626, #ef4444); }}
        .rank-badge.high {{ background: #ea580c; }}
        .rank-badge.normal {{ background: #6b7280; }}

        .source-label {{
            font-size: 12px;
            color: #9ca3af;
            margin-left: auto;
        }}

        body.dark-mode .source-label {{ color: #64748b; }}

        .new-badge {{
            background: linear-gradient(135deg, #f59e0b, #fbbf24);
            color: #92400e;
            font-size: 10px;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}

        .card-title {{
            font-size: 15px;
            line-height: 1.5;
            color: #1a1a1a;
            font-weight: 500;
        }}

        body.dark-mode .card-title {{ color: #e2e8f0; }}

        .card-title-link {{
            color: #1a1a1a;
            text-decoration: none;
        }}

        .card-title-link:hover {{ color: #4f46e5; text-decoration: underline; }}
        body.dark-mode .card-title-link {{ color: #e2e8f0; }}
        body.dark-mode .card-title-link:hover {{ color: #818cf8; }}

        .card-footer {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            font-size: 12px;
        }}

        .time-info {{ color: #9ca3af; }}
        body.dark-mode .time-info {{ color: #64748b; }}

        .count-info {{ color: #059669; font-weight: 500; }}
        body.dark-mode .count-info {{ color: #34d399; }}

        .keyword-tag {{
            color: #2563eb;
            background: #eff6ff;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 11px;
        }}

        body.dark-mode .keyword-tag {{
            color: #93c5fd;
            background: #1e3a5f;
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #9ca3af;
            font-size: 16px;
        }}

        .ai-section {{
            margin-top: 32px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 12px;
            border: 1px solid #bae6fd;
            overflow: hidden;
        }}

        body.dark-mode .ai-section {{
            background: linear-gradient(135deg, #0c4a6e 0%, #164e63 100%);
            border-color: #155e75;
        }}

        .ai-section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            cursor: pointer;
            user-select: none;
        }}

        .ai-section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #0369a1;
        }}

        body.dark-mode .ai-section-title {{ color: #7dd3fc; }}

        .ai-toggle {{ font-size: 12px; color: #0369a1; transition: transform 0.2s; }}
        body.dark-mode .ai-toggle {{ color: #7dd3fc; }}
        .ai-section.collapsed .ai-toggle {{ transform: rotate(-90deg); }}
        .ai-section.collapsed .ai-section-body {{ display: none; }}

        .ai-section-body {{ padding: 0 20px 20px; }}

        .footer {{
            text-align: center;
            padding: 24px;
            color: #9ca3af;
            font-size: 13px;
        }}

        body.dark-mode .footer {{ color: #64748b; }}

        .footer a {{
            color: #4f46e5;
            text-decoration: none;
            font-weight: 500;
        }}

        .footer a:hover {{ text-decoration: underline; }}
        body.dark-mode .footer a {{ color: #818cf8; }}

        .update-notice {{
            color: #ea580c;
            font-weight: 500;
            margin-left: 8px;
        }}

        @media (max-width: 768px) {{
            .top-bar-inner {{ flex-direction: column; align-items: flex-start; }}
            .search-input {{ width: 100%; }}
            .card-grid {{ grid-template-columns: 1fr; }}
            .main-content {{ padding: 12px; }}
        }}

        @media (min-width: 769px) and (max-width: 1024px) {{
            .card-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body class="{theme_class}">
    <div class="top-bar">
        <div class="top-bar-inner">
            <div class="top-bar-left">
                <div class="top-bar-title">📡 热点播报</div>
                <div class="top-bar-meta">
                    <span>{mode_display}</span>
                    <span>·</span>
                    <span>{update_time}</span>
                    <span class="refresh-countdown" id="countdown">{auto_refresh_minutes}:00</span>
                </div>
            </div>
            <div class="top-bar-right">
                <input type="text" class="search-input" id="searchInput" placeholder="搜索热点..." oninput="handleSearch(this.value)">
                <button class="icon-btn" onclick="toggleDarkMode()" title="切换暗色模式" id="darkBtn">☽</button>
            </div>
        </div>
    </div>

    <div class="main-content">
        <div class="stats-bar">
            <span>共 <strong>{total_cards}</strong> 条热点</span>
            <span>·</span>
            <span>新闻总数 <strong>{total_titles}</strong></span>
            {update_info_html}
        </div>

        {platform_filter_html}

        {cards_html}

        {ai_section_html}

        <div class="footer">
            由 <strong>TrendRadar</strong> 生成 ·
            <a href="https://github.com/sansan0/TrendRadar" target="_blank">GitHub 开源项目</a>
        </div>
    </div>

    <script>
        var REFRESH_MINUTES = {auto_refresh_minutes};
        var remainingSeconds = REFRESH_MINUTES * 60;

        function updateCountdown() {{
            remainingSeconds--;
            if (remainingSeconds <= 0) {{
                location.reload();
                return;
            }}
            var m = Math.floor(remainingSeconds / 60);
            var s = remainingSeconds % 60;
            var el = document.getElementById('countdown');
            if (el) el.textContent = m + ':' + (s < 10 ? '0' : '') + s;
        }}

        setInterval(updateCountdown, 1000);

        function handleSearch(query) {{
            query = query.toLowerCase();
            document.querySelectorAll('.news-card').forEach(function(card) {{
                var title = (card.querySelector('.card-title') || {{}}).textContent || '';
                card.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
            }});
        }}

        document.querySelectorAll('.filter-btn').forEach(function(btn) {{
            btn.addEventListener('click', function() {{
                document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
                btn.classList.add('active');
                var source = btn.getAttribute('data-source');
                document.querySelectorAll('.news-card').forEach(function(card) {{
                    if (source === 'all') {{
                        card.style.display = '';
                    }} else {{
                        card.style.display = card.getAttribute('data-source') === source ? '' : 'none';
                    }}
                }});
            }});
        }});

        function toggleDarkMode() {{
            var isDark = document.body.classList.toggle('dark-mode');
            try {{ localStorage.setItem('trendradar-card-dark', isDark ? '1' : '0'); }} catch(e) {{}}
            var btn = document.getElementById('darkBtn');
            if (btn) btn.textContent = isDark ? '☀' : '☽';
        }}

        (function() {{
            try {{
                var saved = localStorage.getItem('trendradar-card-dark');
                if (saved === '1') {{
                    document.body.classList.add('dark-mode');
                    var btn = document.getElementById('darkBtn');
                    if (btn) btn.textContent = '☀';
                }}
            }} catch(e) {{}}
        }})();
    </script>
</body>
</html>"""
