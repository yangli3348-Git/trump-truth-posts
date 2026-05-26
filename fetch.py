#!/usr/bin/env python3
"""
📡 Trump Truth Social 帖子采集器
从 CNN 维护的公开 archive 拉取最新帖子
来源: https://ix.cnn.io/data/truth-social/truth_archive.json
每 5 分钟更新，JSON 数组 ~18MB

策略: Range 请求只取前 500KB（最新帖子在数组头部）
"""

import json, os, time, re
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(HERE, "data", "truth_posts.json")
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# ── 配置 ──
ARCHIVE_URL = "https://ix.cnn.io/data/truth-social/truth_archive.json"
RANGE_BYTES = 500000       # 取前 500KB
KEEP_RECENT = 50           # 本地只保留最新 50 条

def log(tag: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"{ts} [{tag:<6}] {msg}", flush=True)

def clean_html(raw: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', raw)
    text = re.sub(r'</p>\s*<p>', '\n\n', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()

def fetch_posts() -> list[dict]:
    log("FETCH", f"Range 0-{RANGE_BYTES} ...")
    headers = {"Range": f"bytes=0-{RANGE_BYTES}"}
    resp = requests.get(ARCHIVE_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    text = resp.text

    # 从截断的 JSON 数组中提取完整帖子对象
    matches = list(re.finditer(
        r'\{(?:[^{}]|\{[^{}]*\}|\{[^{}]*\{[^{}]*\}[^{}]*\})*\}',
        text
    ))
    log("PARSE", f"匹配到 {len(matches)} 个片段")

    posts = []
    for m in matches:
        try:
            p = json.loads(m.group())
            posts.append({
                "id": p.get("id", ""),
                "created_at": p.get("created_at", ""),
                "content": clean_html(p.get("content", "")),
                "url": p.get("url", ""),
                "media": p.get("media", []),
                "replies": p.get("replies_count", 0),
                "reblogs": p.get("reblogs_count", 0),
                "favorites": p.get("favourites_count", 0),
            })
        except json.JSONDecodeError:
            continue

    posts.sort(key=lambda x: x["created_at"], reverse=True)
    return posts

def main():
    log("START", "Trump Truth Social (CNN archive)")
    start = time.time()

    try:
        posts = fetch_posts()
        log("DONE", f"共 {len(posts)} 条")

        # 保存最新 KEEP_RECENT 条
        recent = posts[:KEEP_RECENT]
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)

        if recent:
            print(f"  最新: [{recent[0]['created_at'][:16]}] {recent[0]['content'][:80]}...")
            print(f"  最早: [{recent[-1]['created_at'][:16]}]")
        log("WRITE", f"保存 {len(recent)} 条 → {OUTPUT_FILE}")

    except Exception as e:
        log("ERROR", str(e))

    elapsed = time.time() - start
    log("END", f"耗时 {elapsed:.1f}s")

if __name__ == "__main__":
    main()
