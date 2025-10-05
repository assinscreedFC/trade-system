import json
import redis.asyncio as redis
from loguru import logger

class RedisPublisher:
    def __init__(self, redis_url="redis://redis:6379/0", stream_name="alerts_stream"):
        self.r = redis.from_url(redis_url)
        self.stream = stream_name

    async def publish(self, payload: dict):
        try:
            # store JSON under field "data"
            await self.r.xadd(self.stream, {"data": json.dumps(payload)})
        except Exception as e:
            logger.exception("Failed to publish to redis: %s", e)
