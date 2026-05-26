#!/usr/bin/env python3
"""
📡 Trump Truth Social 帖子采集器
通过 Mastodon API 拉取，GitHub Actions 美国 IP 直连

学习 stiles/trump-truth-social-archive:
  - Mastodon API: truthsocial.com/api/v1/accounts/107780257626128497/statuses
  - 去重 + 增量 + 排序
  - 输出 JSON

输出: data/truth_posts.json
"""

import json, os, time, re
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(HERE, "data", "truth_posts.json")
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# ── 配置 ──
BASE_URL = "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://truthsocial.com/@realDonaldTrump",
}
FETCH_PAGES = 3          # 拉几页（每页 20 条）
PER_PAGE = 20

def log(tag: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"{ts} [{tag:<6}] {msg}", flush=True)

def clean_html(raw: str) -> str:
    """HTML → 纯文本"""
    text = re.sub(r'<br\s*/?>', '\n', raw)
    text = re.sub(r'</p>\s*<p>', '\n\n', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()

def load_existing() -> dict[str, dict]:
    """加载已有数据"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            posts = json.load(f)
        return {p["id"]: p for p in posts}
    return {}

def fetch_latest() -> list[dict]:
    """拉最新帖子"""
    existing = load_existing()
    all_posts = list(existing.values())
    new_count = 0
    max_id = None

    for page in range(FETCH_PAGES):
        params = {
            "exclude_replies": "true",
            "limit": str(PER_PAGE),
        }
        if max_id:
            params["max_id"] = max_id

        log("FETCH", f"第{page+1}页...")
        try:
            resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log("ERROR", f"第{page+1}页失败: {e}")
            break

        if not data:
            log("DONE", "无更多数据")
            break

        page_new = 0
        for post in data:
            pid = post["id"]
            if pid in existing:
                continue
            page_new += 1
            existing[pid] = {
                "id": pid,
                "created_at": post.get("created_at", ""),
                "content": clean_html(post.get("content", "")),
                "url": post.get("url", ""),
                "media": [m.get("url", "") for m in post.get("media_attachments", [])],
                "replies": post.get("replies_count", 0),
                "reblogs": post.get("reblogs_count", 0),
                "favorites": post.get("favourites_count", 0),
            }

        new_count += page_new
        log("PAGE", f"  +{page_new} 条新")
        max_id = data[-1]["id"]  # 下一页游标

        if page_new == 0:
            break

    # 排序并保存
    all_posts = sorted(existing.values(), key=lambda x: x["created_at"], reverse=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    log("WRITE", f"共 {len(all_posts)} 条 (+{new_count} 新)")
    return all_posts

def main():
    log("START", "Trump Truth Social 采集器")
    start = time.time()
    posts = fetch_latest()
    if posts:
        print(f"  最新: [{posts[0]['created_at'][:16]}] {posts[0]['content'][:80]}...")
        print(f"  最早: [{posts[-1]['created_at'][:16]}]")
    elapsed = time.time() - start
    log("END", f"耗时 {elapsed:.1f}s")

if __name__ == "__main__":
    main()
