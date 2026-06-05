from __future__ import annotations

import secrets

SESSION_COOKIE = "confdex_session"
_sessions: set[str] = set()


def create() -> str:
    token = secrets.token_urlsafe(32)
    _sessions.add(token)
    return token


def valid(token: str) -> bool:
    return bool(token) and token in _sessions


def revoke(token: str) -> None:
    _sessions.discard(token)
