import json
from aiogram import types
from loguru import logger
from services.bot.src.utils import ensure_redis, compute_price_and_changes, pretty_message_for_symbol
from services.scanner.src.worker import REDIS_RESULT_PREFIX

async def cmd_result(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.reply("Usage: /result SYMBOL (e.g. /result BTCUSDT)")
        return
    symbol = parts[1].upper()
    r = await ensure_redis()
    key = REDIS_RESULT_PREFIX + symbol
    try:
        v = await r.get(key)
    except Exception as e:
        logger.exception("redis get error: %s", e)
        await message.reply(f"Redis error: {e}")
        return

    if not v:
        await message.reply(f"ℹ️ No cached result for `{symbol}`. You can run `/next` or wait for the worker to process it.")
        return

    try:
        summary = json.loads(v)
    except Exception as e:
        logger.exception("json decode error: %s", e)
        await message.reply("❌ Invalid data in redis.")
        return

    price_now, pct_1h, pct_24h, pct_7d = await compute_price_and_changes(symbol)
    text = pretty_message_for_symbol(symbol, summary, price_now, pct_1h, pct_24h, pct_7d)
    await message.reply(text, parse_mode="HTML")
