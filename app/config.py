from app.dev import email, db_acc

def email_acc():
    return email()

def email_pssw():
    return email("password")

def db_login():
    return db_acc