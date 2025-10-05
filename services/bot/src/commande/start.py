from aiogram import types
from aiogram.filters import Command

async def cmd_start(message: types.Message):
    await message.reply("🤖 Bot ready. Commands: /run /stop /status /result (SYMBOL) /next" , parse_mode="HTML")
