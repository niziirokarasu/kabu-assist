"""Discord Webhookへの通知 (2000文字制限に対応した分割送信)"""
import os
import time

import requests

DISCORD_LIMIT = 1900  # 余裕を持たせる


def _split_message(text: str) -> list[str]:
    """改行位置を優先して2000文字以内に分割"""
    chunks = []
    while len(text) > DISCORD_LIMIT:
        cut = text.rfind("\n", 0, DISCORD_LIMIT)
        if cut <= 0:
            cut = DISCORD_LIMIT
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def post_to_discord(content: str, username: str = "株アシスタント"):
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    for chunk in _split_message(content):
        resp = requests.post(
            webhook_url,
            json={"content": chunk, "username": username},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(1)  # レートリミット回避
    print(f"[ok] Discordに投稿しました ({len(content)}文字)")
