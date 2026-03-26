import logging
import os
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL")

if redis_url:
    try:
        redis_client = Redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        redis_client = None
else:
    redis_client = None

arq_pool = None
