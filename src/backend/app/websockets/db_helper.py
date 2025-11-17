import asyncmy
import os
import logging
from dotenv import load_dotenv
from asyncmy.cursors import DictCursor

load_dotenv()

# Configure module logger
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "autocommit": True,
    "cursorclass": DictCursor,
}

async def get_conn():
    """
    Acquire an aiomysql connection using environment configuration.
    Raises an exception if connection fails.
    """
    try:
        conn = await asyncmy.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error("Failed to connect to database: %s", e, exc_info=e)
        raise

async def fetch_records(
    table: str,
    where_clause: str = None,
    params: tuple = (),
    order_by: str = None,
    limit: int = None,
    fetch_all: bool = True
) -> list[dict]:
    """
    Run a SELECT query and return rows as dicts.
    Raises on errors after logging.
    """
    sql = f"SELECT * FROM `{table}`"
    if where_clause:
        sql += " WHERE " + where_clause
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += " LIMIT %s"
        params = (*params, limit)

    conn = None
    try:
        conn = await get_conn()
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            if fetch_all:
                rows = await cur.fetchall()
            else:
                rows = await cur.fetchone()
            return rows
    except Exception as e:
        logger.error("Error fetching records from %s: %s", table, e, exc_info=e)
        raise
    finally:
        if conn:
            conn.close()

async def insert_record(table: str, data: dict) -> int:
    """
    Insert a row into the specified table.
    Returns the lastrowid. Raises on error.
    """
    cols = ", ".join(f"`{col}`" for col in data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
    conn = None
    try:
        conn = await get_conn()
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(data.values()))
            await conn.commit()
            return cur.lastrowid
    except Exception as e:
        logger.error("Error inserting record into %s: %s", table, e, exc_info=e)
        raise
    finally:
        if conn:
            conn.close()

async def update_records(
    table: str,
    data: dict,
    where_clause: str,
    where_params: tuple = ()
) -> int:
    """
    Update rows in the specified table.
    Returns number of rows affected. Raises on error.
    """
    set_clause = ", ".join(f"`{col}` = %s" for col in data.keys())
    sql = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
    params = tuple(data.values()) + where_params
    conn = None
    try:
        conn = await get_conn()
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            await conn.commit()
            return cur.rowcount
    except Exception as e:
        logger.error("Error updating records in %s: %s", table, e, exc_info=e)
        raise
    finally:
        if conn:
            conn.close()