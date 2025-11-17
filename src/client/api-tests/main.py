import time
import random
import string
from dataclasses import dataclass
import json
import requests

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule

console = Console()
BASE_URL = "http://localhost:5123"


# ------------------------- Helpers ------------------------- #

@dataclass
class UserTokens:
    username: str
    password: str
    access_token: str
    refresh_token: str


def _rand_suffix(length: int = 6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _pretty_json(data):
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return str(data)


def api_post(path: str, json_data: dict):
    url = BASE_URL + path
    console.print(Rule(f"[bold cyan]POST {url}"))

    console.print(
        Panel(_pretty_json(json_data), title="Payload", border_style="cyan")
    )

    resp = requests.post(url, json=json_data)

    console.print(f"[bold]Status:[/bold] [magenta]{resp.status_code}[/magenta]")

    try:
        body = resp.json()
        console.print(
            Panel(_pretty_json(body), title="Response JSON", border_style="green")
        )
    except Exception:
        text = (resp.text or "")[:300]
        body = {"_raw": text}
        console.print(
            Panel(text, title="Raw Text", border_style="yellow")
        )

    resp.raise_for_status()
    return body


def api_get(path: str, params=None):
    url = BASE_URL + path
    console.print(Rule(f"[bold cyan]GET {url}"))

    if params:
        console.print(
            Panel(_pretty_json(params), title="Query Params", border_style="cyan")
        )

    resp = requests.get(url, params=params)
    console.print(f"[bold]Status:[/bold] [magenta]{resp.status_code}[/magenta]")

    try:
        body = resp.json()
        console.print(
            Panel(_pretty_json(body), title="Response JSON", border_style="green")
        )
    except Exception:
        text = (resp.text or "")[:300]
        body = {"_raw": text}
        console.print(Panel(text, title="Raw Text", border_style="yellow"))

    resp.raise_for_status()
    return body


# ------------------------- User Flow ------------------------- #

def full_user_flow(name: str, skip_verification: bool) -> UserTokens:
    """
    Perform the FULL flow for a single user in correct order:
    register → verify → login → refresh → profile → submit-profile →
    change-password → logout → logout-all
    """

    # ------------------------- REGISTER ------------------------- #
    user_suffix = _rand_suffix()
    username = f"{name}_{user_suffix}"
    email = f"{username}@example.com"
    password = "Aa123456!"

    console.print(Rule(f"[bold blue]User Flow: {username}[/bold blue]"))
    console.print(
        Panel(
            f"[bold]Username:[/bold] {username}\n[bold]Email:[/bold] {email}",
            border_style="blue",
        )
    )

    api_post("/user/register", {
        "username": username,
        "password": password,
        "email": email,
    })

    time.sleep(0.1)

    # ------------------------- EMAIL VERIFICATION ------------------------- #
    if skip_verification:
        console.print("[yellow]Skipping email verification[/yellow]")
    else:
        code = Prompt.ask(
            f"Enter email verification code for [cyan]{username}[/cyan]"
        ).strip()

        api_post("/user/verify-email", {
            "username": username,
            "email_token": code,
        })

    # ------------------------- LOGIN ------------------------- #
    login_resp = api_post("/user/login", {
        "username": username,
        "password": password,
    })

    access = login_resp["access_token"]
    refresh = login_resp["refresh_token"]

    tokens = UserTokens(
        username=username,
        password=password,
        access_token=access,
        refresh_token=refresh,
    )

    console.print(
        Panel(f"Logged in as {username}", border_style="green")
    )

    # ------------------------- REFRESH TOKEN ------------------------- #
    api_post("/user/refresh-token", {
        "refresh_token": refresh
    })

    # ------------------------- PROFILE ------------------------- #
    api_post("/user/profile", {
        "session_token": access
    })

    # ------------------------- SUBMIT PROFILE ------------------------- #
    api_post("/user/submit-profile", {
        "session_token": access,
        "username": username,
        "email": f"{username}+updated@example.com",
    })

    # ------------------------- CHANGE PASSWORD ------------------------- #
    api_post("/user/change-password", {
        "session_token": access,
        "current_password": password,
        "new_password": "Bb123456!",
    })

    # ------------------------- LOGOUT ------------------------- #
    api_post("/user/logout", {
        "session_token": access,
        "refresh_token": refresh,
    })

    # ------------------------- LOGOUT ALL ------------------------- #
    api_post("/user/logout-all", {
        "session_token": access,
    })

    return tokens


# ------------------------- Chat Flow ------------------------- #

def exercise_chat_endpoints(user1: UserTokens, user2: UserTokens):
    console.print(
        Rule(f"[bold magenta]Chat flow: {user1.username} ⇄ {user2.username}[/bold magenta]")
    )

    # fetch initial chats
    api_post("/chat/fetch-chats", {"session_token": user1.access_token})

    # create chat
    create = api_post("/chat/create-chat", {
        "session_token": user1.access_token,
        "receiver": user2.username
    })

    chat_id = (
        create.get("chatID")
        or create.get("chatId")
        or create.get("chat_id")
    )
    if chat_id is None:
        raise RuntimeError("Chat ID missing")

    console.print(Panel(f"Created chat ID: {chat_id}", border_style="magenta"))

    # more chat actions
    api_post("/chat/fetch-chats", {"session_token": user1.access_token})
    api_post("/chat/get-members", {"session_token": user1.access_token, "chatID": chat_id})
    api_post("/chat/messages", {
        "session_token": user1.access_token,
        "chatID": chat_id,
        "limit": 50
    })
    api_post("/chat/archive-chat", {"session_token": user1.access_token, "chatID": chat_id})
    api_post("/chat/fetch-archived", {"session_token": user1.access_token})
    api_post("/chat/unarchive-chat", {"session_token": user1.access_token, "chatID": chat_id})


# ------------------------- MAIN ------------------------- #

def main():
    console.print(Rule("[bold white]Chat API End-to-End Usage Test[/bold white]"))

    skip = Prompt.ask(
        "Skip email verification? (y/n)",
        choices=["y", "n"],
        default="y"
    ) == "y"

    # TWO USERS — FULL FLOW
    user1 = full_user_flow("testuser1", skip)
    user2 = full_user_flow("testuser2", skip)

    # CHAT FLOW
    exercise_chat_endpoints(user1, user2)

    console.print(
        Panel("[bold green]Usage test completed successfully![/bold green]", border_style="green")
    )


if __name__ == "__main__":
    main()