import json
import urllib.request
import time

BASE = "http://127.0.0.1:3333/mcp"

def request(method, params=None, session_id=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        body["params"] = params
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    req = urllib.request.Request(BASE, data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=60)
    sid = resp.headers.get("Mcp-Session-Id", "")
    content_type = resp.headers.get("Content-Type", "")

    if "text/event-stream" in content_type:
        raw = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            raw += chunk
        text = raw.decode("utf-8", errors="replace")
        lines = text.strip().split("\n")
        data_line = ""
        for line in lines:
            if line.startswith("data:"):
                data_line = line[5:].strip()
        return sid, json.loads(data_line) if data_line else {}
    else:
        return sid, json.loads(resp.read().decode())

# 1. Initialize
sid, _ = request("initialize", {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {"name": "test", "version": "1.0"}
})
print(f"Session: {sid[:20]}...")

# 2. Initialized
_, _ = request("notifications/initialized", session_id=sid)
time.sleep(0.5)

# 3. Trigger crawl
print("正在爬取新闻...")
_, crawl_result = request("tools/call", {
    "name": "trigger_crawl",
    "arguments": {"platforms": [], "save_to_local": True}
}, session_id=sid)
print("爬取完成!")

time.sleep(1)

# 4. Get latest news
print("获取今日热点...")
_, news_result = request("tools/call", {
    "name": "get_latest_news",
    "arguments": {"limit": 15}
}, session_id=sid)

content = news_result.get("result", {}).get("content", [])
if content:
    text = content[0].get("text", "")
    data = json.loads(text)
    if data.get("success"):
        news_items = data.get("data", [])
        print(f"\n{'='*60}")
        print(f"今日热点新闻 ({len(news_items)} 条)")
        print(f"{'='*60}")
        for i, item in enumerate(news_items[:15], 1):
            title = item.get("title", "无标题")
            platform = item.get("platform", "未知")
            rank = item.get("rank", "")
            rank_str = f" #{rank}" if rank else ""
            print(f"{i:2}. [{platform}{rank_str}] {title}")
    else:
        print("获取失败:", data.get("error", {}).get("message"))
else:
    print("无内容返回")
