import os

def email_acc():
    return os.getenv("EMAIL_USER")

def email_pssw():
    return os.getenv("EMAIL_PASSWORD")

def db_login():
    return {
        "user": os.getenv("DB_DEV_USER"),
        "password": os.getenv("DB_DEV_PASSWORD"),
        "db": os.getenv("DB_NAME_DEV"),
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 3306))
    }