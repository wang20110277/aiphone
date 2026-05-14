"""记忆存储层 - SQLAlchemy 2.0 async ORM（事实 + 向量）"""
from datetime import datetime, timedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import UserMemoryFact, UserMemoryVector
from database import async_session


async def get_recent_facts(biz_type: str, user_key: str, days: int = 90, top_k: int = 5) -> list[dict]:
    """查询用户近 N 天的结构化记忆事实"""
    cutoff = datetime.now() - timedelta(days=days)
    async with async_session() as session:
        stmt = (
            select(UserMemoryFact)
            .where(
                UserMemoryFact.biz_type == biz_type,
                UserMemoryFact.user_key == user_key,
                (UserMemoryFact.expire_ts.is_(None)) | (UserMemoryFact.expire_ts > datetime.now()),
                UserMemoryFact.last_seen_ts >= cutoff,
            )
            .order_by(UserMemoryFact.last_seen_ts.desc())
            .limit(top_k)
        )
        result = await session.execute(stmt)
        return [
            {"fact_type": r.fact_type, "fact_value": r.fact_value, "last_seen_ts": r.last_seen_ts}
            for r in result.scalars().all()
        ]


async def upsert_fact(biz_type: str, user_key: str, user_id: str,
                      fact_type: str, fact_value: dict, source_call_id: str | None = None) -> None:
    """插入或更新用户记忆事实"""
    async with async_session() as session:
        stmt = (
            select(UserMemoryFact)
            .where(
                UserMemoryFact.biz_type == biz_type,
                UserMemoryFact.user_key == user_key,
                UserMemoryFact.fact_type == fact_type,
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.fact_value = fact_value
            existing.last_seen_ts = datetime.now()
            existing.update_time = datetime.now()
        else:
            session.add(UserMemoryFact(
                biz_type=biz_type, user_id=user_id, user_key=user_key,
                fact_type=fact_type, fact_value=fact_value,
                confidence=1.0, source_call_id=source_call_id,
            ))
        await session.commit()


async def search_similar_vectors(biz_type: str, user_key: str,
                                 query_embedding: list[float], top_k: int = 3,
                                 days: int = 180) -> list[dict]:
    """向量相似度检索（使用 pgvector 余弦距离）"""
    cutoff = datetime.now() - timedelta(days=days)
    async with async_session() as session:
        stmt = text("""
            SELECT content, tags, ts,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM callbot.user_memory_vector
            WHERE biz_type = :biz_type AND user_key = :user_key
              AND ts >= :cutoff
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)
        result = await session.execute(stmt, {
            "embedding": str(query_embedding),
            "biz_type": biz_type,
            "user_key": user_key,
            "cutoff": cutoff,
            "top_k": top_k,
        })
        return [
            {"content": r[0], "tags": r[1], "ts": r[2], "similarity": float(r[3])}
            for r in result.fetchall()
        ]


async def insert_vector(biz_type: str, user_key: str, user_id: str,
                        content: str, embedding: list[float],
                        source_call_id: str | None = None) -> None:
    """插入向量记忆"""
    async with async_session() as session:
        stmt = text("""
            INSERT INTO callbot.user_memory_vector
            (biz_type, user_id, user_key, content, embedding, source_call_id, ts)
            VALUES (:biz_type, :user_id, :user_key, :content, :embedding::vector, :source_call_id, now())
        """)
        await session.execute(stmt, {
            "biz_type": biz_type, "user_id": user_id, "user_key": user_key,
            "content": content, "embedding": str(embedding),
            "source_call_id": source_call_id,
        })
        await session.commit()
