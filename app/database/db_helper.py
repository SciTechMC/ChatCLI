from flask import g
import mysql.connector
from chatcli.app.config import db_login

def get_db():
    """
    :return: A MySQL database connection stored in Flask's 'g' object.
    """
    if 'db' not in g:
        env = db_login()
        g.db = mysql.connector.connect(
            host="localhost",
            user=env["user"],
            password=env["password"],
            database=env["db"]
        )
    return g.db

def close_db():
    """
    Close the DB connection if it exists in 'g'.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

