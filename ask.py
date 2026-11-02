#!/usr/bin/env python3
"""Ask Reddit a question from the terminal.

Usage:
    python3 ask.py "best budget microphone for podcasting"

Read-only. Searches public posts, pulls the top comments, prints them.
Never posts, votes, messages, or stores user data.

Needs four environment variables (from a script-type Reddit app):
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD
"""
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request

USER_AGENT = "macos:ask-threads:0.1 (personal research script)"
POST_LIMIT = 15
COMMENT_LIMIT = 20


def env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing environment variable {name}")
    return value


def get_token():
    creds = f"{env('REDDIT_CLIENT_ID')}:{env('REDDIT_CLIENT_SECRET')}".encode()
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "username": env("REDDIT_USERNAME"),
        "password": env("REDDIT_PASSWORD"),
    }).encode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=body,
        headers={
            "Authorization": "Basic " + base64.b64encode(creds).decode(),
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def get(token, path, **params):
    url = "https://oauth.reddit.com" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"bearer {token}",
        "User-Agent": USER_AGENT,
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python3 ask.py "your question"')
    question = " ".join(sys.argv[1:])
    token = get_token()

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
            if not body or body == "[deleted]":
                continue
            print(f"  -- [{c['score']} pts]")
            for line in body.splitlines():
                print(f"     {line}")
            print()
        time.sleep(1)  # stay well under the rate limit


if __name__ == "__main__":
    main()
