#!/usr/bin/env python3
"""Ask Reddit a question from the terminal.

Usage:
    python3 ask.py "best budget microphone for podcasting"

Read-only. Searches public posts, pulls the top comments, prints them.
Never posts, votes, messages, or stores user data.

Two modes, picked automatically:
  - Keyed:  if REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME and
            REDDIT_PASSWORD are set, it uses the official OAuth API. Fast,
            includes scores, 100 requests a minute.
  - RSS:    otherwise it reads Reddit's public RSS feeds. No key needed.
            Slow (Reddit rate-limits RSS hard), no scores, home connection
            only. One question takes about 2 to 3 minutes.
"""
import base64
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "macos:ask-threads:0.1 (personal research script)"
KEYED = all(os.environ.get(k) for k in (
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"))
POST_LIMIT = 15 if KEYED else 8
COMMENT_LIMIT = 20
PAUSE = 2 if KEYED else 12  # seconds between requests
ATOM = "{http://www.w3.org/2005/Atom}"


def fetch(url, headers, data=None, retries=2):
    req = urllib.request.Request(url, data=data, headers={**headers, "User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                print("  (rate limited, waiting 30s)", file=sys.stderr)
                time.sleep(30)
                continue
            if e.code == 403:
                sys.exit("Reddit blocked this request (403). Try again later, or set the "
                         "REDDIT_* variables once the API app is approved.")
            if e.code == 429:
                sys.exit("Rate limited (429). Wait a few minutes and try again.")
            raise


# ---------- keyed mode: official API ----------

def get_token():
    creds = f"{os.environ['REDDIT_CLIENT_ID']}:{os.environ['REDDIT_CLIENT_SECRET']}".encode()
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "username": os.environ["REDDIT_USERNAME"],
        "password": os.environ["REDDIT_PASSWORD"],
    }).encode()
    raw = fetch("https://www.reddit.com/api/v1/access_token", {
        "Authorization": "Basic " + base64.b64encode(creds).decode()}, data=body)
    return json.loads(raw)["access_token"]


def api(token, path, **params):
    url = "https://oauth.reddit.com" + path + "?" + urllib.parse.urlencode({**params, "raw_json": 1})
    return json.loads(fetch(url, {"Authorization": f"bearer {token}"}))


def run_keyed(question):
    token = get_token()
    search = api(token, "/search", q=question, sort="relevance", limit=POST_LIMIT, type="link")
    posts = [p["data"] for p in search["data"]["children"]]
    if not posts:
        print("No posts found.")
        return
    for post in posts:
        print("=" * 80)
        print(f"[{post['score']} pts] r/{post['subreddit']}: {post['title']}")
        print(f"https://www.reddit.com{post['permalink']}")
        if post.get("selftext"):
            print()
            print(post["selftext"][:1500])
        print()
        thread = api(token, f"/comments/{post['id']}", limit=COMMENT_LIMIT, depth=1, sort="top")
        for c in thread[1]["data"]["children"]:
            if c["kind"] != "t1":
                continue
            body = c["data"].get("body", "").strip()
            if not body or body in ("[deleted]", "[removed]"):
                continue
            print(f"  -- [{c['data']['score']} pts]")
            for line in body.splitlines():
                print(f"     {line}")
            print()
        time.sleep(PAUSE)


# ---------- RSS mode: no key ----------

def strip_html(s):
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def rss(url):
    root = ET.fromstring(fetch(url, {}))
    entries = []
    for e in root.findall(ATOM + "entry"):
        link = e.find(ATOM + "link")
        entries.append({
            "id": (e.findtext(ATOM + "id") or "").strip(),
            "title": (e.findtext(ATOM + "title") or "").strip(),
            "link": link.get("href") if link is not None else "",
            "author": (e.findtext(ATOM + "author/" + ATOM + "name") or "").strip(),
            "subreddit": (e.find(ATOM + "category").get("label")
                          if e.find(ATOM + "category") is not None else ""),
            "text": strip_html(e.findtext(ATOM + "content") or ""),
        })
    return entries


def run_rss(question):
    q = urllib.parse.urlencode({"q": question, "sort": "relevance", "limit": POST_LIMIT})
    posts = [p for p in rss(f"https://www.reddit.com/search.rss?{q}")
             if "/comments/" in p["link"]][:POST_LIMIT]
    if not posts:
        print("No posts found.")
        return
    print(f"{len(posts)} posts. Fetching comments, about {len(posts) * PAUSE // 60 + 1} min...\n")
    for post in posts:
        time.sleep(PAUSE)
        print("=" * 80)
        print(f"{post['subreddit']}: {post['title']}")
        print(post["link"])
        body = re.sub(r"submitted by.*$", "", post["text"], flags=re.S).strip()
        if body and not body.startswith("[link]"):
            print()
            print(body[:1500])
        print()
        thread_url = post["link"].rstrip("/") + "/.rss?" + urllib.parse.urlencode(
            {"limit": COMMENT_LIMIT, "sort": "top"})
        comments = [c for c in rss(thread_url) if c["id"].startswith("t1_")]
        for c in comments[:COMMENT_LIMIT]:
            text = c["text"].strip()
            if not text or text in ("[deleted]", "[removed]"):
                continue
            print(f"  -- {c['author']}")
            for line in text.splitlines():
                print(f"     {line}")
            print()


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python3 ask.py "your question"')
    question = " ".join(sys.argv[1:])
    print(f"mode: {'official API' if KEYED else 'RSS, no key'}\n")
    (run_keyed if KEYED else run_rss)(question)


if __name__ == "__main__":
    main()
