from __future__ import annotations

import os
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from storage import StorageRepository

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


@dataclass
class GoogleConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str]


class GoogleIntegrationService:
    def __init__(self, repository: StorageRepository):
        self.repository = repository

    @staticmethod
    def load_config() -> GoogleConfig:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

        if not client_id or not client_secret or not redirect_uri:
            raise RuntimeError(
                "Missing Google OAuth config. Set GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_OAUTH_REDIRECT_URI."
            )

        scopes_env = os.getenv("GOOGLE_OAUTH_SCOPES")
        scopes = (
            [scope.strip() for scope in scopes_env.split(",") if scope.strip()]
            if scopes_env
            else DEFAULT_SCOPES
        )
        return GoogleConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
        )

    def build_authorize_url(self, *, user_id: str, state: str | None = None) -> str:
        cfg = self.load_config()
        query = {
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "response_type": "code",
            "scope": " ".join(cfg.scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state or user_id,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(query)}"

    def exchange_code_for_tokens(self, *, user_id: str, code: str) -> dict[str, Any]:
        cfg = self.load_config()
        form_body = urllib.parse.urlencode(
            {
                "code": code,
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "redirect_uri": cfg.redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            GOOGLE_TOKEN_URL,
            data=form_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        expiry_iso = None
        expires_in = payload.get("expires_in")
        if expires_in:
            expiry_iso = (datetime.now(timezone.utc).timestamp() + int(expires_in))
            expiry_iso = datetime.fromtimestamp(expiry_iso, tz=timezone.utc).isoformat()

        self.repository.ensure_user(
            user_id=user_id,
            email=f"google+{user_id}@local.zagrebbuddy",
            display_name="Google Connected User",
        )
        self.repository.upsert_google_integration(
            user_id=user_id,
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            token_uri=GOOGLE_TOKEN_URL,
            scopes=cfg.scopes,
            expiry=expiry_iso,
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
        )
        return payload

    def _credentials_for_user(self, user_id: str) -> Credentials:
        integration = self.repository.get_google_integration(user_id)
        if not integration:
            raise ValueError("Google integration not connected for this user")

        expiry = None
        if integration.get("expiry"):
            expiry = datetime.fromisoformat(integration["expiry"])

        credentials = Credentials(
            token=integration["access_token"],
            refresh_token=integration.get("refresh_token"),
            token_uri=integration.get("token_uri") or GOOGLE_TOKEN_URL,
            client_id=integration.get("client_id") or os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=integration.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=integration.get("scopes") or DEFAULT_SCOPES,
            expiry=expiry,
        )

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.repository.upsert_google_integration(
                user_id=user_id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri or GOOGLE_TOKEN_URL,
                scopes=list(credentials.scopes or DEFAULT_SCOPES),
                expiry=credentials.expiry.isoformat() if credentials.expiry else None,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
            )

        return credentials

    @staticmethod
    def build_google_maps_directions_url(places: list[dict[str, Any]]) -> str | None:
        if len(places) < 2:
            return None

        origin = f"{places[0]['lat']},{places[0]['lng']}"
        destination = f"{places[-1]['lat']},{places[-1]['lng']}"
        waypoints = [f"{p['lat']},{p['lng']}" for p in places[1:-1]]
        params = {
            "api": "1",
            "travelmode": "walking",
            "origin": origin,
            "destination": destination,
        }
        if waypoints:
            params["waypoints"] = "|".join(waypoints)
        return f"https://www.google.com/maps/dir/?{urllib.parse.urlencode(params)}"

    def create_calendar_event(
        self,
        *,
        user_id: str,
        title: str,
        description: str | None,
        start_iso: str,
        end_iso: str,
        timezone_name: str = "Europe/Zagreb",
        location: str | None = None,
    ) -> dict[str, Any]:
        credentials = self._credentials_for_user(user_id)
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        event_body: dict[str, Any] = {
            "summary": title,
            "description": description or "",
            "start": {"dateTime": start_iso, "timeZone": timezone_name},
            "end": {"dateTime": end_iso, "timeZone": timezone_name},
        }
        if location:
            event_body["location"] = location

        created = (
            service.events()
            .insert(calendarId="primary", body=event_body)
            .execute()
        )
        return created

    def update_calendar_event(
        self,
        *,
        user_id: str,
        event_id: str,
        title: str | None = None,
        description: str | None = None,
        start_iso: str | None = None,
        end_iso: str | None = None,
        timezone_name: str = "Europe/Zagreb",
        location: str | None = None,
    ) -> dict[str, Any]:
        credentials = self._credentials_for_user(user_id)
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        if title is not None:
            event["summary"] = title
        if description is not None:
            event["description"] = description
        if start_iso is not None:
            event["start"] = {"dateTime": start_iso, "timeZone": timezone_name}
        if end_iso is not None:
            event["end"] = {"dateTime": end_iso, "timeZone": timezone_name}
        if location is not None:
            event["location"] = location

        updated = (
            service.events()
            .update(calendarId="primary", eventId=event_id, body=event)
            .execute()
        )
        return updated
