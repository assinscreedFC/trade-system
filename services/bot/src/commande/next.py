from aiogram import types
from loguru import logger

async def cmd_next(message: types.Message, worker=None):
    if worker is None:
        await message.reply("⚠️ Worker not initialized. Use /run first.")
        return
    try:
        task = worker.run_once_batch()
        res = await task
        processed = [r.get("symbol") for r in res if isinstance(r, dict) and r.get("symbol")]
        await message.reply(f"✅ Executed batch for: {', '.join(processed)}")
    except Exception as e:
        logger.exception("next error: %s", e)
        await message.reply(f"❌ Error executing batch: {e}")
