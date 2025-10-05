# bot/scoring.py
import pandas as pd
import pandas_ta as ta
import json

def ohlcv_to_df(ohlcv):
    """
    Convertit une liste OHLCV (API Bitget ou autre) en DataFrame standard:
    - accepte 6-colonnes (ts, o,h,l,c,volume) ou 8-colonnes (ts,o,h,l,c,baseVol,usdtVol,quoteVol)
    - renomme automatiquement baseVolume -> volume si présent
    - convertit en float/open/high/low/close/volume
    - index = timestamp (datetime)
    """
    if not ohlcv:
        return pd.DataFrame(columns=["open","high","low","close","volume"])

    # détecte la longueur d'une ligne
    first_len = len(ohlcv[0])

    if first_len == 6:
        cols = ["timestamp","open","high","low","close","volume"]
    elif first_len >= 8:
        # Bitget: ts, open, high, low, close, baseVol, usdtVol, quoteVol
        cols = ["timestamp","open","high","low","close","baseVolume","usdtVolume","quoteVolume"]
    else:
        # fallback générique
        cols = [f"c{i}" for i in range(first_len)]

    df = pd.DataFrame(ohlcv, columns=cols)

    # timestamp -> datetime index (Bitget fournit ms)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
    df.set_index("timestamp", inplace=True)

    # normaliser le nom de la colonne volume (priorité baseVolume -> quoteVolume -> volume)
    if "baseVolume" in df.columns:
        df = df.rename(columns={"baseVolume": "volume"})
    elif "quoteVolume" in df.columns and "volume" not in df.columns:
        df = df.rename(columns={"quoteVolume": "volume"})
    # si aucune colonne volume, crée-la à 0
    if "volume" not in df.columns:
        df["volume"] = 0.0

    # cast des colonnes numériques utiles
    for c in ["open","high","low","close","volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # supprimer les lignes NA résultantes si besoin
    df = df.dropna(subset=["open","high","low","close"])

    return df


def compute_indicators(df):
    df = df.copy()
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

def compute_simple_score(norm_dict, weights):
    s = 0.0
    s += weights.get("liquidity_vol", 0.25) * norm_dict.get("volume_norm", 0)
    s += weights.get("atr_percent", 0.25) * norm_dict.get("atr_pct_norm", 0)
    s += weights.get("volume_spike", 0.2) * norm_dict.get("vol_spike_norm", 0)
    s += weights.get("adx", 0.15) * norm_dict.get("adx_norm", 0)
    s += weights.get("rsi_pullback", 0.15) * norm_dict.get("rsi_pull_norm", 0)
    return s

# helpers
def _clamp(x, a=0.0, b=1.0):
    try:
        return max(a, min(b, float(x)))
    except Exception:
        return 0.0

def compute_norms_from_indicator_df(df_latest, params=None):
    if params is None:
        params = {}
    volume_ratio_cap = params.get("volume_ratio_cap", 3.0)
    atr_pct_cap = params.get("atr_pct_cap", 0.05)
    adx_cap = params.get("adx_cap", 40.0)

    vol = float(df_latest.get("volume", 0) or 0)
    vol_ma20 = float(df_latest.get("vol_ma20", 0) or 0.0)
    vol_ratio = (vol / vol_ma20) if vol_ma20 > 0 else 0.0
    atr_pct = float(df_latest.get("atr_pct", 0) or 0.0)
    vol_spike_ratio = float(df_latest.get("vol_spike_ratio", vol_ratio) or 0.0)
    adx = float(df_latest.get("adx", 0) or 0.0)
    rsi = float(df_latest.get("rsi", 50) or 50.0)

    volume_norm = _clamp(vol_ratio / volume_ratio_cap)
    atr_pct_norm = _clamp(atr_pct / atr_pct_cap)
    vol_spike_norm = _clamp(vol_spike_ratio / volume_ratio_cap)
    adx_norm = _clamp(adx / adx_cap)
    rsi_pull_norm = _clamp((60.0 - rsi) / 30.0)

    norm_dict = {
        "volume_norm": volume_norm,
        "atr_pct_norm": atr_pct_norm,
        "vol_spike_norm": vol_spike_norm,
        "adx_norm": adx_norm,
        "rsi_pull_norm": rsi_pull_norm,
        "raw": {
            "volume": vol,
            "vol_ma20": vol_ma20,
            "vol_ratio": vol_ratio,
            "atr_pct": atr_pct,
            "vol_spike_ratio": vol_spike_ratio,
            "adx": adx,
            "rsi": rsi
        }
    }
    return norm_dict

def compute_scores_from_ohlcv(ohlcv_1h, ohlcv_1d, weights=None, norm_params=None):
    if weights is None:
        weights = {
            "liquidity_vol": 0.25,
            "atr_percent": 0.25,
            "volume_spike": 0.2,
            "adx": 0.15,
            "rsi_pullback": 0.15
        }
    if norm_params is None:
        norm_params = {}

    out = {}
    for label, raw in (("1h", ohlcv_1h), ("1d", ohlcv_1d)):
        if not raw or len(raw) == 0:
            out[label] = {"error": "no data", "score": 0.0}
            continue
        df = ohlcv_to_df(raw)
        df_ind = compute_indicators(df)
        if df_ind.empty:
            out[label] = {"error": "insufficient data after indicators", "score": 0.0}
            continue
        latest = df_ind.iloc[-1]
        norms = compute_norms_from_indicator_df(latest, norm_params)
        score = compute_simple_score(norms, weights)
        out[label] = {"norms": norms, "score": float(score), "latest_raw": norms["raw"]}
    return out
