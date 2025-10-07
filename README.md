# trade-system

# ⚡ Crypto Alert Bot

> Bot Python asynchrone pour surveiller les marchés crypto et générer des alertes intelligentes en temps réel.

---

## 🌐 Description

Crypto Alert Bot utilise **Redis Streams** et `asyncio` pour gérer des flux d’événements en direct. Il est conçu pour être modulaire, scalable et prêt pour les notifications ou dashboards.

- Surveillance temps réel des coins / symboles crypto.
- Calcul de scores et indicateurs techniques (volume, ATR%, RSI, ADX, ratio de volume).
- Architecture asynchrone avec plusieurs tâches (`_worker_task`, `_alert_task`).

---

## ⚙️ Installation

```bash
git clone <URL_DU_DEPOT>
cd crypto-alert-bot
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```
Folders:
- config/
- services/scanner/
- services/bot/
- services/worker/
- .github/workflows/


docker run -d --name redis -p 6379:6379 redis