import json
from typing import Optional

import redis.asyncio as aioredis

from app.agent.conversation import ConversationMemory
from app.config import settings


class RedisCache:
    """Redis 缓存管理器"""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        try:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
            )
            await self._redis.ping()
        except Exception:
            self._redis = None

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def is_connected(self) -> bool:
        return self._redis is not None

    async def save_conversation(
        self, session_id: str, memory: ConversationMemory, ttl: int = settings.CONVERSATION_TTL
    ) -> bool:
        if not self._redis:
            return False
        key = f"conv:{session_id}"
        await self._redis.setex(key, ttl, json.dumps(memory.to_dict(), ensure_ascii=False))
        return True

    async def get_conversation(self, session_id: str) -> Optional[ConversationMemory]:
        if not self._redis:
            return None
        key = f"conv:{session_id}"
        data = await self._redis.get(key)
        if data:
            return ConversationMemory.from_dict(json.loads(data))
        return None

    async def delete_conversation(self, session_id: str) -> bool:
        if not self._redis:
            return False
        key = f"conv:{session_id}"
        await self._redis.delete(key)
        return True

    async def cache_response(
        self, cache_key: str, response: dict, ttl: int = 600
    ) -> bool:
        """缓存通用API响应"""
        if not self._redis:
            return False
        await self._redis.setex(
            f"cache:{cache_key}", ttl,
            json.dumps(response, ensure_ascii=False),
        )
        return True

    async def get_cached_response(self, cache_key: str) -> Optional[dict]:
        if not self._redis:
            return None
        data = await self._redis.get(f"cache:{cache_key}")
        return json.loads(data) if data else None
