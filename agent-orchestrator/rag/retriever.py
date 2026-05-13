"""Agentic RAG 检索 - SQLAlchemy 2.0 + pgvector"""
import logging
from sqlalchemy import text
from database import async_session
from llm.service import get_llm_service

logger = logging.getLogger(__name__)

TOP_K = 3
SIMILARITY_THRESHOLD = 0.7


async def retrieve_scripts(biz_type: str, user_input: str, top_k: int = TOP_K) -> list[dict]:
    """根据用户输入和业务类型检索最相关话术"""
    llm = get_llm_service()
    query_embedding = await llm.get_embeddings(user_input)
    if not query_embedding:
        logger.warning("embedding 生成失败，跳过 RAG")
        return []

    async with async_session() as session:
        stmt = text("""
            SELECT title, content, scene, conditions, tags,
                   1 - (embedding <=> :embedding::vector) AS score
            FROM callbot.script_library
            WHERE biz_type = :biz_type
              AND is_active = TRUE
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)
        result = await session.execute(stmt, {
            "embedding": str(query_embedding),
            "biz_type": biz_type,
            "top_k": top_k,
        })
        return [
            {
                "title": r[0], "content": r[1], "scene": r[2],
                "score": round(float(r[5]), 4),
            }
            for r in result.fetchall()
            if float(r[5]) >= SIMILARITY_THRESHOLD
        ]


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
