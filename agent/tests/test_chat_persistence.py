from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeChat:
    def send_message(self, _message: str) -> _FakeResponse:
        return _FakeResponse(
            '{"message":"Fake assistant reply","itinerary":null,"follow_ups":[],"active_skills_used":[],"needs_more_info":false}'
        )


class _FakeModel:
    def __init__(self, _model_name: str) -> None:
        pass

    def start_chat(self, history: list[dict] | None = None) -> _FakeChat:
        return _FakeChat()


@pytest.fixture()
def client_and_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, Path]:
    agent_dir = Path(__file__).resolve().parent.parent
    monkeypatch.chdir(agent_dir)

    db_path = tmp_path / "test_zagreb_buddy.db"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("ZAGREB_BUDDY_DB_PATH", str(db_path))

    import google.generativeai as genai

    monkeypatch.setattr(genai, "configure", lambda **_kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", _FakeModel)

    # Re-import app module for a fresh repository/agent per test.
    if "main" in sys.modules:
        del sys.modules["main"]
    main_module = importlib.import_module("main")
    return TestClient(main_module.app), db_path


def test_chat_persists_messages_and_history(client_and_db: tuple[TestClient, Path]) -> None:
    client, _db_path = client_and_db
    session_id = "test-session-1"

    first = client.post("/chat", json={"message": "Bok!", "conversation_id": session_id})
    assert first.status_code == 200, first.text
    assert first.json()["conversation_id"] == session_id

    second = client.post(
        "/chat",
        json={"message": "Any coffee spots?", "conversation_id": session_id},
    )
    assert second.status_code == 200, second.text

    history = client.get(f"/chat/{session_id}/history")
    assert history.status_code == 200, history.text
    payload = history.json()

    assert len(payload) == 4
    assert payload[0]["role"] == "user"
    assert payload[1]["role"] == "assistant"
    assert payload[-1]["role"] == "assistant"


def test_chat_history_limit_validation(client_and_db: tuple[TestClient, Path]) -> None:
    client, _db_path = client_and_db
    bad = client.get("/chat/anything/history?limit=0")
    assert bad.status_code == 400
    assert "between 1 and 500" in bad.json()["detail"]


def test_chat_writes_to_database(client_and_db: tuple[TestClient, Path]) -> None:
    client, db_path = client_and_db
    session_id = "db-check-session"

    response = client.post(
        "/chat",
        json={"message": "Hello from DB test", "conversation_id": session_id},
    )
    assert response.status_code == 200, response.text

    conn = sqlite3.connect(db_path)
    try:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        sessions_count = conn.execute(
            "SELECT COUNT(*) FROM chat_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()[0]
        messages_count = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert users_count == 1
    assert sessions_count == 1
    assert messages_count == 2


def test_google_maps_route_requires_header(client_and_db: tuple[TestClient, Path]) -> None:
    client, _db_path = client_and_db
    response = client.post(
        "/integrations/google/maps/route",
        json={
            "places": [
                {
                    "id": "a",
                    "name": "Start",
                    "lat": 45.81,
                    "lng": 15.98,
                    "one_liner": "start",
                    "why_recommended": "test",
                    "practical_tip": "test",
                    "visit_duration_min": 20,
                    "category": "cafe",
                },
                {
                    "id": "b",
                    "name": "End",
                    "lat": 45.82,
                    "lng": 15.99,
                    "one_liner": "end",
                    "why_recommended": "test",
                    "practical_tip": "test",
                    "visit_duration_min": 20,
                    "category": "bar",
                },
            ]
        },
    )
    assert response.status_code == 400
    assert "X-User-ID" in response.json()["detail"]


def test_google_maps_route_builds_directions_url(client_and_db: tuple[TestClient, Path]) -> None:
    client, _db_path = client_and_db
    response = client.post(
        "/integrations/google/maps/route",
        headers={"X-User-ID": "user-1"},
        json={
            "places": [
                {
                    "id": "a",
                    "name": "Start",
                    "lat": 45.8100,
                    "lng": 15.9800,
                    "one_liner": "start",
                    "why_recommended": "test",
                    "practical_tip": "test",
                    "visit_duration_min": 20,
                    "category": "cafe",
                },
                {
                    "id": "mid",
                    "name": "Mid",
                    "lat": 45.8150,
                    "lng": 15.9850,
                    "one_liner": "mid",
                    "why_recommended": "test",
                    "practical_tip": "test",
                    "visit_duration_min": 20,
                    "category": "market",
                },
                {
                    "id": "b",
                    "name": "End",
                    "lat": 45.8200,
                    "lng": 15.9900,
                    "one_liner": "end",
                    "why_recommended": "test",
                    "practical_tip": "test",
                    "visit_duration_min": 20,
                    "category": "bar",
                },
            ]
        },
    )
    assert response.status_code == 200, response.text
    url = response.json()["maps_directions_url"]
    assert "google.com/maps/dir" in url
    assert "origin=" in url
    assert "destination=" in url
