# DEPRECATED: 使用 memory/store.py (SQLAlchemy 2.0 async ORM)
import psycopg
from config import settings


async def search_similar(biz_type: str, user_key: str, query_embedding: list, top_k: int = 3, days: int = 180) -> list[dict]:
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT content, tags, ts,
                1 - (embedding <=> %s::vector) as similarity
                FROM callbot.user_memory_vector
                WHERE biz_type = %s AND user_key = %s
                  AND ts >= now() - interval '%s days'
                ORDER BY embedding <=> %s::vector
                LIMIT %s""",
                (str(query_embedding), biz_type, user_key, days, str(query_embedding), top_k),
            )
            rows = await cur.fetchall()
            return [{"content": r[0], "tags": r[1], "ts": r[2], "similarity": r[3]} for r in rows]


async def insert_vector(biz_type: str, user_key: str, content: str, embedding: list, source_call_id: str = None):
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO callbot.user_memory_vector (biz_type, user_key, content, embedding, source_call_id, ts)
                VALUES (%s, %s, %s, %s::vector, %s, now())""",
                (biz_type, user_key, content, str(embedding), source_call_id),
            )
            await conn.commit()
