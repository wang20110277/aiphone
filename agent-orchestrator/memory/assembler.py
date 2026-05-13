import logging
from memory.redis_memory import RedisHotMemory
from memory.pg_facts import get_recent_facts
from memory.pg_vector import search_similar
from config import settings

logger = logging.getLogger(__name__)


class MemoryAssembler:
    def __init__(self):
        self.redis = RedisHotMemory(settings.redis_url)

    async def assemble(self, biz_type: str, user_key: str, current_input: str = "") -> str:
        parts = []

        hot_facts = self.redis.get_all_facts(biz_type, user_key)
        if hot_facts:
            lines = [f"- [{k}]: {v}" for k, v in list(hot_facts.items())[:5]]
            parts.append("## 用户记忆（近期）\n" + "\n".join(lines))

        pg_facts = await get_recent_facts(biz_type, user_key, days=90, top_k=5)
        if pg_facts:
            lines = [f"- [{f['fact_type']}]: {f['fact_value']} ({f['last_seen_ts'].date()})" for f in pg_facts]
            parts.append("## 用户记忆（长期）\n" + "\n".join(lines))

        return "\n\n".join(parts)
