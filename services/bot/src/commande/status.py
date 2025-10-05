import os
import json
from aiogram import types
from services.bot.src.utils import ensure_redis
from loguru import logger

REDIS_INDEX_KEY = "bot:symbol_index"

async def cmd_status(message: types.Message, worker_task=None):
    r = await ensure_redis()
    idx = await r.get(REDIS_INDEX_KEY) or "0"
    total = "unknown"
    try:
        path = os.getenv("SYMBOL_LIST_FILE", "filtered_pairs.json")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        total = sum(1 for entry in data for p in entry.get("pairs", []) if p.get("symbol","").endswith("USDT"))
    except Exception:
        total = "unknown"
    worker_running = worker_task and not worker_task.done()
    await message.reply(f"Index: {idx}\nTotal symbols: {total}\nWorker running: {worker_running}")
