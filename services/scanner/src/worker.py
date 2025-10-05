# bot/worker.py
import asyncio
import os
import json
from typing import List
import pandas as pd
import redis.asyncio as aioredis
from services.scanner.src.fetcher import get_candles
from services.scanner.src.scoring import compute_scores_from_ohlcv

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SYMBOL_LIST_FILE = os.getenv("SYMBOL_LIST_FILE", "./data/filtered_pairs.json")
STORE_WINNER= os.getenv("STORE_WINNER", "./data/winner.json")
REDIS_INDEX_KEY = "bot:symbol_index"
REDIS_RESULT_PREFIX = "bot:result:"  # store last result per symbol as JSON
ALERT_STREAM = os.getenv("ALERT_STREAM", "alerts_stream")
ALERT_GROUP = os.getenv("ALERT_GROUP", "bots")
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.7"))  # default threshold
THRESH = 0.6

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 5))
SLEEP_BETWEEN_BATCHES = int(os.getenv("SLEEP_BETWEEN_BATCHES", 5 * 60))

class BotWorker:
    def __init__(self, redis_url=REDIS_URL, symbols_file=SYMBOL_LIST_FILE):
        self.r = aioredis.from_url(redis_url, decode_responses=True)
        self.symbols = self._load_symbols_file(symbols_file)
        if not self.symbols:
            raise RuntimeError("Aucune paire trouvée dans filtered_pairs.json")

    def _load_symbols_file(self, path) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                #print(data)
            syms = []
            for entry in data:
                for p in entry.get("pairs", []):
                    sym = p.get("symbol")
                    if sym and sym.endswith("USDT"):
                        syms.append(sym)
                        break
            return syms
        except FileNotFoundError:
            return []

    async def _get_index(self) -> int:
        v = await self.r.get(REDIS_INDEX_KEY)
        if v is None:
            await self.r.set(REDIS_INDEX_KEY, 0)
            return 0
        return int(v)

    async def _set_index(self, idx: int):
        await self.r.set(REDIS_INDEX_KEY, int(idx))

    async def _maybe_publish_alert(self, symbol: str, summary: dict):
        """
        Publishes to Redis stream if either 1h or 1d score exceeds threshold.
        """
        try:
            s1 = summary.get("1h", {}).get("score", 0.0) or 0.0
            s1d = summary.get("1d", {}).get("score", 0.0) or 0.0
            top_score = max(s1, s1d)
            if top_score >= ALERT_THRESHOLD:
                payload = {
                    "symbol": symbol,
                    "score_1h": s1,
                    "score_1d": s1d,
                    "summary": summary
                }
                # push to stream as JSON string under field "data"
                await self.r.xadd(ALERT_STREAM, {"data": json.dumps(payload)}, maxlen=1000)
        except Exception as e:
            # don't fail processing on alert publish failure
            print("publish alert error:", e)

    async def _process_symbol(self, symbol: str):
        try:
            candles_1h = await get_candles(symbol, "1h", limit=200)
            candles_1d = await get_candles(symbol, "1day", limit=200)
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

        # compute scores
        try:
            summary = compute_scores_from_ohlcv(candles_1h, candles_1d)
        except Exception as e:
            return {"symbol": symbol, "error": f"scoring error: {e}"}

        # store summary in redis
        try:
            await self.r.set(REDIS_RESULT_PREFIX + symbol, json.dumps(summary))
        except Exception as e:
            print("redis set error:", e)

        # publish to alert stream if threshold exceeded
        await self._maybe_publish_alert(symbol, summary)

        return {"symbol": symbol, "summary": summary}

    async def run_once_batch(self):
        idx = await self._get_index()
        n = len(self.symbols)
        results = []
        for i in range(BATCH_SIZE):
            symbol_idx = (idx + i) % n
            symbol = self.symbols[symbol_idx]
            res = await self._process_symbol(symbol)
            results.append(res)
        new_idx = (idx + BATCH_SIZE) % n
        await self._set_index(new_idx)
        return results

    async def run_forever(self):
        while True:
            try:
                results = await self.run_once_batch()

                winners = []
                for r in results:
                    s1 = r.get("summary", {}).get("1h", {}).get("score", 0) or 0
                    s1d = r.get("summary", {}).get("1d", {}).get("score", 0) or 0
                    top = max(s1, s1d)
                    if top >= THRESH:
                        winners.append({"symbol": r["symbol"], "score_1h": s1, "score_1d": s1d})
                        with open(STORE_WINNER, "w", encoding="utf-8") as f:
                            json.dump(winners, f, ensure_ascii=False, indent=4)

                print(f"Processed batch: {[r['symbol'] for r in results]}")
            except Exception as e:
                print("Worker error:", e)
            await asyncio.sleep(SLEEP_BETWEEN_BATCHES)


if __name__ == "__main__":
    import asyncio

    async def test_worker():
        print("⚡ Starting worker test...")
        worker = BotWorker()
        results = await worker.run_once_batch()
        for r in results:
            sym = r.get("symbol")
            summary = r.get("summary")
            if summary:
                print(f"\nSymbol: {sym}")
                print("1h score:", summary.get("1h", {}).get("score"))
                print("1d score:", summary.get("1d", {}).get("score"))
            else:
                print(f"\nSymbol: {sym} -- Error:", r.get("error"))

    asyncio.run(test_worker())
