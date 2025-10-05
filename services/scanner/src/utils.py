# test_scoring_debug.py
import importlib
import requests
import json
import sys

# adapte le chemin si besoin (si ton package est 'bot', fais import bot.scoring)
try:
    import bot.scoring as scoring
except Exception:
    # fallback si tu as un module scoring à la racine
    import scoring

# reload to ensure newest code is loaded
importlib.reload(scoring)

SYMBOL = "BTCUSDT"
URL = "https://api.bitget.com/api/v2/spot/market/candles"
params = {"symbol": SYMBOL, "granularity": "1h", "limit": 3}

print("Using ohlcv_to_df from:", scoring.ohlcv_to_df.__module__, scoring.ohlcv_to_df.__qualname__)
print("Function code location:", getattr(scoring.ohlcv_to_df, "__code__", "no code"))

r = requests.get(URL, params=params, timeout=15)
r.raise_for_status()
j = r.json()
print("API code/msg:", j.get("code"), j.get("msg"))
raw = j.get("data", [])
print("Rows fetched:", len(raw))
if raw:
    print("Length of first row:", len(raw[0]))
    print("First row sample:", raw[0])
    print("Full rows sample:")
    for row in raw:
        print(row)

# Try to convert
try:
    df = scoring.ohlcv_to_df(raw)
    print("\nDataFrame head:\n", df.head())
    print("DF columns:", df.columns.tolist())
    print("DF shape:", df.shape)
except Exception as e:
    print("ohlcv_to_df error:", e, file=sys.stderr)
    raise
