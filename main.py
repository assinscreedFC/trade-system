# main.py
import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
from fastapi import FastAPI
import uvicorn
from services.bot.src.main import main as bot_main

app = FastAPI()

@app.get("/")
def ping():
    return {"status": "ok"}

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # lance le bot dans une tâche background
    loop.create_task(bot_main())
    # lance le serveur FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8080)
