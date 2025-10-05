from aiogram import types
from loguru import logger

async def cmd_stop(message: types.Message, worker_task=None, alert_task=None):
    if worker_task:
        worker_task.cancel()
        worker_task = None
    if alert_task:
        alert_task.cancel()
        alert_task = None
    await message.reply("⏹️ Worker and listener stopped.")
