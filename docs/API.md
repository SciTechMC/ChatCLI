# ChatCLI API Reference

Reference for the two ChatCLI backend services:

| Service | Framework | Default port | Base URL |
|---|---|---|---|
| **HTTP API** | Flask (Waitress in prod) | `5123` | `http://<host>:5123` |
| **WebSocket server** | FastAPI (uvicorn) | `8765` | `ws://<host>:8765` |

Client defaults live in [config.js](../src/client/ChatCLI/src/preload/config.js).

---

## Table of contents

1. [Conventions](#conventions)
2. [Route index](#route-index)
3. [Authentication](#authentication)
4. [Errors](#errors)
5. [Rate limits](#rate-limits)
6. [HTTP API — base](#http-api--base)
7. [HTTP API — user](#http-api--user)
8. [HTTP API — chat](#http-api--chat)
9. [WebSocket — `/ws`](#websocket--ws)
10. [WebSocket — `/call/{call_id}`](#websocket--callcall_id)
11. [Object shapes](#object-shapes)
12. [Data model](#data-model)
13. [Behavioural notes](#behavioural-notes)

---

## Conventions

- Every endpoint except `GET /`, `GET /verify-connection`, `GET /subscribe` and `GET /user/reset-password` takes a JSON request body and returns JSON.
- A `POST` with a missing, empty or unparseable body returns `400 Bad request` with `"Invalid JSON format."`. Because the check is `if not data`, a body of `{}`, `[]`, `0`, `""` or `null` is also rejected this way.
- Requests are parsed with `request.get_json(silent=True)`, which requires `Content-Type: application/json`. Any other content type parses as `None` and yields the same `400`. The sole exception is `POST /user/reset-password`, which falls back to form-encoded data.
- Timestamps in responses are ISO 8601 strings. Token expiries are computed in UTC; `messages.timestamp` is written by MariaDB's `CURRENT_TIMESTAMP` in the server's local timezone, and neither carries an offset suffix.
- Username and email comparisons are case-insensitive. This comes from the schema collation (`utf8mb4_unicode_ci`), not from application logic — several queries compare a lowercased input against the column directly.
- There is no API versioning prefix. All paths are as written.
- Both services bind `0.0.0.0`.

---

## Route index

Complete enumeration — 27 HTTP rules across 3 blueprints, plus 2 WebSocket routes. Anything not listed here does not exist.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| `GET` | `/` | — | — |
| `GET` `POST` | `/verify-connection` | — | — |
| `GET` `POST` | `/subscribe` | — | — |
| `GET` | `/user/` | — | — |
| `POST` | `/user/register` | — | 5/min |
| `POST` | `/user/verify-email` | — | 5/min |
| `POST` | `/user/resend-verification` | — | 1/min |
| `POST` | `/user/login` | — | 5/min |
| `POST` | `/user/reset-password-request` | — | 5/min |
| `GET` `POST` | `/user/reset-password` | reset token | 5/min |
| `POST` | `/user/refresh-token` | refresh token | 10/min |
| `POST` | `/user/profile` | session | 10/min |
| `POST` | `/user/submit-profile` | session | 10/min |
| `POST` | `/user/change-password` | session | 5/min |
| `POST` | `/user/logout` | session | 5/min |
| `POST` | `/user/logout-all` | session | 5/min |
| `GET` | `/chat/` | — | — |
| `POST` | `/chat/fetch-chats` | session | — |
| `POST` | `/chat/fetch-archived` | session | — |
| `POST` | `/chat/create-chat` | session | — |
| `POST` | `/chat/create-group` | session | — |
| `POST` | `/chat/get-members` | session | — |
| `POST` | `/chat/add-members` | session | — |
| `POST` | `/chat/remove-members` | session | — |
| `POST` | `/chat/messages` | session | — |
| `POST` | `/chat/archive-chat` | session | 10/min |
| `POST` | `/chat/unarchive-chat` | session | 10/min |
| `WS` | `/ws` | session (in-band) | — |
| `WS` | `/call/{call_id}` | session (in-band) | — |

Flask additionally answers `HEAD` and `OPTIONS` on every `GET` rule. `POST`-only rules answer `OPTIONS`. Any other method returns `405`.

Templates `subscribe.html`, `username_input.html` and `welcome.html` exist in [templates/](../src/backend/app/templates/) but no route renders them; only `index.html` and `reset_password.html` are reachable.

---

## Authentication

Two token types, both issued by `POST /user/login`:

| Token | Lifetime | Purpose |
|---|---|---|
| `access_token` (a.k.a. `session_token`) | 1 day | Authenticates every protected request |
| `refresh_token` | `REFRESH_TOKEN_DAYS` days (default 60) | Exchanged for a new pair via `POST /user/refresh-token` |

Tokens are sent **in the JSON request body**, not in an `Authorization` header. The field name is `session_token` on every protected endpoint:

```json
{ "session_token": "…", "chatID": 12 }
```

Server-side, tokens are stored as SHA-256 hashes; the plaintext value is returned to the client once at issue time and never again.

The two services validate the same token against **different predicates**:

| | HTTP (`base_services.authenticate_token`) | WebSocket (`websockets/services.authenticate`) |
|---|---|---|
| Token row | `revoked = FALSE AND expires_at > CURRENT_TIMESTAMP()` | same |
| User row | `email_verified = TRUE AND disabled = FALSE` | `disabled = FALSE AND deleted = FALSE` |

So the WebSocket server accepts a token belonging to an unverified account, and the HTTP API accepts one belonging to an account flagged `deleted` but not `disabled`. In practice both flags are set together by the delete path, and a token can only be obtained via `/user/login`, which requires `email_verified = 1 AND disabled = 0`.

`authenticate_token` swallows every exception and returns `None`, so a database fault during authentication surfaces as `401`, not `500`.

Tokens are revoked by: `POST /user/login` (revokes all of that user's prior session tokens), `POST /user/logout`, `POST /user/logout-all`, `POST /user/change-password`, `POST /user/refresh-token` (the presented refresh token only), and account disable/delete via `POST /user/submit-profile`.

---

## Errors

All raised `APIError`s serialize identically:

```json
{ "status": "error", "message": "Human-readable description." }
```

| Status | Class | Default message |
|---|---|---|
| 400 | `BadRequest` | Bad request. |
| 401 | `Unauthorized` | Authentication required. |
| 403 | `Forbidden` | You do not have permission to perform this action. |
| 404 | `NotFound` | Resource not found. |
| 409 | `Conflict` | Conflict detected. |
| 422 | `UnprocessableEntity` | Unprocessable entity. |
| 429 | `TooManyRequests` | Too many requests. |
| 500 | `APIError` | A backend error occurred. |

Only `APIError` and its subclasses use this envelope — the app registers exactly one error handler, `@app.errorhandler(APIError)`. Everything else returns Werkzeug's **HTML** error page, including:

| Situation | Response |
|---|---|
| Unknown path | `404` HTML |
| Wrong method on a known path | `405` HTML, with an `Allow` header |
| Rate limit exceeded | `429` HTML, produced by Flask-Limiter |
| Unhandled Python exception | `500` HTML |

Services wrap their bodies in `except Exception: raise APIError()`, so most internal faults do surface as JSON `500`. Faults raised outside those blocks — notably a database error inside `insert_record`/`update_records` on a path with no wrapper — reach Werkzeug instead.

When `FLASK_ENV=dev`, [main.py](../src/backend/main.py) starts the server with `debug=True`, which replaces the `500` page with the **interactive Werkzeug debugger** (traceback plus a PIN-gated console). Production (`FLASK_ENV=prod`) serves via Waitress with the debugger off.

Error messages are not uniform in their leakage: `/user/login` deliberately returns the same string for a wrong password, an unverified account and a disabled account, while `/user/resend-verification` and `/user/reset-password-request` return `404 User not found.` for an unknown username and a different response for a known one.

---

## Rate limits

Configured in [extensions.py](../src/backend/app/extensions.py) as `Limiter(key_func=get_remote_address, storage_uri="memory://")`. Endpoints not listed are unlimited.

Properties that follow from that configuration:

- The key is `request.remote_addr`. No `ProxyFix` / `X-Forwarded-For` handling is installed, so behind a reverse proxy every client shares the proxy's IP as one bucket.
- Storage is per-process memory. Counters reset on restart, and are not shared across Waitress worker threads' parent processes if the service is ever scaled to multiple processes.
- No limit is applied to any `/chat/*` endpoint except archive/unarchive, and none to the WebSocket server at all.

| Limit | Endpoints |
|---|---|
| 1 / minute | `/user/resend-verification` |
| 5 / minute | `/user/register`, `/user/verify-email`, `/user/login`, `/user/reset-password-request`, `/user/reset-password`, `/user/change-password`, `/user/logout`, `/user/logout-all` |
| 10 / minute | `/user/refresh-token`, `/user/profile`, `/user/submit-profile`, `/chat/archive-chat`, `/chat/unarchive-chat` |

---

## HTTP API — base

### `GET /`

Renders the landing page (`templates/index.html`). Returns HTML.

### `GET|POST /verify-connection`

Health check. No authentication.

**200**
```json
{ "message": "Server is reachable!" }
```

### `GET|POST /subscribe`

Adds an email address to the newsletter list.

**Request** (POST)
```json
{ "email": "user@example.com" }
```

**200**
```json
{ "message": "Subscription successful." }
```

**Errors** — `400` Email is required. · `409` This email is already subscribed. · `500` Database error.

> `GET` runs the same logic with an empty body and therefore always returns `400`.

---

## HTTP API — user

All paths below are prefixed `/user`.

### `GET /user/`

Returns the plain string `User's index route`.

---

### `POST /user/register`

Creates an account and emails a 6-digit verification code (valid 5 minutes). **An invite code is required.**

**Request**
```json
{
  "username": "alice",
  "password": "Sup3rSecret!",
  "email": "alice@example.com",
  "invite_code": "ABC123"
}
```

Validation:
- `username` — required; may not contain any of `" % ' ( ) * + , / : ; < = > ? @ [ \ ] ^ { | } ~ ` ` or a space.
- `email` — required; must match `^[\w\.\+-]+@[\w-]+\.[\w\.-]+$`.
- `password` — required; ≥ 8 characters and must include an uppercase letter, a lowercase letter, a digit and a punctuation character.
- `invite_code` — required; must be non-revoked, unexpired and have `uses < max_uses`. One use is consumed atomically.

**201**
```json
{ "message": "Verification email sent!" }
```

When `FLASK_ENV=dev` **and** `IGNORE_EMAIL_VERIF=true`, the account is verified immediately and the response is `{ "message": "Email Verification skipped!" }`.

**Errors** — `400` Username and password are required. · `400` Username includes invalid characters. · `400` Email is required. · `400` Invalid email address. · `400` Password must be ≥8 chars, include upper, lower, digit & special. · `400` An invite code is required to register. · `400` Invalid or exhausted invite code. · `409` User '`<name>`' already exists. · `429` · `500`

Invite codes are minted out-of-band with [make_invite.py](../src/backend/make_invite.py).

---

### `POST /user/verify-email`

Consumes the verification code and marks the account verified.

**Request**
```json
{ "username": "alice", "email_token": "123456" }
```

**200**
```json
{ "message": "Email verified!" }
```

**Errors** — `400` Username and email_token are required. · `400` Invalid or expired code. · `429` · `500`

---

### `POST /user/resend-verification`

Revokes any outstanding codes and issues a new one.

**Request**
```json
{ "username": "alice" }
```

**200**
```json
{ "message": "Verification email resent!" }
```

**Errors** — `400` Username is required. · `400` Email is already verified. · `404` User not found. · `429` · `500`

---

### `POST /user/login`

Authenticates and issues a token pair. Revokes all of the user's existing session tokens first.

**Request**
```json
{ "username": "alice", "password": "Sup3rSecret!" }
```

**200**
```json
{
  "message": "Login successful",
  "access_token": "…",
  "refresh_token": "…"
}
```

**Errors** — `400` Username and password required. · `400` Username or password is incorrect. · `429` · `500`

> Unverified and disabled accounts are indistinguishable from wrong credentials: all return `400 Username or password is incorrect.`

---

### `POST /user/refresh-token`

Rotates a refresh token: the presented token is revoked and a new pair is issued.

**Request**
```json
{ "refresh_token": "…" }
```

**200**
```json
{
  "ok": true,
  "message": "Token refreshed",
  "access_token": "…",
  "refresh_token": "…"
}
```

**Errors** — `400` Refresh token required. · `401` Invalid refresh token. · `401` Refresh token expired or revoked. · `429` · `500`

---

### `POST /user/reset-password-request`

Generates a reset token (valid 1 hour) and emails a link to the address on file.

**Request**
```json
{ "username": "alice" }
```

**200**
```json
{ "message": "Password reset email sent!" }
```

**Errors** — `400` Username is required. · `404` User not found. · `429` · `500`

---

### `GET|POST /user/reset-password`

**`GET`** — renders the reset form. Requires query parameters `token` and `username`; returns HTML.

```
GET /user/reset-password?token=…&username=alice
```

Missing either parameter returns `400 Missing query parameters.`

**`POST`** — applies the new password. Accepts a JSON body **or** a form-encoded body (the HTML form posts the latter).

**Request**
```json
{
  "username": "alice",
  "token": "…",
  "password": "N3wSecret!",
  "confirm_password": "N3wSecret!"
}
```

**200**
```json
{ "message": "Password reset successfully" }
```

**Errors** — `400` Invalid request format. · `400` Username and token are required. · `400` New password and confirmation are required. · `400` Passwords do not match. · `400` Password must be ≥8 chars, include upper, lower, digit & special. · `400` Invalid or expired reset link. · `400` Username does not match. · `429` · `500`

---

### `POST /user/profile`

Returns the authenticated user's profile.

**Request**
```json
{ "session_token": "…" }
```

**200**
```json
{ "username": "alice", "email": "alice@example.com" }
```

**Errors** — `400` Session token is required. · `401` Invalid or expired session token. · `404` User not found. · `429` · `500`

---

### `POST /user/submit-profile`

Three mutually exclusive operations, resolved in this order: **delete** → **disable** → **update**.

**Request**
```json
{
  "session_token": "…",
  "username": "alice2",
  "email": "new@example.com",
  "disable": false,
  "delete": false
}
```

| Field | Effect |
|---|---|
| `delete: true` | Scrubs the user's messages to `[deleted]`, revokes every token, renames the account to `deleted_<userID>` and flags it `disabled` + `deleted`. Other fields ignored. |
| `disable: true` | Flags the account `disabled` and revokes session + refresh tokens. Reversible only out-of-band. |
| `username` / `email` | Updates whichever differs from the current value. Changing the email sets `email_verified = false` and sends a new 6-digit code to the new address. |

**200** — delete
```json
{ "disable": false, "delete": true, "message": "Account deleted." }
```

**200** — disable
```json
{ "disable": true, "delete": false, "message": "Account disabled." }
```

**200** — update
```json
{
  "username": "alice2",
  "email": "new@example.com",
  "verificationSent": true,
  "message": "Profile updated."
}
```

**Errors** — `400` Session token is required. · `400` No changes requested. · `401` Invalid or expired session token. · `404` User not found. · `429` · `500`

---

### `POST /user/change-password`

Changes the password and revokes **all** session and refresh tokens — the caller must log in again.

**Request**
```json
{
  "session_token": "…",
  "current_password": "Sup3rSecret!",
  "new_password": "N3wSecret!"
}
```

**200**
```json
{ "message": "Password changed successfully." }
```

**Errors** — `400` Session token is required. · `400` Old password is required. · `400` New password is required. · `400` New password cannot be the same as old password. · `400` Password must be ≥8 chars, include upper, lower, digit & special. · `401` Invalid or expired session token. · `403` Incorrect current password. · `404` User not found. · `429` · `500`

---

### `POST /user/logout`

Revokes the presented session token and the presented refresh token. Other sessions are unaffected.

**Request**
```json
{ "session_token": "…", "refresh_token": "…" }
```

**200**
```json
{ "message": "Logged out successfully." }
```

**Errors** — `400` Session token is required. · `400` Refresh token is required. · `401` Invalid or expired session token. · `404` User not found. · `429` · `500`

---

### `POST /user/logout-all`

Revokes every session and refresh token belonging to the user.

**Request**
```json
{ "session_token": "…" }
```

**200**
```json
{ "message": "Logged out from all sessions successfully." }
```

**Errors** — `400` Session token is required. · `401` Invalid or expired session token. · `404` User not found. · `429` · `500`

---

## HTTP API — chat

All paths below are prefixed `/chat` and require `session_token`. All are `POST`.

Common errors on every endpoint in this section: `400` Invalid JSON format. · `401` (invalid/expired token) · `500`.

### `GET /chat/`

Returns the plain string `chat's index route`.

---

### `POST /chat/fetch-chats`

Lists the caller's non-archived chats.

**Request**
```json
{ "session_token": "…" }
```

**200**
```json
{
  "response": [
    { "chatID": 1, "name": "bob",      "type": "private" },
    { "chatID": 7, "name": "Dev Team", "type": "group" }
  ]
}
```

For private chats `name` is the other participant's username, or `"Unknown"` if the peer row is missing. For groups it is `group_name`.

**Errors** — `400` Session token is required. · `401` Unable to verify user! · `404` User not found.

---

### `POST /chat/fetch-archived`

Same shape as `fetch-chats`, for chats the caller has archived.

**Request**
```json
{ "session_token": "…" }
```

**200**
```json
{ "response": [ { "chatID": 3, "type": "private", "name": "carol" } ] }
```

**Errors** — `400` Session token is required. · `401` Unable to verify user! · `404` User not found.

---

### `POST /chat/create-chat`

Opens a private chat with `receiver`. If one already exists it is reused and un-archived for both participants.

**Request**
```json
{ "session_token": "…", "receiver": "bob" }
```

**201**
```json
{ "chatID": 12 }
```

**Errors** — `400` Session token and receiver are required. · `400` Cannot chat with yourself. · `401` Unable to verify user! · `404` User not found.

---

### `POST /chat/create-group`

Creates a group chat. The caller is added as a participant automatically.

**Request**
```json
{ "session_token": "…", "name": "Dev Team", "members": ["bob", "carol"] }
```

`members` must be a non-empty list, and **every** listed username must exist — otherwise the whole call fails.

**201**
```json
{ "chatID": 13 }
```

**Errors** — `400` token, name and members list are required. · `401` Invalid session token. · `404` User not found. · `404` One or more members not found.

---

### `POST /chat/get-members`

Lists the usernames in a group chat. The caller must be a participant. Group chats only.

**Request**
```json
{ "session_token": "…", "chatID": 13 }
```

**200**
```json
{ "members": ["alice", "bob", "carol"] }
```

**Errors** — `400` session_token and chatID are required. · `401` Invalid session token. · `404` Group not found. · `404` Chat not found or access denied.

---

### `POST /chat/add-members`

Adds users to a group chat. The caller must be a participant. Already-present users are skipped silently.

**Request**
```json
{ "session_token": "…", "chatID": 13, "members": ["dave"] }
```

**200**
```json
{ "chatID": 13 }
```

**Errors** — `400` session_token, chatID and members list are required. · `401` Invalid session token. · `404` Chat not found or access denied. · `404` Group not found. · `404` One or more users not found.

---

### `POST /chat/remove-members`

Removes users from a group chat. The caller must be a participant; any participant may remove any other, including themselves.

**Request**
```json
{ "session_token": "…", "chatID": 13, "members": ["dave"] }
```

**200**
```json
{ "chatID": 13 }
```

**Errors** — same set as `add-members`.

---

### `POST /chat/messages`

Fetches message history for a chat, oldest-first.

**Request**
```json
{ "session_token": "…", "chatID": 13, "limit": 50 }
```

`limit` is optional, defaults to `50`, and must be an integer between 1 and 200. The `limit` most recent messages are selected, then returned in ascending timestamp order.

**200**
```json
{
  "messages": [
    {
      "messageID": 501,
      "userID": 4,
      "username": "bob",
      "message": "hey",
      "timestamp": "2026-08-11T20:14:02",
      "edited_at": null,
      "deleted_at": null
    }
  ]
}
```

Deleted messages are still returned, with `message` set to `--deleted--` and `deleted_at` populated. If the author's account no longer resolves, `username` is `"unknown"`.

**Errors** — `400` session_token and chatID are required. · `400` limit must be an integer. · `400` limit must be between 1 and 200. · `401` Unable to verify user! · `404` Chat not found or access denied.

---

### `POST /chat/archive-chat`

Archives the chat for the caller only. Rate limited 10/min.

**Request**
```json
{ "session_token": "…", "chatID": 13 }
```

**200**
```json
{ "message": "Chat archived" }
```

**Errors** — `400` Session token and chatID are required. · `401` Unable to verify user! · `404` User not found. · `429`

---

### `POST /chat/unarchive-chat`

Inverse of `archive-chat`. Rate limited 10/min.

**Request**
```json
{ "session_token": "…", "chatID": 13 }
```

**200**
```json
{ "message": "Chat unarchived" }
```

**Errors** — same set as `archive-chat`.

---

## WebSocket — `/ws`

`ws://<host>:8765/ws` — the main realtime channel: messaging, typing, presence and call signalling.

`CORSMiddleware` is installed with `allow_origins=["*"]`, but Starlette's CORS middleware only processes HTTP scopes; it does not apply to WebSocket handshakes. Neither WebSocket route inspects the `Origin` header, so there is no origin restriction on either. Credentials are not cookie-based — the token travels in the first frame — so a cross-origin page cannot authenticate implicitly.

### Handshake

The **first** frame after connecting must be an auth frame. Anything else closes the socket with code `1008`.

```json
{ "type": "auth", "token": "<access_token>" }
```

On success the server replies with two frames, in order:

```json
{ "type": "auth_ack", "status": "ok" }
{ "type": "online_users", "users": ["bob", "carol"] }
```

`users` lists currently-online users who share at least one chat with the caller. **The caller's own username is included** whenever they are in at least one chat: the self-exclusion filter compares `row["userID"]` (an `int`) against `username` (a `str`), which is never equal. The same filter is used when broadcasting `user_status`, so a user also receives their own presence events.

**Close codes**

| Code | Cause |
|---|---|
| `1008` | Malformed auth frame, or invalid/expired/revoked token |
| `1011` | Database error during authentication, or session valid but no active user |
| `1000` | A newer connection for the same username replaced this one |

Only one socket per username is kept. Connecting again closes the previous socket with `1000`.

On disconnect the server removes the socket from all subscriptions and broadcasts `user_status` with `online: false`.

### Client → server messages

Each frame must be a JSON object with a `type`. An unrecognised `type` — or a payload that doesn't match one of the shapes below — yields `{ "type": "error", "message": "Unknown action: <type>" }` or `{ "type": "error", "message": "Invalid message payload" }`.

| Message | Payload | Effect |
|---|---|---|
| `join_chat` | `{ "type": "join_chat", "chatID": 13 }` | Subscribes this socket to the chat's broadcasts. Requires participation. |
| `leave_chat` | `{ "type": "leave_chat", "chatID": 13 }` | Unsubscribes. |
| `join_idle` | `{ "type": "join_idle" }` | Adds the socket to the idle subscription set. |
| `post_msg` | `{ "type": "post_msg", "chatID": 13, "text": "hey" }` | Inserts a message and broadcasts `new_message`. `text` must be a string. Requires participation. |
| `edit_msg` | `{ "type": "edit_msg", "chatID": 13, "messageID": 501, "text": "hey!" }` | Updates the message and broadcasts `edited_message`. Author only. |
| `delete_msg` | `{ "type": "delete_msg", "chatID": 13, "messageID": 501 }` | Soft-deletes and broadcasts `deleted_message`. Author only. |
| `typing` | `{ "type": "typing", "chatID": 13 }` | Broadcasts `user_typing` to the chat, excluding the sender. |
| `chat_created` | `{ "type": "chat_created", "chatID": 12 }` | Notifies the other participants that a chat was created. |
| `call_invite` | `{ "type": "call_invite", "chatID": 13 }` | Starts a call. See [Calls](#calls). |
| `call_accept` | `{ "type": "call_accept", "chatID": 13, "call_id": "…" }` | Joins a ringing call. |
| `call_decline` | `{ "type": "call_decline", "chatID": 13 }` | Declines and tears down the pending call. |
| `call_end` | `{ "type": "call_end", "chatID": 13 }` | Ends the active call. |

### Server → client messages

| Message | Payload |
|---|---|
| `auth_ack` | `{ "type": "auth_ack", "status": "ok" }` |
| `online_users` | `{ "type": "online_users", "users": ["bob"] }` |
| `user_status` | `{ "type": "user_status", "username": "bob", "online": true }` |
| `new_message` | [Message payload](#message-payload) with `type: "new_message"` |
| `edited_message` | [Message payload](#message-payload) with `type: "edited_message"` |
| `deleted_message` | `{ "type": "deleted_message", "messageID": 501, "chatID": 13, "deleted_at": "2026-08-11T20:20:00" }` |
| `user_typing` | `{ "type": "user_typing", "username": "bob", "chatID": 13 }` |
| `chat_created` | `{ "type": "chat_created", "chatID": 12, "creator": "alice" }` |
| `error` | `{ "type": "error", "message": "…" }` |

`new_message`, `edited_message`, `deleted_message` and `user_typing` go to every socket subscribed to the chat via `join_chat`. `user_status` and `chat_created` go directly to the relevant users' active sockets, subscription or not.

#### Which actions reply to the sender

[handler.py](../src/backend/app/websockets/handler.py) only forwards a service's return value to the sender for **four** message types. For the rest the return value is assigned to a local variable and discarded, or the service returns `None`.

| Client message | Sender gets a direct reply? |
|---|---|
| `post_msg` | Yes — the payload, or an `error` |
| `chat_created` | Handler forwards it, but the service always returns `None`, so nothing is sent |
| `call_invite`, `call_accept` | Yes — the payload, or a `call_error` |
| `call_decline`, `call_end` | Service returns `None`. `call_end` separately sends a `call_error` directly when no call exists |
| `join_chat` | **No.** Its `error` returns are discarded |
| `edit_msg`, `delete_msg` | **No.** The payload is assigned but never sent |
| `leave_chat`, `typing`, `join_idle` | No return value by design |

The practical consequence: a rejected `join_chat`, `edit_msg` or `delete_msg` produces **no response frame at all**. A client cannot distinguish "denied" from "lost". Successful edits and deletes still reach the sender, but only via the chat broadcast, and therefore only if the sender has joined the chat.

#### Error payloads

Errors are delivered as `{ "type": "error", "message": "…" }`.

**Actually reachable by a client:**

| Message | Raised by |
|---|---|
| `Invalid message content.` | `post_msg` with a null `chatID` or unauthenticated socket |
| `User not found.` | `post_msg`, author row missing |
| `Access denied.` | `post_msg`, sender is not a participant |
| `Database error.` | `post_msg`, insert/select failure |
| `Unknown action: <type>` | Handler, `type` present but unmatched |
| `Invalid message payload` | Handler, frame is not an object with a `type` |
| `Internal server error.` | Handler, any non-`ValueError` exception |

**Present in the source but unreachable**, because the calling path discards the return value: `Unauthenticated.`, `Access denied for this chat.` (both `join_chat`); `Invalid request parameters.`, `Message not found.`, `Message is already deleted.`, `Unauthorized: You can only delete your own messages.`, `Database error during deletion.` (all `delete_msg`); `Message not found.`, `Unauthorized: You can only edit your own messages.` (the `edit_msg` path through `post_msg`).

Note that a frame such as `{"type": "post_msg", "chatID": 1, "text": 5}` fails the handler's `isinstance(text, str)` guard and falls through to the generic case, returning `Unknown action: post_msg` rather than a type error.

There is no `call_state` message. `services.emit_call_state()` builds one, but `join_chat` discards its return value, so it is never transmitted.

### Calls

Call control runs over `/ws`; the audio itself runs through LiveKit, whose URL and per-user JWT arrive in the `call_invite` / `call_accepted` payloads.

A call has one `call_id` (UUID) per chat at a time, and a state of `ringing` → `active` → ended (session discarded).

**`call_invite`** — broadcast to all online participants of the chat, and returned to the initiator:
```json
{
  "type": "call_invite",
  "chatID": 13,
  "call_id": "0f9c…",
  "caller": "alice",
  "lk_token": "<livekit jwt>",
  "lk_url": "ws://livekit-host:7880"
}
```

**`call_accepted`** — broadcast when someone joins; sets the session state to `active`:
```json
{
  "type": "call_accepted",
  "chatID": 13,
  "call_id": "0f9c…",
  "accepted_by": "bob",
  "lk_token": "<livekit jwt>",
  "lk_url": "ws://livekit-host:7880"
}
```

**`call_declined`**
```json
{ "type": "call_declined", "chatID": 13, "call_id": "0f9c…", "by": "bob", "initiator": "alice" }
```

**`call_ended`**
```json
{ "type": "call_ended", "chatID": 13, "call_id": "0f9c…", "ended_by": "alice", "initiator": "alice" }
```

**`call_error`** — sent to the requesting user only:
```json
{ "type": "call_error", "chatID": 13, "code": "ACCESS_DENIED", "message": "You are not a participant of this chat." }
```

| `code` | Meaning |
|---|---|
| `ACCESS_DENIED` | Caller is not a participant of the chat |
| `CALL_NOT_FOUND` | No pending call for this chat |
| `SESSION_NOT_FOUND` | `call_id` given but no matching session |

The LiveKit room name is the `chatID` as a string. The JWT grants `room_join` on that room with the user's username as identity. Tokens are minted with `LIVEKIT_KEY` / `LIVEKIT_SECRET`; `lk_url` echoes `LIVEKIT_URL`.

Call state is held in memory and is lost on server restart.

---

## WebSocket — `/call/{call_id}`

`ws://<host>:8765/call/<call_id>` — a signalling relay scoped to a single call.

Same auth handshake as `/ws`: the first frame must be `{ "type": "auth", "token": "<access_token>" }`. One socket per username; a new connection closes the previous one with `1000`.

The order of operations is: authenticate → **register the socket in `active_call_connections[username]`, closing any previous one** → look up the call → check participation → check state. Registration therefore happens before authorisation, so a connection that is about to be rejected has already displaced that user's existing call socket.

After auth the server validates the call, and on failure sends a rejection frame and closes with `1008`:

```json
{ "type": "call_ws_error", "call_id": "0f9c…", "code": "CALL_NOT_FOUND" }
```

| `code` | Meaning | Extra fields |
|---|---|---|
| `CALL_NOT_FOUND` | No session for this `call_id` | — |
| `ACCESS_DENIED` | User is not among the call's participants | — |
| `CALL_NOT_ACTIVE` | Session state is neither `ringing` nor `active` | `state` |

Once admitted, **every JSON frame received is relayed verbatim to the other sockets in the same call room** — the server does not inspect or validate the payload. There is no fixed schema for these frames.

When a socket disconnects, the remaining peers receive:

```json
{ "type": "leave" }
```

The room is discarded once the last socket leaves.

---

## Object shapes

### Chat summary

Returned by `/chat/fetch-chats` and `/chat/fetch-archived`.

```json
{ "chatID": 13, "name": "Dev Team", "type": "group" }
```

| Field | Type | Notes |
|---|---|---|
| `chatID` | int | |
| `name` | string | Peer username for `private`, `group_name` for `group` |
| `type` | string | `"private"` or `"group"` |

### Message

Returned by `/chat/messages`.

```json
{
  "messageID": 501,
  "userID": 4,
  "username": "bob",
  "message": "hey",
  "timestamp": "2026-08-11T20:14:02",
  "edited_at": null,
  "deleted_at": null
}
```

### Message payload

Broadcast over `/ws` for `new_message` and `edited_message`. Same fields as above plus `type` and `chatID`.

```json
{
  "type": "new_message",
  "messageID": 501,
  "chatID": 13,
  "userID": 4,
  "username": "bob",
  "message": "hey",
  "timestamp": "2026-08-11T20:14:02",
  "edited_at": null,
  "deleted_at": null
}
```

| Field | Type | Notes |
|---|---|---|
| `messageID` | int | |
| `chatID` | int | Broadcast payloads only |
| `userID` | int | Author |
| `username` | string | Author; `"unknown"` if unresolvable |
| `message` | string | `--deleted--` once soft-deleted, `[deleted]` if the author's account was deleted |
| `timestamp` | string | ISO 8601 |
| `edited_at` | string \| null | ISO 8601 |
| `deleted_at` | string \| null | ISO 8601 |

---

## Data model

From [install_update_server.py](../src/backend/install_update_server.py). All tables `utf8mb4` / `utf8mb4_unicode_ci`.

| Table | Key columns | Constraints that affect API behaviour |
|---|---|---|
| `users` | `userID` PK | `username VARCHAR(20) UNIQUE`, `password VARCHAR(128)`, `email VARCHAR(100)`, `email_verified`, `disabled`, `deleted`, `invite_code VARCHAR(64)` |
| `session_tokens` | `tokenID` PK | `session_token CHAR(64) UNIQUE` (SHA-256 hex), `expires_at NOT NULL`, `revoked`, `ip_address` — always written as `NULL` |
| `refresh_tokens` | `id` PK | `token CHAR(64) UNIQUE`, FK → `users.userID` |
| `email_tokens` | `tokenID` PK | `email_token CHAR(6)` |
| `pass_reset_tokens` | `tokenID` PK | `reset_token CHAR(64) UNIQUE` |
| `chats` | `chatID` PK | `type ENUM('private','group')`, `group_name VARCHAR(100)` |
| `participants` | PK `(chatID, userID)` | FKs to both parents; composite PK makes duplicate joins fail |
| `messages` | `messageID` PK | `message TEXT`; **no FK** to `chats` or `users` |
| `invite_codes` | `codeID` PK | `code VARCHAR(64) UNIQUE`, `max_uses`, `uses`, `revoked`, nullable `expires_at` |
| `email_subscribers` | `id` PK | `email VARCHAR(255) UNIQUE` |

Column widths are enforced only by MariaDB — the application validates none of them. `app/config.py` defines `VALID_TABLES`, a whitelist checked by the Flask DB helper; note it does **not** include `invite_codes`, which is reached through a raw cursor instead. The WebSocket DB helper has no equivalent whitelist.

All user-supplied values reach the database through parameter binding. The dynamic fragments that are string-interpolated (`IN (...)` lists, `ORDER BY`, `LIMIT`) are built from placeholder counts and hardcoded literals, not from request data.

---

## Behavioural notes

Observable behaviours that are not obvious from the endpoint descriptions.

**Validation gaps that surface as `500` rather than `4xx`**

- `POST /user/register` does not length-check `username` against the 20-character column. A longer value fails at insert and returns `500`. The invite code is consumed and committed *before* that insert, so a registration that fails this way still spends one use of the code.
- `POST /user/submit-profile` applies **no** validation to a new `username` or `email` — no character-set check, no length check, no format check, no uniqueness check, despite `/user/register` enforcing all four. A rename collides with `username UNIQUE` and returns `500`.
- Passing the same username twice in a `members` array (`["bob","bob"]`) makes `len(rows) != len(members)`, returning `404 One or more members not found.` This affects `/chat/create-group`, `/chat/add-members` and `/chat/remove-members`.

**Ordering**

- `/chat/messages` validates `limit` before authenticating, so `limit` errors are reachable without a valid token.
- `/user/register` checks username availability before consuming the invite code.

**Type handling**

- `chatID` and `messageID` are passed through from JSON without coercion. MariaDB coerces them at query time, but `chat_subscriptions` is an in-memory dict keyed by the raw value, so joining with `"13"` and posting with `13` produce different keys and the broadcast will not reach the subscriber.

**Authorisation coverage**

- `/chat/archive-chat` and `/chat/unarchive-chat` perform no participation check, but their `UPDATE` is scoped to the caller's own `participants` row, so a non-participant's call affects nothing.
- `/chat/remove-members` allows any participant to remove any other participant, including the group creator. There is no owner or admin role anywhere in the schema.
- The `edit_msg` path verifies message ownership and that the message belongs to the claimed chat, but does not re-check that the editor is still a participant of that chat.

**State durability**

- All WebSocket state — `active_connections`, `chat_subscriptions`, `pending_calls`, `call_sessions`, `user_status` — is per-process memory, reset by `services.reset_variables()` at startup. Restarting the WebSocket server drops all presence and call state while HTTP sessions remain valid.
- Expired and revoked token rows are never purged; see [FOLLOWUPS.md](../FOLLOWUPS.md).

**LiveKit**

- The room name is the `chatID` as a string, and the JWT grants `room_join` on that room. A token minted for one call remains valid for that room for its lifetime, independent of the `call_sessions` state the WebSocket server tracks.
