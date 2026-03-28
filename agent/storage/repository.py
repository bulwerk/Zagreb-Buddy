from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any


class StorageRepository:
    """Minimal persistence layer for MVP account, chat, and contribution data."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        default_db_path = Path(__file__).resolve().parents[1] / "data" / "zagreb_buddy.db"
        self.db_path = Path(db_path) if db_path else default_db_path
        self.schema_path = Path(__file__).with_name("schema.sql")
        self._ensure_parent_dir()
        self.initialize()

    def _ensure_parent_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self) -> None:
        schema = self.schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema)

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        home_city: str = "zagreb",
        user_id: str | None = None,
    ) -> str:
        user_id = user_id or str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, home_city)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, email, display_name, password_hash, home_city),
            )
        return user_id

    def ensure_user(
        self,
        *,
        user_id: str,
        email: str,
        display_name: str,
        password_hash: str = "!",
        home_city: str = "zagreb",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, home_city)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (user_id, email, display_name, password_hash, home_city),
            )

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_chat_session(
        self,
        *,
        user_id: str,
        title: str | None = None,
        city_slug: str = "zagreb",
        session_id: str | None = None,
    ) -> str:
        session_id = session_id or str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, user_id, title, city_slug)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, title, city_slug),
            )
        return session_id

    def get_chat_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def ensure_chat_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str | None = None,
        city_slug: str = "zagreb",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, user_id, title, city_slug)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (session_id, user_id, title, city_slug),
            )

    def list_user_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_chat_message(self, *, session_id: str, role: str, content: str) -> str:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("role must be one of: user, assistant, system")

        message_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content)
                VALUES (?, ?, ?, ?)
                """,
                (message_id, session_id, role, content),
            )
            conn.execute(
                """
                UPDATE chat_sessions
                SET updated_at = datetime('now')
                WHERE id = ?
                """,
                (session_id,),
            )
        return message_id

    def list_chat_messages(
        self,
        *,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_user_preferences(
        self,
        *,
        user_id: str,
        preferred_vibes: list[str] | None = None,
        preferred_skills: list[str] | None = None,
        dislikes: list[str] | None = None,
    ) -> None:
        vibes_json = json.dumps(preferred_vibes or [])
        skills_json = json.dumps(preferred_skills or [])
        dislikes_json = json.dumps(dislikes or [])

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (
                    user_id,
                    preferred_vibes_json,
                    preferred_skills_json,
                    dislikes_json,
                    updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                    preferred_vibes_json = excluded.preferred_vibes_json,
                    preferred_skills_json = excluded.preferred_skills_json,
                    dislikes_json = excluded.dislikes_json,
                    updated_at = datetime('now')
                """,
                (user_id, vibes_json, skills_json, dislikes_json),
            )

    def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT preferred_vibes_json, preferred_skills_json, dislikes_json, updated_at
                FROM user_preferences
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if not row:
            return {
                "preferred_vibes": [],
                "preferred_skills": [],
                "dislikes": [],
                "updated_at": None,
            }

        return {
            "preferred_vibes": json.loads(row["preferred_vibes_json"] or "[]"),
            "preferred_skills": json.loads(row["preferred_skills_json"] or "[]"),
            "dislikes": json.loads(row["dislikes_json"] or "[]"),
            "updated_at": row["updated_at"],
        }

    def submit_contribution(
        self,
        *,
        user_id: str,
        contribution_type: str,
        city_slug: str,
        payload: dict[str, Any],
        target_slug: str | None = None,
    ) -> str:
        if contribution_type not in {"city", "skill", "place"}:
            raise ValueError("contribution_type must be one of: city, skill, place")

        contribution_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO contributions (
                    id,
                    user_id,
                    contribution_type,
                    city_slug,
                    target_slug,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    contribution_id,
                    user_id,
                    contribution_type,
                    city_slug,
                    target_slug,
                    json.dumps(payload),
                ),
            )
        return contribution_id

    def list_contributions(
        self,
        *,
        status: str | None = None,
        city_slug: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM contributions WHERE 1=1"
        params: list[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if city_slug:
            query += " AND city_slug = ?"
            params.append(city_slug)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        contributions = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            contributions.append(item)
        return contributions

    def update_contribution_status(
        self,
        *,
        contribution_id: str,
        status: str,
        reviewer_note: str | None = None,
    ) -> None:
        if status not in {"submitted", "in_review", "approved", "rejected"}:
            raise ValueError("status must be one of: submitted, in_review, approved, rejected")

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE contributions
                SET status = ?, reviewer_note = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (status, reviewer_note, contribution_id),
            )

    def upsert_google_integration(
        self,
        *,
        user_id: str,
        access_token: str,
        refresh_token: str | None,
        token_uri: str,
        scopes: list[str],
        expiry: str | None = None,
        google_email: str | None = None,
        client_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO google_integrations (
                    user_id,
                    google_email,
                    access_token,
                    refresh_token,
                    token_uri,
                    client_id,
                    scopes_json,
                    expiry,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                    google_email = excluded.google_email,
                    access_token = excluded.access_token,
                    refresh_token = COALESCE(excluded.refresh_token, google_integrations.refresh_token),
                    token_uri = excluded.token_uri,
                    client_id = excluded.client_id,
                    scopes_json = excluded.scopes_json,
                    expiry = excluded.expiry,
                    updated_at = datetime('now')
                """,
                (
                    user_id,
                    google_email,
                    access_token,
                    refresh_token,
                    token_uri,
                    client_id,
                    json.dumps(scopes),
                    expiry,
                ),
            )

    def get_google_integration(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM google_integrations WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if not row:
            return None

        payload = dict(row)
        payload["scopes"] = json.loads(payload.pop("scopes_json") or "[]")
        return payload
