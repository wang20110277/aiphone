"""Agentic RAG — Adaptive + Corrective retrieval"""
import logging
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from database import async_session
from llm.service import get_llm_service

logger = logging.getLogger(__name__)


# ── Structured output schemas ──

class GradeRetrieval(BaseModel):
    """LLM decides whether retrieval is needed"""
    binary_score: str = Field(description="yes or no")


class GradeDocuments(BaseModel):
    """LLM grades document relevance"""
    binary_score: str = Field(description="relevant or irrelevant")


class RewrittenQuery(BaseModel):
    """LLM rewrites query for better retrieval"""
    query: str = Field(description="rewritten query string")


# ── Core retrieval ──

async def retrieve_scripts(biz_type: str, user_input: str, top_k: int | None = None) -> list[dict]:
    """Vector similarity search against script_library"""
    top_k = top_k or settings.rag_top_k
    threshold = settings.rag_similarity_threshold
    llm = get_llm_service()
    query_embedding = await llm.get_embeddings(user_input)
    if not query_embedding:
        logger.warning("embedding 生成失败，跳过 RAG")
        return []

    async with async_session() as session:
        from sqlalchemy import text
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
            if float(r[5]) >= threshold
        ]


def build_rag_block(scripts: list[dict]) -> str:
    """Format retrieved scripts as prompt injection block"""
    if not scripts:
        return ""
    lines = ["## 参考话术（按相关度排序）"]
    for i, s in enumerate(scripts, 1):
        lines.append(f"{i}. [{s['scene']}] {s['title']}（相关度: {s['score']}）")
        lines.append(f"   {s['content']}")
    lines.append("\n请参考以上话术风格和内容回复用户，可根据实际情况灵活调整措辞。")
    return "\n".join(lines)


# ── Agentic RAG functions ──

async def should_retrieve(user_input: str, biz_type: str) -> bool:
    """LLM decides whether retrieval is needed for this query"""
    llm = get_llm_service()
    structured = llm._chat.with_structured_output(GradeRetrieval, method="json_mode")
    messages = [
        SystemMessage(content="你是一个电话客服系统的检索决策器。判断用户输入是否需要查询知识库话术来辅助回复。简单问候、结束语、确认语不需要检索。业务咨询、产品问题、投诉处理需要检索。"),
        HumanMessage(content=f"业务类型: {biz_type}\n用户输入: {user_input}\n\n需要检索知识库吗？回答 yes 或 no。"),
    ]
    try:
        result = await structured.ainvoke(messages)
        return result.binary_score.lower() == "yes"
    except Exception as e:
        logger.warning(f"should_retrieve 失败，默认检索: {e}")
        return True


async def grade_documents(user_input: str, scripts: list[dict]) -> list[dict]:
    """LLM grades each script for relevance, returns only relevant ones"""
    if not scripts:
        return []
    llm = get_llm_service()
    structured = llm._chat.with_structured_output(GradeDocuments, method="json_mode")

    relevant = []
    for script in scripts:
        messages = [
            SystemMessage(content="你是文档相关性评估器。判断检索到的话术是否与用户问题相关。"),
            HumanMessage(content=f"用户问题: {user_input}\n\n话术内容: {script['content'][:500]}\n\n这段话术与用户问题相关吗？回答 relevant 或 irrelevant。"),
        ]
        try:
            result = await structured.ainvoke(messages)
            if result.binary_score.lower() == "relevant":
                relevant.append(script)
        except Exception as e:
            logger.warning(f"grade_documents 失败，保留该文档: {e}")
            relevant.append(script)
    return relevant


async def rewrite_query(original_query: str, failed_scripts: list[dict]) -> str:
    """LLM rewrites the query for better retrieval"""
    llm = get_llm_service()
    structured = llm._chat.with_structured_output(RewrittenQuery, method="json_mode")
    failed_summary = "\n".join(f"- {s['title']}: {s['content'][:100]}" for s in failed_scripts[:3])
    messages = [
        SystemMessage(content="你是查询优化器。用户的问题检索到了不相关的话术，请改写问题以便检索到更相关的内容。保留原始意图，使用更具体的关键词。"),
        HumanMessage(content=f"原始问题: {original_query}\n\n检索到的不相关话术:\n{failed_summary}\n\n请改写问题:"),
    ]
    try:
        result = await structured.ainvoke(messages)
        return result.query
    except Exception as e:
        logger.warning(f"rewrite_query 失败，使用原始查询: {e}")
        return original_query
