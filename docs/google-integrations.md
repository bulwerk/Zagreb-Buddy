# Google integrations (Maps + Calendar)

This backend now supports connecting a user to Google, generating Google Maps route links from itinerary places, and creating/updating Google Calendar events.

## Environment variables (backend)

Set these in `agent/.env` (or deployment env):

```env
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_OAUTH_REDIRECT_URI=https://your-frontend-domain/google/callback
# Optional override:
# GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/calendar.events
```

## API requirements

- All Google integration endpoints require request header:
  - `X-User-ID: <your-app-user-id>`
- Tokens are stored in SQLite table: `google_integrations`.

## Endpoints

### 1) Start OAuth connect

`GET /integrations/google/connect`

Response:

```json
{
  "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

Use this URL in frontend to redirect user to Google consent.

### 1b) Check connection status

`GET /integrations/google/status`

Response:

```json
{
  "connected": true,
  "google_email": null
}
```

### 2) Complete OAuth (exchange auth code)

`POST /integrations/google/callback`

Body:

```json
{
  "code": "<authorization code from Google redirect>"
}
```

Response:

```json
{
  "connected": true,
  "scope": "...",
  "expires_in": 3599
}
```

### 3) Build Google Maps walking route from suggested places

`POST /integrations/google/maps/route`

Body:

```json
{
  "places": [
    {
      "id": "a",
      "name": "Spot A",
      "lat": 45.81,
      "lng": 15.98,
      "one_liner": "...",
      "why_recommended": "...",
      "practical_tip": "...",
      "visit_duration_min": 20,
      "category": "cafe"
    },
    {
      "id": "b",
      "name": "Spot B",
      "lat": 45.82,
      "lng": 15.99,
      "one_liner": "...",
      "why_recommended": "...",
      "practical_tip": "...",
      "visit_duration_min": 20,
      "category": "bar"
    }
  ]
}
```

Response:

```json
{
  "maps_directions_url": "https://www.google.com/maps/dir/?api=1&..."
}
```

### 4) Create calendar event

`POST /integrations/google/calendar/events`

Body:

```json
{
  "title": "Zagreb evening route",
  "description": "Suggested by Zagreb Buddy",
  "start_iso": "2026-04-10T17:00:00+02:00",
  "end_iso": "2026-04-10T20:00:00+02:00",
  "timezone_name": "Europe/Zagreb",
  "location": "Zagreb city center"
}
```

Response:

```json
{
  "id": "google-event-id",
  "html_link": "https://www.google.com/calendar/event?eid=...",
  "status": "confirmed"
}
```

### 5) Update calendar event

`PATCH /integrations/google/calendar/events`

Body:

```json
{
  "event_id": "google-event-id",
  "title": "Updated title",
  "start_iso": "2026-04-10T18:00:00+02:00",
  "end_iso": "2026-04-10T21:00:00+02:00"
}
```

Response shape is same as create endpoint.

## Recommended frontend flow

1. User clicks “Connect Google”.
2. Frontend calls `GET /integrations/google/connect` and redirects to returned URL.
3. Google redirects back to frontend route `/google/callback` with `code`.
4. Frontend posts `code` to backend callback endpoint.
5. When itinerary exists, frontend calls maps route endpoint and shows “Open in Google Maps”.
6. User confirms plan -> frontend calls create calendar event endpoint.
7. User edits plan -> frontend calls update calendar event endpoint.

