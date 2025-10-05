# bot/api.py
import requests
import asyncio

BASE_CANDLES = "https://api.bitget.com/api/v2/spot/market/candles"

def _fetch_candles_sync(symbol: str, granularity: str, limit: int = 200, startTime: str = None, endTime: str = None):
    params = {"symbol": symbol, "granularity": granularity, "limit": limit}
    if startTime:
        params["startTime"] = str(startTime)
    if endTime:
        params["endTime"] = str(endTime)
    r = requests.get(BASE_CANDLES, params=params, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != "00000":
        raise RuntimeError(f"Bitget API error: {j.get('msg')}")
    return j.get("data", [])

async def get_candles(symbol: str, granularity: str = "1h", limit: int = 200):
    """Async wrapper returning list of candles."""
    return await asyncio.to_thread(_fetch_candles_sync, symbol, granularity, limit)
