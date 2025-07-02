import logging
from flask import g
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from mysql.connector.cursor import MySQLCursorDict
from app.config import VALID_TABLES
from functools import wraps

load_dotenv()

# ——————————————————————————————————————————————————————————
# 1) DEBUG CURSOR: logs every time you hit "participants"
# ——————————————————————————————————————————————————————————
class DebugCursor(MySQLCursorDict):
    def execute(self, operation, params=None, multi=False):
        sql_upper = operation.strip().upper()
        if "PARTICIPANTS" in sql_upper:
            logging.getLogger("db-debug").debug(
                f"[PARTICIPANTS SQL] {operation!r}  params={params}"
            )
        return super().execute(operation, params=params, multi=multi)


# ——————————————————————————————————————————————————————————
# 2) get_db() — now uses DebugCursor by default
# ——————————————————————————————————————————————————————————
def get_db():
    """
    :return: A MySQL database connection stored in Flask's 'g' object,
             configured to use DebugCursor so you see every participants
             INSERT/UPDATE/DELETE in your Flask log.
    """
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "chatcli"),
            port=int(os.getenv("DB_PORT", 3306)),
            autocommit=True,
        )
    return g.db

def close_db():
    """
    Close the DB connection if it exists in 'g'.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def transactional(fn):
    """
    Decorator: run entire function inside one DB transaction.
    If any exception is raised, roll back all changes.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        conn = get_db()
        # Turn off autocommit so that DML starts a transaction
        conn.autocommit = False

        try:
            result = fn(*args, **kwargs)
            conn.commit()     # commit everything at once
            return result
        except Exception:
            conn.rollback()   # undo everything
            raise
        finally:
            # Restore default for subsequent operations
            conn.autocommit = True
    return wrapper

def insert_record(table: str, data: dict) -> int:
    """
    Insert a single row into `table`.
    Only issues a commit if conn.autocommit == True.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Table '{table}' is not writable via insert_record")

    cols = ", ".join(f"`{col}`" for col in data.keys())
    vals_placeholders = ", ".join(["%s"] * len(data))
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({vals_placeholders})"

    conn = get_db()
    cursor = conn.cursor(cursor_class=DebugCursor)
    try:
        cursor.execute(sql, tuple(data.values()))
        # only auto-commit if autocommit is on
        if conn.autocommit:
            conn.commit()
        return cursor.lastrowid
    except Error as e:
        conn.rollback()
        logging.error(f"[insert_record] Error inserting into {table}: {e}\nSQL: {sql}\nData: {data}")
        raise

def update_records(
    table: str,
    data: dict,
    where_clause: str,
    where_params: tuple = ()
) -> int:
    """
    Update one or more rows in `table`.
    Only issues a commit if conn.autocommit == True.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Table '{table}' is not updatable via update_records")

    set_clause = ", ".join(f"`{col}` = %s" for col in data.keys())
    sql = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
    params = tuple(data.values()) + where_params

    conn = get_db()
    cursor = conn.cursor(cursor_class=DebugCursor)
    try:
        cursor.execute(sql, params)
        if conn.autocommit:
            conn.commit()
        return cursor.rowcount
    except Error as e:
        conn.rollback()
        logging.error(f"[update_records] Error updating {table}: {e}\nSQL: {sql}\nParams: {params}")
        raise

def fetch_records(
    table: str,
    where_clause: str = None,
    params: tuple = (),
    order_by: str = None,
    limit: int = None,
    fetch_all: bool = True
):
    """
    Generic fetcher for any whitelisted table.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Table '{table}' is not in VALID_TABLES")

    db = get_db()
    cursor = db.cursor(dictionary=True, cursor_class=DebugCursor)

    sql = f"SELECT * FROM `{table}`"
    if where_clause:
        sql += " WHERE " + where_clause
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += " LIMIT %s"
        params = (*params, limit)

    try:
        cursor.execute(sql, params)
    except Error as e:
        logging.error(f"[fetch_records] Error on {table}: {e}\nSQL: {sql}\nParams: {params}")
        raise

    if fetch_all:
        return cursor.fetchall()
    else:
        return cursor.fetchone()  # <-- Always return a dict or None
