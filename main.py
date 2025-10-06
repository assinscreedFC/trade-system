import os
from dotenv import load_dotenv

load_dotenv()

from services.bot.src.main import main as bot_main
import asyncio
from fastapi import FastAPI
import uvicorn

app = FastAPI()


from fastapi.responses import JSONResponse

@app.get("/", response_class=JSONResponse)
@app.head("/", response_class=JSONResponse)
def ping():
    return {"status": "ok"}



async def start():
    # lance uvicorn dans une coroutine séparée
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)

    # lance uvicorn et le bot en parallèle
    await asyncio.gather(server.serve(), bot_main())


if __name__ == "__main__":
    asyncio.run(start())
