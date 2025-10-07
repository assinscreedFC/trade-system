import asyncio
from aiogram import types, Bot
from services.bot.src.utils import compute_price_and_changes, format_winner_message, alert_listener
from services.scanner.src.worker import BotWorker
from loguru import logger
import html
from typing import Optional

_worker_task: Optional[asyncio.Task] = None
_worker: Optional[BotWorker] = None
_alert_task: Optional[asyncio.Task] = None

async def _get_worker():
    global _worker
    if _worker is None:
        _worker = BotWorker()  # simple instance
    return _worker

async def cmd_run(message: types.Message):
    ALERT_THRESHOLD = 0.7
    MAX_DISPLAY = 10
    global _worker, _worker_task, _alert_task

    # --- Initialisation du worker ---
    try:
        _worker = await _get_worker()
    except Exception as e:
        logger.exception("Worker init failed: %s", e)
        await message.reply(f"❌ Worker init failed: {html.escape(str(e))}")
        return

    # --- Démarrage du worker s'il n'est pas déjà en cours ---
    if not (_worker_task and not _worker_task.done()):
        loop = asyncio.get_event_loop()
        _worker_task = loop.create_task(_worker.run_forever())
        started_text = "▶️ Worker started (background loop)."
    else:
        started_text = "ℹ️ Worker already running; executing an immediate batch."

    # --- Démarrage du listener si pas déjà ---
    if not (_alert_task and not _alert_task.done()):
        bot: Bot = message.bot
        loop = asyncio.get_event_loop()
        _alert_task = loop.create_task(alert_listener(bot, message.chat.id))
        started_text += " Alert listener started."

    # --- Exécution du batch immédiat ---
    try:
        await message.reply(started_text + " Running immediate batch...")
        results = await _worker.run_once_batch()
    except Exception as e:
        logger.exception("Error running batch: %s", e)
        await message.reply(f"❌ Error executing batch: {html.escape(str(e))}")
        return

    # --- Traitement des winners ---
    winners = []
    scored = []
    for r in results:
        if not isinstance(r, dict):
            continue
        sym = r.get("symbol")
        if not sym:
            continue
        summary = r.get("summary") or r.get("result") or {}
        s1 = (summary.get("1h", {}) or {}).get("score", 0.0)
        s1d = (summary.get("1d", {}) or {}).get("score", 0.0)
        top = max(s1, s1d)
        scored.append((sym, top))
        if top >= ALERT_THRESHOLD:
            winners.append((sym, summary, top))

    if not winners:
        scored.sort(key=lambda x: x[1], reverse=True)
        lines = ["✅ Batch complete — aucun winner."]
        lines.extend([f"• {html.escape(sym)} — score: <code>{sc:.4f}</code>" for sym, sc in scored[:5]])
        await message.reply("\n".join(lines), parse_mode="HTML")
        return

    for sym, summary, top in winners[:MAX_DISPLAY]:
        try:
            price_now, pct_1h, pct_24h, pct_7d = await compute_price_and_changes(sym)
            #print(sym, summary, price_now, pct_1h, pct_24h, pct_7d)
        except Exception:
            price_now = pct_1h = pct_24h = pct_7d = None
        msg = format_winner_message(sym, summary, price_now, pct_1h, pct_24h, pct_7d)
        await message.reply(msg, parse_mode="HTML")

    await message.reply(f"🔔 {len(winners)} winner(s) detected in this batch (threshold {ALERT_THRESHOLD}).")
