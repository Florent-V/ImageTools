"""Server-side sessions in SQLite (WAL), shared by every uvicorn worker.

The cookie only holds a random session id; the database only holds its
SHA-256. sqlite3 is blocking: every public method runs in a worker thread.
"""

import hashlib
import json
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anyio import to_thread

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id_hash TEXT PRIMARY KEY,
    sub TEXT NOT NULL,
    oauth_sid TEXT,
    user_claims TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    access_expires_at INTEGER,
    created_at INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL,
    last_revalidated_at INTEGER NOT NULL,
    absolute_expires_at INTEGER NOT NULL,
    -- Revalidation lease: one worker refreshes, the others don't wait on a DB lock
    revalidating_until INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sessions_sub ON sessions(sub);
CREATE INDEX IF NOT EXISTS sessions_oauth_sid ON sessions(oauth_sid);
CREATE TABLE IF NOT EXISTS login_attempts (
    state TEXT PRIMARY KEY,
    code_verifier TEXT NOT NULL,
    nonce TEXT,
    return_to TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS seen_jti (
    jti TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL
);
"""


def hash_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


def now() -> int:
    return int(time.time())


@dataclass
class Session:
    id_hash: str
    sub: str
    oauth_sid: str | None
    user: dict[str, Any]
    access_token: str | None
    refresh_token: str | None
    access_expires_at: int | None
    created_at: int
    last_seen_at: int
    last_revalidated_at: int
    absolute_expires_at: int


@dataclass
class LoginAttempt:
    code_verifier: str
    nonce: str | None
    return_to: str


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        # Autocommit mode: transactions are explicit (BEGIN IMMEDIATE)
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _run(self, fn, *args):
        conn = self._connect()
        try:
            return fn(conn, *args)
        finally:
            conn.close()

    async def _call(self, fn, *args):
        return await to_thread.run_sync(self._run, fn, *args)

    # ── setup / maintenance ─────────────────────────────────────────────

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        def create(conn):
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)

        self._run(create)
        self.path.chmod(0o600)

    async def purge(self) -> None:
        def purge(conn, ts):
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM sessions WHERE absolute_expires_at <= ?", (ts,))
            conn.execute("DELETE FROM login_attempts WHERE expires_at <= ?", (ts,))
            conn.execute("DELETE FROM seen_jti WHERE expires_at <= ?", (ts,))
            conn.execute("COMMIT")

        await self._call(purge, now())

    async def purge_idle(self, idle_ttl_s: int) -> None:
        await self._call(
            lambda conn, ts: conn.execute("DELETE FROM sessions WHERE last_seen_at <= ?", (ts,)),
            now() - idle_ttl_s,
        )

    # ── login attempts ──────────────────────────────────────────────────

    async def add_login_attempt(self, state: str, code_verifier: str, nonce: str | None, return_to: str, ttl_s: int) -> None:
        await self._call(
            lambda conn: conn.execute(
                "INSERT INTO login_attempts (state, code_verifier, nonce, return_to, expires_at) VALUES (?, ?, ?, ?, ?)",
                (state, code_verifier, nonce, return_to, now() + ttl_s),
            )
        )

    async def consume_login_attempt(self, state: str) -> LoginAttempt | None:
        """Single use, atomic: the row is deleted whatever happens next."""

        def consume(conn):
            row = conn.execute(
                "DELETE FROM login_attempts WHERE state = ? RETURNING code_verifier, nonce, return_to, expires_at",
                (state,),
            ).fetchone()
            if row is None or row["expires_at"] <= now():
                return None
            return LoginAttempt(row["code_verifier"], row["nonce"], row["return_to"])

        return await self._call(consume)

    # ── sessions ────────────────────────────────────────────────────────

    async def create_session(self, sub: str, oauth_sid: str | None, user: dict[str, Any], token: dict[str, Any], absolute_ttl_s: int) -> str:
        """Returns the raw session id (for the cookie only, never stored)."""
        session_id = secrets.token_urlsafe(32)
        ts = now()
        await self._call(
            lambda conn: conn.execute(
                "INSERT INTO sessions (id_hash, sub, oauth_sid, user_claims, access_token, refresh_token, access_expires_at,"
                " created_at, last_seen_at, last_revalidated_at, absolute_expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    hash_id(session_id), sub, oauth_sid, json.dumps(user), token.get("access_token"),
                    token.get("refresh_token"), _expires_at(token), ts, ts, ts, ts + absolute_ttl_s,
                ),
            )
        )
        return session_id

    async def get_session(self, session_id: str) -> Session | None:
        row = await self._call(
            lambda conn: conn.execute("SELECT * FROM sessions WHERE id_hash = ?", (hash_id(session_id),)).fetchone()
        )
        return _session(row) if row else None

    async def touch(self, id_hash: str) -> None:
        await self._call(lambda conn: conn.execute("UPDATE sessions SET last_seen_at = ? WHERE id_hash = ?", (now(), id_hash)))

    async def delete_session(self, id_hash: str) -> Session | None:
        row = await self._call(
            lambda conn: conn.execute("DELETE FROM sessions WHERE id_hash = ? RETURNING *", (id_hash,)).fetchone()
        )
        return _session(row) if row else None

    async def delete_by_sid(self, oauth_sid: str) -> int:
        return await self._call(lambda conn: conn.execute("DELETE FROM sessions WHERE oauth_sid = ?", (oauth_sid,)).rowcount)

    async def delete_by_sub(self, sub: str) -> int:
        return await self._call(lambda conn: conn.execute("DELETE FROM sessions WHERE sub = ?", (sub,)).rowcount)

    async def claim_revalidation(self, id_hash: str, interval_s: int, lease_s: int) -> bool:
        """True if this caller must refresh. Atomic across workers: still due
        (not done meanwhile) and nobody else holding the lease."""

        def claim(conn, ts):
            return conn.execute(
                "UPDATE sessions SET revalidating_until = ? WHERE id_hash = ?"
                " AND last_revalidated_at <= ? AND revalidating_until <= ?",
                (ts + lease_s, id_hash, ts - interval_s, ts),
            ).rowcount == 1

        return await self._call(claim, now())

    async def release_revalidation(self, id_hash: str) -> None:
        await self._call(lambda conn: conn.execute("UPDATE sessions SET revalidating_until = 0 WHERE id_hash = ?", (id_hash,)))

    async def save_tokens(self, id_hash: str, token: dict[str, Any], previous_refresh_token: str | None) -> None:
        await self._call(
            lambda conn, ts: conn.execute(
                "UPDATE sessions SET access_token = ?, refresh_token = ?, access_expires_at = ?,"
                " last_revalidated_at = ?, revalidating_until = 0 WHERE id_hash = ?",
                (
                    token.get("access_token"), token.get("refresh_token") or previous_refresh_token,
                    _expires_at(token), ts, id_hash,
                ),
            ),
            now(),
        )

    # ── back-channel logout replay protection ───────────────────────────

    async def remember_jti(self, jti: str, expires_at: int) -> bool:
        """False if this jti was already seen."""
        return await self._call(
            lambda conn: conn.execute(
                "INSERT OR IGNORE INTO seen_jti (jti, expires_at) VALUES (?, ?)", (jti, expires_at)
            ).rowcount == 1
        )


def _expires_at(token: dict[str, Any]) -> int | None:
    if token.get("expires_at"):
        return int(token["expires_at"])
    if token.get("expires_in"):
        return now() + int(token["expires_in"])
    return None


def _session(row: sqlite3.Row) -> Session:
    return Session(
        id_hash=row["id_hash"],
        sub=row["sub"],
        oauth_sid=row["oauth_sid"],
        user=json.loads(row["user_claims"]),
        access_token=row["access_token"],
        refresh_token=row["refresh_token"],
        access_expires_at=row["access_expires_at"],
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
        last_revalidated_at=row["last_revalidated_at"],
        absolute_expires_at=row["absolute_expires_at"],
    )
