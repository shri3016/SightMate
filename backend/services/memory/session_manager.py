"""SessionManager — cached screen understanding + conversation memory.

Holds, per session_id, the latest ScreenUnderstanding and the message history.
This is what makes SightMate a real conversational assistant: analyze the
screen once, answer many follow-ups from the cached understanding + history.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from ...core.interfaces import Message
from ...db import Database
from ...schemas import ScreenUnderstanding


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionManager:
    def __init__(self, db: Database):
        self._db = db

    def create_session(self) -> str:
        session_id = uuid.uuid4().hex
        ts = _now()
        with self._db.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
                (session_id, ts, ts),
            )
        return session_id

    def ensure_session(self, session_id: str | None) -> str:
        """Return a valid session id, creating one if needed."""
        if session_id and self._exists(session_id):
            return session_id
        return self.create_session()

    def save_understanding(self, session_id: str, understanding: ScreenUnderstanding) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE sessions SET page_type = ?, last_understanding = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    understanding.page_type,
                    json.dumps(understanding.to_dict(), ensure_ascii=False),
                    _now(),
                    session_id,
                ),
            )

    def get_understanding(self, session_id: str) -> ScreenUnderstanding | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT last_understanding FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if not row or not row["last_understanding"]:
            return None
        return ScreenUnderstanding.from_dict(json.loads(row["last_understanding"]))

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, role, content, _now()),
            )

    def get_history(self, session_id: str) -> list[Message]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def _exists(self, session_id: str) -> bool:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return row is not None
