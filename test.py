import asyncio
import redis.asyncio as redis
import json


async def test():
    r = redis.from_url("redis://localhost:6379", decode_responses=True)
    ALERT_STREAM = "ALERT_STREAM"

    # Ajouter un message test
    payload = {"symbol": "BTCUSDT", "price": 61000}
    msg_id = await r.xadd(ALERT_STREAM, {"data": json.dumps(payload)})
    print("Message ajouté ID =", msg_id)

    # Lire tous les messages
    messages = await r.xrange(ALERT_STREAM, "-", "+")
    print("Contenu du stream :", messages)

    await r.close()


asyncio.run(test())
