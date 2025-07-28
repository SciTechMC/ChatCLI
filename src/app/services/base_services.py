import hashlib
import mysql.connector
from flask import current_app

from app.errors import BadRequest, Conflict, APIError
from app.database.db_helper import fetch_records, insert_record

# module logger
import logging
logger = logging.getLogger(__name__)


def authenticate_token(session_token: str) -> str | None:
    """
    Given a plain session token, returns the associated username if valid; otherwise None.
    """
    if not session_token:
        return None
    try:
        token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
        sessions = fetch_records(
            table="session_tokens",
            where_clause="session_token = %s AND revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()",
            params=(token_hash,),
            fetch_all=True
        )
        if not sessions:
            return None
        user_id = sessions[0]["userID"]
        users = fetch_records(
            table="users",
            where_clause="userID = %s AND email_verified = TRUE AND disabled = FALSE",
            params=(user_id,),
            fetch_all=True
        )
        if not users:
            return None
        return users[0]["username"]
    except Exception as e:
        logger.error("Error authenticating token: %s", e, exc_info=e)
        return None


def verify_connection(data: dict) -> dict:
    """
    Health-check endpoint logic.
    """
    # No business logic needed beyond health check
    return {"message": "Server is reachable!"}


def subscribe(data: dict) -> dict:
    """
    Subscribes an email address.
    Expects data: { "email": str }
    """
    email = data.get("email")
    if not email:
        raise BadRequest("Email is required.")
    try:
        existing = fetch_records(
            table="email_subscribers",
            where_clause="email = %s",
            params=(email,),
            fetch_all=True
        )
        if existing:
            raise Conflict("This email is already subscribed.")
        insert_record(
            table="email_subscribers",
            data={"email": email}
        )
    except Conflict:
        raise
    except mysql.connector.Error as err:
        logger.error("Database error subscribing email %s: %s", email, err, exc_info=err)
        raise APIError("Database error.")
    except Exception as e:
        logger.error("Unexpected error during subscription: %s", e, exc_info=e)
        raise APIError("Internal server error.")
    return {"message": "Subscription successful."}