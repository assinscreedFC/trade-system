import requests
import json
from collections import defaultdict

# URLs Bitget
URL_COINS = "https://api.bitget.com/api/v2/spot/public/coins"
URL_SYMBOLS = "https://api.bitget.com/api/v2/spot/public/symbols"
OUT_FILE = "./data/filtered_pairs.json"
# Ordre de potentiel (priorité de tri)
BLOCKCHAIN_ORDER = [
    "BTC", "ERC20", "TRC20", "SOL", "Polygon", "AVAXC",
    "ARBITRUM", "APTOS", "SUI"
]

# 1) Récupérer les données (avec gestion d'erreur basique)
def fetch_json(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])

coins_data = fetch_json(URL_COINS)
symbols_data = fetch_json(URL_SYMBOLS)

# 2) Construire un mapping coin -> chains utiles (filtrer par BLOCKCHAIN_ORDER)
coins_chains = {}  # coin -> list of chain dicts (filtered)
for c in coins_data:
    coin_name = c.get("coin")
    chains = []
    for ch in c.get("chains", []):
        chain_name = ch.get("chain")
        if chain_name in BLOCKCHAIN_ORDER and ch.get("withdrawable") == "true":
            chains.append({
                "chain": chain_name,
                "needTag": ch.get("needTag"),
                "withdrawFee": ch.get("withdrawFee"),
                "minWithdrawAmount": ch.get("minWithdrawAmount"),
                "contractAddress": ch.get("contractAddress"),
                "congestion": ch.get("congestion")
            })
    if chains:
        coins_chains[coin_name] = chains

# 3) Filtrer symbols : ne garder que les paires contre USDT et dont baseCoin est dans coins_chains
filtered_pairs = defaultdict(lambda: {"coin": None, "chains": [], "pairs": []})
for s in symbols_data:
    base = s.get("baseCoin")
    quote = s.get("quoteCoin")
    status = s.get("status")
    symbol_name = s.get("symbol")
    # Condition : paire USDT, coin supporté par chain utiles, et paire en ligne
    if quote == "USDT" and base in coins_chains and status == "online":
        # prepare entry
        entry = filtered_pairs[base]
        entry["coin"] = base
        # add chain infos (ensure unique)
        for ch in coins_chains[base]:
            if ch not in entry["chains"]:
                entry["chains"].append(ch)
        # add pair metadata
        #"baseCoin": "ENA",
            #"quoteCoin": "EUR",
        entry["pairs"].append({
            "symbol": symbol_name,
            "baseCoin":s.get("baseCoin"),
            "quoteCoin":s.get("quoteCoin"),
            "minTradeAmount": s.get("minTradeAmount"),
            "maxTradeAmount": s.get("maxTradeAmount"),
            "takerFeeRate": s.get("takerFeeRate"),
            "makerFeeRate": s.get("makerFeeRate"),
            "pricePrecision": s.get("pricePrecision"),
            "quantityPrecision": s.get("quantityPrecision"),
            "minTradeUSDT": s.get("minTradeUSDT"),

        })

# 4) Transformer en liste et trier par ordre de blockchain (on met en tête la meilleure chain disponible)
def sort_key(item):
    # item: {"coin":..., "chains":[...], ...}
    chains = item.get("chains", [])
    # find smallest index among chains (best chain for this coin)
    idxs = []
    for ch in chains:
        try:
            idxs.append(BLOCKCHAIN_ORDER.index(ch["chain"]))
        except ValueError:
            pass
    return min(idxs) if idxs else len(BLOCKCHAIN_ORDER)

result_list = list(filtered_pairs.values())
# remove entries without pairs (filtres de sécurité)
result_list = [r for r in result_list if r["pairs"]]
result_list.sort(key=sort_key)

# 5) Écrire dans JSON

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result_list, f, ensure_ascii=False, indent=4)

print(f"✅ {len(result_list)} coins/paires filtrés enregistrés dans '{OUT_FILE}'")
# Affichage rapide d'exemple
for i, item in enumerate(result_list[:10], 1):
    coin = item["coin"]
    chains = ", ".join(ch["chain"] for ch in item["chains"])
    n_pairs = len(item["pairs"])
    print(f"{i}. {coin} — chains: {chains} — paires USDT: {n_pairs}")
