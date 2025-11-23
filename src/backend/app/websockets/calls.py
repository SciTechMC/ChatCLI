import logging
import services

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  CALL INVITE
# ---------------------------------------------------------------------------

async def call_invite(caller: str, chat_id: int):
    """Notify all members of a chat that a call invite was sent."""
    subscribers = services.chat_subscriptions.get(chat_id, set())

    for ws in subscribers.copy():
        try:
            await ws.send_json({
                "type": "call_invite",
                "from": caller,
                "chatID": chat_id,
            })
        except Exception:
            logger.warning("Subscriber in chat %s disconnected, removing.", chat_id)
            subscribers.discard(ws)


# ---------------------------------------------------------------------------
#  CALL ACCEPT
# ---------------------------------------------------------------------------

async def call_accept(username: str, chat_id: int, call_id: str):
    """Broadcast that the user accepted the call."""
    subscribers = services.chat_subscriptions.get(chat_id, set())

    for ws in subscribers.copy():
        try:
            await ws.send_json({
                "type": "call_accept",
                "from": username,
                "chatID": chat_id,
                "call_id": call_id,
            })
        except Exception:
            logger.warning("Subscriber in chat %s disconnected, removing.", chat_id)
            subscribers.discard(ws)


# ---------------------------------------------------------------------------
#  CALL DECLINE
# ---------------------------------------------------------------------------

async def call_decline(username: str, chat_id: int):
    subscribers = services.chat_subscriptions.get(chat_id, set())

    for ws in subscribers.copy():
        try:
            await ws.send_json({
                "type": "call_decline",
                "from": username,
                "chatID": chat_id,
            })
        except Exception:
            subscribers.discard(ws)


# ---------------------------------------------------------------------------
#  CALL END
# ---------------------------------------------------------------------------

async def call_end(username: str, chat_id: int):
    subscribers = services.chat_subscriptions.get(chat_id, set())

    for ws in subscribers.copy():
        try:
            await ws.send_json({
                "type": "call_end",
                "from": username,
                "chatID": chat_id,
            })
        except Exception:
            subscribers.discard(ws)