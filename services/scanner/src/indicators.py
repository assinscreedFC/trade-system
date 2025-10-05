import pandas as pd
import pandas_ta as ta

def ohlcv_to_df(ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df




def compute_indicators(df):
    # basic indicators
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["atr_pct"] = df["atr"] / df["close"]
    df["rsi"] = ta.rsi(df["close"], length=14)
    adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
    df["adx"] = adx_df.get("ADX_14")
    df["ma20"] = ta.sma(df["close"], length=20)
    df["ma50"] = ta.sma(df["close"], length=50)
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["vol_spike_ratio"] = df["volume"] / df["vol_ma20"]
    df = df.dropna()
    return df
