# mobile_meme_bot

A Telegram bot that posts one random IT meme a day to a topic of a university mobile-development group chat. It runs as a one-shot script on a GitHub Actions schedule, so there is no server to host.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-2CA5E0?style=flat-square&logo=telegram&logoColor=white)
![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?style=flat-square&logo=aiohttp&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)

## Features

- Pulls the hot posts of `r/ProgrammerHumor` and `r/programmingmemes` (50 per subreddit, fetched in parallel).
- Filters out NSFW posts, spoilers, non-image URLs and posts below 500 upvotes.
- Picks the meme with a **weighted random choice** (probability proportional to upvotes), so popular memes win more often but the feed stays varied.
- Never repeats a meme: seen posts are stored as short MD5 hashes of the image URL in `state.json`. When the pool is exhausted the list resets.
- Keeps the caption within Telegram's 1024-character limit by trimming the title.
- Posts into a specific forum topic via `message_thread_id`.
- Exits with a non-zero code when no meme is available, so the workflow does not commit a stale state and the next run simply retries.

## How it works

```mermaid
flowchart LR
    Cron["GitHub Actions<br/>cron 10:00 UTC + manual dispatch"] --> Bot["bot.py"]
    Bot -->|"GET /gimme/{sub}/50"| API["meme-api.com<br/>(Reddit proxy)"]
    API --> Bot
    Bot -->|"filter, dedupe, weighted pick"| State[("state.json")]
    Bot -->|"send_photo"| TG["Telegram topic"]
    Cron -->|"commit state.json"| Repo["main branch"]
```

Memes come from [meme-api.com](https://github.com/D3vd/Meme_Api) rather than Reddit directly, because Reddit blocks anonymous requests from cloud IPs such as GitHub runners.

## Tech stack

| Area | Tools |
| --- | --- |
| Language | Python 3.10 |
| Telegram | aiogram |
| HTTP | aiohttp |
| Scheduling and state | GitHub Actions (`.github/workflows/meme.yml`), `state.json` committed back to the repo |

## Project structure

```
.
├── bot.py                      # fetch, filter, pick, post
├── state.json                  # hashes of already posted memes
├── requirements.txt
└── .github/workflows/meme.yml  # daily cron + manual dispatch
```

## Getting started

```bash
pip install -r requirements.txt
BOT_TOKEN=<your bot token> python bot.py
```

The target chat and topic ids (`CHAT_ID`, `TOPIC_ID`) and the subreddit list (`SUBS`) are constants at the top of `bot.py`. To run it on GitHub Actions, add `BOT_TOKEN` as a repository secret. The workflow runs daily at 10:00 UTC and can also be started manually.
