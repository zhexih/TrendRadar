import json
import urllib.request
import time
import sqlite3
import os

# 先直接从 SQLite 读取
db_path = r"d:\Trea study\TrendRadar\output\news\2026-05-07.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT title, platform, rank, weight FROM news ORDER BY weight DESC LIMIT 15")
    rows = cursor.fetchall()
    conn.close()
    
    print("=" * 60)
    print(f"今日热点新闻 ({len(rows)} 条)")
    print("=" * 60)
    for i, (title, platform, rank, weight) in enumerate(rows, 1):
        rank_str = f" #{rank}" if rank else ""
        print(f"{i:2}. [{platform}{rank_str}] {title}")
else:
    print(f"数据库不存在: {db_path}")
    
    # 通过 MCP 获取
    BASE = "http://127.0.0.1:3333/mcp"
    def request(method, params=None, session_id=None):
        body = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params:
            body["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        req = urllib.request.Request(BASE, data=json.dumps(body).encode(), headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=30)
        sid = resp.headers.get("Mcp-Session-Id", "")
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

    sid, _ = request("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    })
    _, _ = request("notifications/initialized", session_id=sid)
    time.sleep(0.5)
    
    _, result = request("tools/call", {
        "name": "get_latest_news",
        "arguments": {"limit": 15, "date": "2026-05-07"}
    }, session_id=sid)
    
    content = result.get("result", {}).get("content", [])
    if content:
        text = content[0].get("text", "")
        print("MCP result:", text[:3000])
