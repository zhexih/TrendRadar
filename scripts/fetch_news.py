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
    resp = urllib.request.urlopen(req, timeout=30)
    sid = resp.headers.get("Mcp-Session-Id", "")
    content_type = resp.headers.get("Content-Type", "")

    # 如果返回的是 SSE，读取 SSE 流提取数据
    if "text/event-stream" in content_type:
        raw = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            raw += chunk
        text = raw.decode("utf-8", errors="replace")
        # 解析 SSE: 找 data: 行
        lines = text.strip().split("\n")
        data_line = ""
        for line in lines:
            if line.startswith("data:"):
                data_line = line[5:].strip()
        return sid, json.loads(data_line) if data_line else {}
    else:
        return sid, json.loads(resp.read().decode())

# 1. Initialize
sid, init_result = request("initialize", {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {"name": "test", "version": "1.0"}
})
print(f"Session: {sid[:20]}...")

# 2. Send initialized notification
_, _ = request("notifications/initialized", session_id=sid)

time.sleep(0.5)

# 3. Get latest news
_, news_result = request("tools/call", {
    "name": "get_latest_news",
    "arguments": {"limit": 15}
}, session_id=sid)

# 4. Display
print("=" * 60)
print("今日热点新闻")
print("=" * 60)

content = news_result.get("content", [])
if content:
    text = content[0].get("text", "")
    lines = text.split("\n")
    for line in lines[:50]:
        print(line)
else:
    print("无新闻数据")
    print("Raw:", json.dumps(news_result, ensure_ascii=False, indent=2)[:2000])
