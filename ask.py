#!/usr/bin/env python3
"""Ask Reddit a question from the terminal.

Usage:
    python3 ask.py "best budget microphone for podcasting"

Read-only. Searches public posts, pulls the top comments, prints them.
Never posts, votes, messages, or stores user data.

Two modes, picked automatically:
  - Keyed:  if REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME and
            REDDIT_PASSWORD are set, it uses the official OAuth API.
  - No key: otherwise it reads Reddit's public .json pages. Works from a
            home connection; Reddit blocks this from cloud/datacenter IPs.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "macos:ask-threads:0.1 (personal research script)"
POST_LIMIT = 15
COMMENT_LIMIT = 20
KEYED = all(os.environ.get(k) for k in (
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"))


def get_token():
    creds = f"{os.environ['REDDIT_CLIENT_ID']}:{os.environ['REDDIT_CLIENT_SECRET']}".encode()
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "username": os.environ["REDDIT_USERNAME"],
        "password": os.environ["REDDIT_PASSWORD"],
    }).encode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token", data=body,
        headers={"Authorization": "Basic " + base64.b64encode(creds).decode(),
                 "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def get(token, path, **params):
    if token:
        url = "https://oauth.reddit.com" + path
        headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    else:
        url = "https://www.reddit.com" + path + ".json"
        headers = {"User-Agent": USER_AGENT}
    url += "?" + urllib.parse.urlencode({**params, "raw_json": 1})
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 403 and not token:
            sys.exit("Reddit blocked this request (403). The no-key mode only works "
                     "from a home connection, not from a cloud machine. Run it on "
                     "your Mac, or set the REDDIT_* variables once the API app is approved.")
        if e.code == 429:
            sys.exit("Rate limited (429). Wait a minute and try again.")
        raise


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python3 ask.py "your question"')
    question = " ".join(sys.argv[1:])
    token = get_token() if KEYED else None
    print(f"mode: {'official API' if token else 'no key (public pages)'}\n")

    search = get(token, "/search", q=question, sort="relevance", limit=POST_LIMIT, type="link")
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

        thread = get(token, f"/comments/{post['id']}", limit=COMMENT_LIMIT, depth=1, sort="top")
        comments = [c["data"] for c in thread[1]["data"]["children"] if c["kind"] == "t1"]
        for c in comments:
            body = c.get("body", "").strip()
            if not body or body in ("[deleted]", "[removed]"):
                continue
            print(f"  -- [{c['score']} pts]")
            for line in body.splitlines():
                print(f"     {line}")
            print()
        time.sleep(2 if token else 6)  # no-key mode is limited to ~10 requests a minute


if __name__ == "__main__":
    main()
