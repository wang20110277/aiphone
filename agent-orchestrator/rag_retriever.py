import logging
import asyncio
import asyncpg
from llm_base import get_embedding

logger = logging.getLogger(__name__)

PG_DSN = "postgresql://callbot:callbot@localhost:5432/callbot_0"
TOP_K = 3
SIMILARITY_THRESHOLD = 0.7


async def retrieve_scripts(
    biz_type: str,
    user_input: str,
    top_k: int = TOP_K,
    pool: asyncpg.Pool | None = None,
) -> list[dict]:
    """Agentic RAG: 根据用户输入和业务类型检索最相关话术"""
    query_embedding = await get_embedding(user_input)
    if not query_embedding:
        logger.warning("embedding generation failed, skipping RAG")
        return []

    own_pool = pool is None
    if own_pool:
        pool = await asyncpg.create_pool(PG_DSN, min_size=1, max_size=4)

    try:
        rows = await pool.fetch(
            """
            SELECT title, content, scene, conditions, tags,
                   1 - (embedding <=> $1::vector) AS score
            FROM callbot.script_library
            WHERE biz_type = $2
              AND is_active = TRUE
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            str(query_embedding),
            biz_type,
            top_k,
        )
        results = []
        for r in rows:
            if r["score"] >= SIMILARITY_THRESHOLD:
                results.append({
                    "title": r["title"],
                    "content": r["content"],
                    "scene": r["scene"],
                    "score": round(float(r["score"]), 4),
                })
        return results
    finally:
        if own_pool:
            await pool.close()


def build_rag_block(scripts: list[dict]) -> str:
    """将检索到的话术格式化为 Prompt 注入块"""
    if not scripts:
        return ""
    lines = ["## 参考话术（按相关度排序）"]
    for i, s in enumerate(scripts, 1):
        lines.append(f"{i}. [{s['scene']}] {s['title']}（相关度: {s['score']}）")
        lines.append(f"   {s['content']}")
    lines.append("\n请参考以上话术风格和内容回复用户，可根据实际情况灵活调整措辞。")
    return "\n".join(lines)
