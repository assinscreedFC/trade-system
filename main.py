# main.py (à la racine du projet)
import os
from dotenv import load_dotenv
load_dotenv()

# importe la coroutine main depuis le package du bot
from services.bot.src.main import main as bot_main
import asyncio

if __name__ == "__main__":
    # lance proprement la coroutine principale du bot
    asyncio.run(bot_main())
