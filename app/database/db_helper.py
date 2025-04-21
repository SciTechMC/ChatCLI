from flask import g
import mysql.connector
import os

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

