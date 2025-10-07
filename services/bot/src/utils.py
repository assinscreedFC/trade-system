import os
import json
import html
import asyncio
from typing import Optional
from loguru import logger
from aiogram import Bot
import redis.asyncio as aioredis
from services.scanner.src.fetcher import get_candles

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ALERT_STREAM = os.getenv("ALERT_STREAM", "alerts_stream")

# Redis client global
_redis = None


async def ensure_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def format_percent(p: float) -> str:
    try:
        return f"{p * 100:+.2f}%"
    except Exception:
        return "n/a"


def pretty_message_for_symbol(symbol: str, summary: dict, price: float,
                              pct_1h: Optional[float], pct_24h: Optional[float], pct_7d: Optional[float]) -> str:
    sym_esc = html.escape(symbol)
    price_s = f"{price:.8f}" if isinstance(price, (int, float)) else str(price)
    price_esc = html.escape(price_s)

    def esc_num(x):
        try:
            return html.escape(f"{x * 100:+.2f}%")
        except Exception:
            return "n/a"

    pct1h_s = esc_num(pct_1h)
    pct24h_s = esc_num(pct_24h)
    pct7d_s = esc_num(pct_7d)

    s1 = summary.get("1h", {})
    s1d = summary.get("1d", {})
    score1h = s1.get("score", 0.0)
    score1d = s1d.get("score", 0.0)

    raw1h = s1.get("latest_raw", {}) or {}
    raw1d = s1d.get("latest_raw", {}) or {}

    def raw_field(d, k):
        return html.escape(str(d.get(k, "n/a")))

    lines = [
        f"<b>{sym_esc}</b>",
        f"• Price now: <code>{price_esc}</code>",
        f"• Change 1h: <code>{pct1h_s}</code>  |  24h: <code>{pct24h_s}</code>  |  7d: <code>{pct7d_s}</code>",
        "",
        f"📊 <b>Scores</b>",
        f"• 1H score: <code>{score1h:.4f}</code>",
        f"• 1D score: <code>{score1d:.4f}</code>",
        "",
        f"🔎 <b>Latest raw (1H)</b>: vol=<code>{raw_field(raw1h, 'volume')}</code>, atr%=<code>{raw_field(raw1h, 'atr_pct')}</code>, adx=<code>{raw_field(raw1h, 'adx')}</code>, rsi=<code>{raw_field(raw1h, 'rsi')}</code>",
        f"🔎 <b>Latest raw (1D)</b>: vol=<code>{raw_field(raw1d, 'volume')}</code>, atr%=<code>{raw_field(raw1d, 'atr_pct')}</code>, adx=<code>{raw_field(raw1d, 'adx')}</code>, rsi=<code>{raw_field(raw1d, 'rsi')}</code>",
        f"LINK TRADINGVIEW: https://fr.tradingview.com/chart/?symbol=BITGET%3A{symbol}"
    ]
    return "\n".join(lines)


def format_winner_message(symbol: str, summary: dict, price: Optional[float],
                          pct_1h: Optional[float], pct_24h: Optional[float], pct_7d: Optional[float]) -> str:
    try:
        sym = (symbol or "UNKNOWN").upper()
        s1 = (summary.get("1h", {}) or {}).get("score", 0.0) or 0.0
        s1d = (summary.get("1d", {}) or {}).get("score", 0.0) or 0.0
        top = max(float(s1), float(s1d))
    except Exception:
        sym = (symbol or "UNKNOWN").upper()
        top = 0.0

    header = f"🚀 <b>WINNER — {html.escape(sym)}</b>\nTop score: <code>{top:.4f}</code>\n\n"

    try:
        body = pretty_message_for_symbol(sym, summary or {}, price if price is not None else 0.0, pct_1h, pct_24h,
                                         pct_7d)
    except Exception as e:
        logger.exception("pretty_message_for_symbol failed for %s: %s", sym, e)
        body = f"<b>{html.escape(sym)}</b>\n• score: <code>{top:.4f}</code>"

    footer = f"\n\nℹ️ Pour plus de détails utilisez /result {html.escape(sym)} ou /next pour forcer le worker."
    return header + body + footer


async def compute_price_and_changes(symbol: str):
    # identique à ton compute_price_and_changes
    try:
        candles_1h = await get_candles(symbol, "1h", limit=2)
        last = float(candles_1h[-1][4]) if candles_1h else 0.0
        prev = float(candles_1h[-2][4]) if len(candles_1h) >= 2 else last
        pct_1h = (last - prev) / prev if prev != 0 else 0.0
    except Exception:
        last = 0.0
        pct_1h = None

    try:
        candles_1d = await get_candles(symbol, "1day", limit=8)
        lastd = float(candles_1d[-1][4]) if candles_1d else last
        prev24 = float(candles_1d[-2][4]) if len(candles_1d) >= 2 else lastd
        pct_24h = (lastd - prev24) / prev24 if prev24 != 0 else 0.0
        prev7 = float(candles_1d[-8][4]) if len(candles_1d) >= 8 else lastd
        pct_7d = (lastd - prev7) / prev7 if prev7 != 0 else 0.0
        price_now = lastd if candles_1d else last
    except Exception:
        price_now = last
        pct_24h = pct_7d = None

    return price_now, pct_1h, pct_24h, pct_7d


async def alert_listener(bot: Bot, chat_id: int, redis_url: str = REDIS_URL):
    r = aioredis.from_url(redis_url, decode_responses=True)

    last_id = "$"
    while True:
        try:
            streams = await r.xread({ALERT_STREAM: last_id}, block=20000, count=50)
            print('no streams', streams)
            if not streams:
                #print('no streams',streams)
                continue
            for _, messages in streams:
                for msg_id, fields in messages:
                    raw = fields.get("data") or fields.get("json") or ""
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        payload = {"raw": raw}

                    price_now, pct_1h, pct_24h, pct_7d = await compute_price_and_changes(payload.get("symbol", "UNK"))
                    text = format_winner_message(payload.get("symbol", "UNK"), payload.get("summary", {}), price_now, pct_1h,
                                                 pct_24h, pct_7d)
                    try:
                        await bot.send_message(chat_id, text, parse_mode="HTML")
                    except Exception as e:
                        logger.exception("Failed to send alert to chat %s: %s", chat_id, e)
                    last_id = msg_id
        except Exception as e:
            logger.exception("alert_listener error: %s", e)
            await asyncio.sleep(2)
