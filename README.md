# ask-threads

Ask Reddit a question from the terminal and read what people actually say.

## What it does

- Takes a question as a command-line argument.
- Searches public Reddit posts for it.
- Pulls the top comments on each matching post.
- Prints everything to the terminal for reading.

Read-only. It never posts, votes, messages, or stores user data.

## Setup

1. Create a script-type app at https://www.reddit.com/prefs/apps
2. Set four environment variables:

```bash
export REDDIT_CLIENT_ID=...
export REDDIT_CLIENT_SECRET=...
export REDDIT_USERNAME=...
export REDDIT_PASSWORD=...
```

3. Run it:

```bash
python3 ask.py "best budget microphone for podcasting"
```

No dependencies beyond Python 3. Without the four variables it falls back to Reddit RSS feeds. Slower, no scores, home connection only.

## Limits

- About 10 to 25 requests per question. Reddit allows 100 per minute.
- Personal, non-commercial use only.
