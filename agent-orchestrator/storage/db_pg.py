# DEPRECATED: 使用 storage/repository.py (SQLAlchemy 2.0 async ORM)
import psycopg
from config import settings


def get_connection():
    return psycopg.connect(settings.pg_dsn)


async def insert_call_session(state_dict: dict):
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO callbot.call_session
                (call_id, fs_uuid, biz_type, task_id, user_id, phone_hash, user_key, start_ts, identity_verified, recording_notice_played)
                VALUES (gen_random_uuid(), %(fs_uuid)s, %(biz_type)s, %(task_id)s, %(core_user_id)s, %(phone_hash)s, %(user_key)s, now(), %(identity_verified)s, %(recording_notice_played)s)""",
                state_dict,
            )
            await conn.commit()


async def update_call_session_end(fs_uuid: str, end_ts, hangup_cause: str, result_code: str):
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """UPDATE callbot.call_session SET end_ts = %s, hangup_cause = %s, result_code = %s WHERE fs_uuid = %s""",
                (end_ts, hangup_cause, result_code, fs_uuid),
            )
            await conn.commit()


async def insert_turn(call_id: str, fs_uuid: str, biz_type: str, user_key: str, role: str, text: str, asr_conf: float = None):
    async with await psycopg.AsyncConnection.connect(settings.pg_dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO callbot.call_turn (call_id, fs_uuid, biz_type, user_key, role, text, asr_conf, ts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())""",
                (call_id, fs_uuid, biz_type, user_key, role, text, asr_conf),
            )
            await conn.commit()
