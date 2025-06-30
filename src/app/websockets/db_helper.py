import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "autocommit": True,
}

async def get_conn():
    return await aiomysql.connect(**DB_CONFIG)

async def fetch_records(table, where_clause=None, params=(), order_by=None, limit=None, fetch_all=True):
    sql = f"SELECT * FROM `{table}`"
    if where_clause:
        sql += " WHERE " + where_clause
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += " LIMIT %s"
        params = (*params, limit)
    async with await get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params)
            return await cur.fetchall() if fetch_all else cur

async def insert_record(table, data: dict):
    cols = ", ".join(f"`{col}`" for col in data.keys())
    vals_placeholders = ", ".join(["%s"] * len(data))
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({vals_placeholders})"
    async with await get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(data.values()))
            await conn.commit()
            return cur.lastrowid

async def update_records(table, data: dict, where_clause: str, where_params: tuple = ()):
    set_clause = ", ".join(f"`{col}` = %s" for col in data.keys())
    sql = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
    params = tuple(data.values()) + where_params
    async with await get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            await conn.commit()
            return cur.rowcount