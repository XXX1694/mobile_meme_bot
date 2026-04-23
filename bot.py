"""Один запуск: тянем hot из сабов, выбираем случайный неповторный мем, постим в топик."""
import asyncio
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import aiohttp
from aiogram import Bot

CHAT_ID = -1003554574954
TOPIC_ID = 352
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDDIT_UA = "it_meme_bot/1.0 by u/kbtumobile_bot"

SUBS = [
    "ProgrammerHumor",
    "programmingmemes",
    "techhumor",
    "softwaregore",
    "ProgrammerAnimemes",
]

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".gifv")
STATE_PATH = Path(__file__).parent / "state.json"


async def fetch_sub(session: aiohttp.ClientSession, sub: str) -> list[dict]:
    """Скачиваем hot конкретного сабреддита. Ошибки/таймауты — пустой список."""
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=50"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                print(f"[warn] r/{sub} вернул {resp.status}", file=sys.stderr)
                return []
            data = await resp.json()
            return [c["data"] for c in data.get("data", {}).get("children", [])]
    except Exception as exc:
        print(f"[warn] r/{sub}: {exc}", file=sys.stderr)
        return []


def is_image_meme(post: dict) -> bool:
    """Отсеиваем видео/NSFW/закреп; оставляем только картинки."""
    if post.get("stickied") or post.get("over_18") or post.get("is_video"):
        return False
    if post.get("post_hint") == "image":
        return True
    url = (post.get("url") or "").lower()
    return url.endswith(IMAGE_EXT)


def post_hash(post: dict) -> str:
    return hashlib.md5(post["id"].encode()).hexdigest()[:10]


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"seen": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


async def main() -> None:
    if not BOT_TOKEN:
        print("BOT_TOKEN не задан", file=sys.stderr)
        sys.exit(1)

    async with aiohttp.ClientSession(headers={"User-Agent": REDDIT_UA}) as session:
        results = await asyncio.gather(*(fetch_sub(session, s) for s in SUBS))

    all_posts = [p for sub_posts in results for p in sub_posts]
    if not all_posts:
        print("все саб-реддиты пустые/забанили — прерываемся", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    seen = set(state.get("seen", []))

    candidates = [p for p in all_posts if is_image_meme(p) and post_hash(p) not in seen]
    if not candidates:
        # круг замкнулся — чистим seen и снова фильтруем (уже без проверки на seen)
        print("cycle complete — seen reset", file=sys.stderr)
        seen.clear()
        candidates = [p for p in all_posts if is_image_meme(p)]

    if not candidates:
        print("после фильтра 0 картинок — прерываемся", file=sys.stderr)
        sys.exit(1)

    post = random.choice(candidates)
    seen.add(post_hash(post))
    state["seen"] = sorted(seen)
    save_state(state)

    url = post["url"]
    if url.endswith(".gifv"):
        url = url[:-1]  # imgur .gifv → .gif
    title = post["title"][:900]
    caption = f"{title}\n\nr/{post['subreddit']} · reddit.com{post['permalink']}"

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_photo(
            chat_id=CHAT_ID,
            message_thread_id=TOPIC_ID,
            photo=url,
            caption=caption,
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
