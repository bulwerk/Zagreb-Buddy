import logging
import os
import uuid

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google_integration import GoogleIntegrationService
from storage import StorageRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zagreb Buddy Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zagrebbuddy.vercel.app",
        "http://localhost:3000",
        "http://107.189.25.214:8080",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    user_context: dict | None = None


class MessageRecord(BaseModel):
    role: str
    content: str


class PlaceResponse(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    one_liner: str
    why_recommended: str
    practical_tip: str
    visit_duration_min: int
    category: str


class ItineraryResponse(BaseModel):
    places: list[PlaceResponse]
    total_duration_min: int
    total_walking_min: int
    weather_note: str | None = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    itinerary: ItineraryResponse | None = None
    follow_ups: list[str] = []
    active_skills: list[str] = []
    needs_more_info: bool = False


class GoogleConnectResponse(BaseModel):
    authorize_url: str


class GoogleConnectCallbackRequest(BaseModel):
    code: str


class GoogleRouteRequest(BaseModel):
    places: list[PlaceResponse]


class GoogleRouteResponse(BaseModel):
    maps_directions_url: str


class CalendarEventCreateRequest(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    description: str | None = None
    timezone_name: str = "Europe/Zagreb"
    location: str | None = None


class CalendarEventUpdateRequest(BaseModel):
    event_id: str
    title: str | None = None
    description: str | None = None
    start_iso: str | None = None
    end_iso: str | None = None
    timezone_name: str = "Europe/Zagreb"
    location: str | None = None


class CalendarEventResponse(BaseModel):
    id: str
    html_link: str | None = None
    status: str | None = None


from zagreb_agent import ZagrebAgent  # noqa: E402

repository = StorageRepository(db_path=os.getenv("ZAGREB_BUDDY_DB_PATH"))
agent = ZagrebAgent(repository=repository)
google_service = GoogleIntegrationService(repository=repository)


def _require_user_id(user_id: str | None) -> str:
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing X-User-ID header",
        )
    return user_id


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())

    try:
        result = await agent.chat(
            message=req.message,
            session_id=conversation_id,
            user_context=req.user_context,
        )
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Agent failed to process message")

    return ChatResponse(conversation_id=conversation_id, **result)


@app.get("/chat/{conversation_id}/history", response_model=list[MessageRecord])
async def chat_history(conversation_id: str, limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")

    try:
        return agent.get_history(conversation_id, limit=limit)
    except Exception as e:
        logger.error(f"Failed to load chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load chat history")


@app.get("/integrations/google/connect", response_model=GoogleConnectResponse)
async def google_connect(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    resolved_user_id = _require_user_id(x_user_id)
    try:
        authorize_url = google_service.build_authorize_url(user_id=resolved_user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return GoogleConnectResponse(authorize_url=authorize_url)


@app.post("/integrations/google/callback")
async def google_callback(
    req: GoogleConnectCallbackRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    resolved_user_id = _require_user_id(x_user_id)
    try:
        token_payload = google_service.exchange_code_for_tokens(
            user_id=resolved_user_id,
            code=req.code,
        )
    except Exception as e:
        logger.error(f"Google OAuth exchange failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Google token exchange failed")

    return {
        "connected": True,
        "scope": token_payload.get("scope"),
        "expires_in": token_payload.get("expires_in"),
    }


@app.post("/integrations/google/maps/route", response_model=GoogleRouteResponse)
async def google_maps_route(
    req: GoogleRouteRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    _require_user_id(x_user_id)
    directions_url = google_service.build_google_maps_directions_url(
        [place.model_dump() for place in req.places]
    )
    if not directions_url:
        raise HTTPException(
            status_code=400,
            detail="At least two places are required to build a route",
        )
    return GoogleRouteResponse(maps_directions_url=directions_url)


@app.post("/integrations/google/calendar/events", response_model=CalendarEventResponse)
async def create_calendar_event(
    req: CalendarEventCreateRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    resolved_user_id = _require_user_id(x_user_id)
    try:
        event = google_service.create_calendar_event(
            user_id=resolved_user_id,
            title=req.title,
            description=req.description,
            start_iso=req.start_iso,
            end_iso=req.end_iso,
            timezone_name=req.timezone_name,
            location=req.location,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Google Calendar create failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Google Calendar create failed")

    return CalendarEventResponse(
        id=event["id"],
        html_link=event.get("htmlLink"),
        status=event.get("status"),
    )


@app.patch("/integrations/google/calendar/events", response_model=CalendarEventResponse)
async def update_calendar_event(
    req: CalendarEventUpdateRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    resolved_user_id = _require_user_id(x_user_id)
    try:
        event = google_service.update_calendar_event(
            user_id=resolved_user_id,
            event_id=req.event_id,
            title=req.title,
            description=req.description,
            start_iso=req.start_iso,
            end_iso=req.end_iso,
            timezone_name=req.timezone_name,
            location=req.location,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Google Calendar update failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Google Calendar update failed")

    return CalendarEventResponse(
        id=event["id"],
        html_link=event.get("htmlLink"),
        status=event.get("status"),
    )


@app.get("/health")
async def health():
    skills = agent.skills.list_skills()
    return {
        "status": "running",
        "skills_loaded": len(skills),
        "skill_names": skills,
    }
