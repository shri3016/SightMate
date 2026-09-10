"""SQLite storage.

Two tables:
- sessions: one row per screen-sharing session; caches the latest
  ScreenUnderstanding so follow-up questions need no re-analysis.
- messages: conversation history (the "what was the price?" memory).

Privacy: raw screenshots are never stored — only the derived understanding.

A fresh connection is opened per operation, which keeps the store safe across
Flask's worker threads without a shared-connection lock.
"""
from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id                 TEXT PRIMARY KEY,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    page_type          TEXT,
    last_understanding TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


class Database:
    def __init__(self, path: str):
        self._path = path
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
