from flask import g
import mysql.connector
from mysql.connector import Error
import logging
import os
from app.config import VALID_TABLES

def get_db():
    """
    :return: A MySQL database connection stored in Flask's 'g' object.
    """
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_DEV_USER"),
            password=os.getenv("DB_DEV_PASSWORD"),
            database=os.getenv("DB_NAME_DEV"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    return g.db

def close_db():
    """
    Close the DB connection if it exists in 'g'.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def insert_record(table: str, data: dict) -> int:
    """
    Insert a single row into `table`.

    :param table: Name of the table (must be in VALID_TABLES)
    :param data:  Dict mapping column names to values, e.g.
                  {"email": "foo@example.com", "revoked": False}
    :return:      The newly inserted row's auto-increment ID.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Table '{table}' is not writable via insert_record")

    cols = ", ".join(f"`{col}`" for col in data.keys())
    vals_placeholders = ", ".join(["%s"] * len(data))
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({vals_placeholders})"

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, tuple(data.values()))
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

    :param table:        Name of the table (must be in VALID_TABLES)
    :param data:         Dict mapping columns to new values, e.g.
                         {"revoked": True, "expires_at": some_datetime}
    :param where_clause: SQL WITHOUT the leading 'WHERE', e.g. "userID = %s AND revoked = %s"
    :param where_params: Tuple of values to bind in where_clause.
    :return:             Number of rows affected.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Table '{table}' is not updatable via update_records")

    set_clause = ", ".join(f"`{col}` = %s" for col in data.keys())
    sql = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
    params = tuple(data.values()) + where_params

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
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

    :param table:        Name of the table (must be in config.VALID_TABLES).
    :param where_clause: SQL WITHOUT leading 'WHERE', e.g. "userID = %s".
    :param params:       Tuple of values to bind into where_clause (and/or LIMIT).
    :param order_by:     Optional "column_name ASC|DESC".
    :param limit:        Optional max number of rows to return.
    :param fetch_all:    If True, returns list of dicts. Otherwise returns raw cursor.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Table '{table}' is not in VALID_TABLES")

    db = get_db()
    cursor = db.cursor(dictionary=True)

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

    return cursor.fetchall() if fetch_all else cursor