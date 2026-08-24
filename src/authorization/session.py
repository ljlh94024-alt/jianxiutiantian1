"""Short-lived, one-time authorization sessions."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class AuthorizationSession:
    session_id: str
    target_id: str
    task_id: str
    expires_at: datetime
    consumed: bool = False

    def is_valid(self, target_id: str, task_id: str) -> bool:
        return (
            not self.consumed
            and datetime.now(timezone.utc) < self.expires_at
            and self.target_id == target_id
            and self.task_id == task_id
        )


class SessionStore:
    def __init__(self, lifetime_minutes: int = 10):
        if lifetime_minutes <= 0:
            raise ValueError("Session lifetime must be positive")
        self.lifetime = timedelta(minutes=lifetime_minutes)
        self._sessions: dict[str, AuthorizationSession] = {}

    def create(self, target_id: str, task_id: str) -> AuthorizationSession:
        session = AuthorizationSession(
            secrets.token_urlsafe(24), target_id, task_id, datetime.now(timezone.utc) + self.lifetime
        )
        self._sessions[session.session_id] = session
        return session

    def consume(self, session_id: str, target_id: str, task_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or not session.is_valid(target_id, task_id):
            return False
        session.consumed = True
        return True

