import json
import urllib.request
import time

BASE = "http://127.0.0.1:3333/mcp"


def mcp_request(method, params=None, session_id=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=120)
    sid = resp.headers.get("Mcp-Session-Id", session_id or "")
    ct = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ct:
        raw = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            raw += chunk
        text = raw.decode("utf-8", errors="replace")
        lines = text.strip().split("\n")
        dl = ""
        for line in lines:
            if line.startswith("data:"):
                dl = line[5:].strip()
        return sid, json.loads(dl) if dl else {}
    return sid, json.loads(resp.read().decode())


def new_session():
    sid, _ = mcp_request(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "trae-client", "version": "1.0"},
        },
    )
    notif_body = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    headers = {"Content-Type": "application/json", "Mcp-Session-Id": sid}
    req = urllib.request.Request(
        BASE, data=json.dumps(notif_body).encode(), headers=headers, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
    time.sleep(0.3)
    return sid


def call_tool(tool_name, arguments):
    sid = new_session()
    _, resp = mcp_request(
        "tools/call",
        {"name": tool_name, "arguments": arguments},
        session_id=sid,
    )
    content = resp.get("result", {}).get("content", [])
    if content:
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"success": False, "raw": text[:200]}
    err = resp.get("error", {})
    return {"success": False, "error": err}


def extract_items(data):
    raw = data.get("data", {})
    if isinstance(raw, list):
        return raw
    elif isinstance(raw, dict):
        return raw.get("items", [])
    return []


def main():
    print("=" * 70)
    print(f"  TrendRadar 今日热点新闻 ({time.strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    news = call_tool("get_latest_news", {"limit": 50})
    if news.get("success"):
        items = extract_items(news)
        for i, item in enumerate(items[:40], 1):
            title = item.get("title", "")
            platform = item.get("platform_name", item.get("platform", ""))
            rank = item.get("rank", "")
            rank_str = f" #{rank}" if rank else ""
            print(f"{i:2}. [{platform}{rank_str}] {title}")
    else:
        print(f"  获取失败: {news.get('error', news.get('raw', ''))}")

    print("\n" + "=" * 70)
    print("  RSS 订阅今日更新")
    print("=" * 70)

    rss = call_tool("get_latest_rss", {"days": 1, "limit": 20, "include_summary": False})
    if rss.get("success"):
        rss_items = extract_items(rss)
        if rss_items:
            for i, item in enumerate(rss_items[:20], 1):
                title = item.get("title", "")
                feed = item.get("feed_name", item.get("feed_id", ""))
                print(f"{i:2}. [{feed}] {title}")
        else:
            print("  暂无 RSS 数据")
    else:
        print(f"  RSS 获取失败: {rss.get('error', rss.get('raw', ''))}")

    print("\n" + "=" * 70)
    print("  热点话题统计")
    print("=" * 70)

    topics = call_tool("get_trending_topics", {
        "top_n": 15, "mode": "current", "extract_mode": "keywords"
    })
    if topics.get("success"):
        td = topics.get("data", {})
        if isinstance(td, dict):
            for k, v in list(td.items())[:15]:
                if isinstance(v, list):
                    print(f"  {k}: {len(v)} 条相关")
                elif isinstance(v, dict):
                    count = v.get("count", v.get("frequency", "?"))
                    print(f"  {k}: {count}")
                else:
                    print(f"  {k}: {v}")
        elif isinstance(td, list):
            for t in td[:15]:
                word = t.get("word", t.get("keyword", ""))
                count = t.get("count", t.get("frequency", 0))
                print(f"  {word} (出现{count}次)")
    else:
        print(f"  话题获取失败: {topics.get('error', topics.get('raw', ''))}")


if __name__ == "__main__":
    main()
