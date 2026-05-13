# DEPRECATED: 使用 memory/store.py (SQLAlchemy 2.0 async ORM)
import psycopg
from config import settings


async def get_recent_facts(biz_type: str, user_key: str, days: int = 90, top_k: int = 5) -> list[dict]:
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT fact_type, fact_value, last_seen_ts
                FROM callbot.user_memory_fact
                WHERE biz_type = %s AND user_key = %s
                  AND (expire_ts IS NULL OR expire_ts > now())
                  AND last_seen_ts >= now() - interval '%s days'
                ORDER BY last_seen_ts DESC LIMIT %s""",
                (biz_type, user_key, days, top_k),
            )
            rows = await cur.fetchall()
            return [{"fact_type": r[0], "fact_value": r[1], "last_seen_ts": r[2]} for r in rows]


async def upsert_fact(biz_type: str, user_key: str, fact_type: str, fact_value: dict, source_call_id: str = None):
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO callbot.user_memory_fact (biz_type, user_key, fact_type, fact_value, first_seen_ts, last_seen_ts, source_call_id)
                VALUES (%s, %s, %s, %s, now(), now(), %s)
                ON CONFLICT ON CONSTRAINT user_memory_fact_pkey DO UPDATE
                SET fact_value = EXCLUDED.fact_value, last_seen_ts = now()""",
                (biz_type, user_key, fact_type, fact_value, source_call_id),
            )
            await conn.commit()
