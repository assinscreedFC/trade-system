# services/bot/src/main.py
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from loguru import logger
from services.bot.src.handlers import router  # on importe le router (aiogram v3)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ TELEGRAM_TOKEN not set in environment")

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="none"))
dp = Dispatcher()

async def main():
    # inclure le router contenant tous les handlers
    dp.include_router(router)

    logger.info("🤖 Bot starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"❌ Bot crashed: {e}")
    finally:
        await bot.session.close()
        logger.info("🛑 Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
