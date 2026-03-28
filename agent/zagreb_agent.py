import json
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from dotenv import load_dotenv
from skill_loader import SkillLoader
from storage import StorageRepository

import google.generativeai as genai

load_dotenv()

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent


class ZagrebAgent:
    def __init__(self, repository: StorageRepository | None = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment / .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        print("🏙️ Zagreb Buddy — Loading skills...")
        self.skills = SkillLoader(str(AGENT_DIR / "skills"))

        self.base_system_prompt = (AGENT_DIR / "system_prompt.md").read_text()

        self.sessions: dict[str, list[dict]] = defaultdict(list)
        self.repository = repository

        print("🚀 Zagreb Buddy ready!\n")

    @staticmethod
    def _anon_identity_for_session(session_id: str) -> tuple[str, str]:
        # Deterministic anonymous identity to satisfy DB foreign keys.
        user_id = f"anon-{session_id}"
        email = f"anon+{session_id}@local.zagrebbuddy"
        return user_id, email

    def _ensure_persistent_session(self, session_id: str) -> None:
        if not self.repository:
            return

        user_id, email = self._anon_identity_for_session(session_id)
        self.repository.ensure_user(
            user_id=user_id,
            email=email,
            display_name="Anonymous User",
        )
        self.repository.ensure_chat_session(
            session_id=session_id,
            user_id=user_id,
        )

    def _load_history_from_storage(self, session_id: str) -> list[dict]:
        if not self.repository:
            return []

        if self.repository.get_chat_session(session_id) is None:
            return []

        rows = self.repository.list_chat_messages(session_id=session_id, limit=20)
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def get_history(self, session_id: str, limit: int = 100) -> list[dict]:
        if self.repository:
            rows = self.repository.list_chat_messages(session_id=session_id, limit=limit)
            return [{"role": row["role"], "content": row["content"]} for row in rows]

        history = self.sessions.get(session_id, [])
        return history[-limit:]

    def _build_full_prompt(self, matched_skills: list, user_context: dict | None) -> str:
        """Assemble the complete system prompt with dynamic context."""
        now = datetime.now()

        time_context = (
            f"- Current time: {now.strftime('%H:%M')}\n"
            f"- Day: {now.strftime('%A')}\n"
            f"- Date: {now.strftime('%Y-%m-%d')}\n"
        )

        if user_context and user_context.get("lat"):
            time_context += (
                f"- User location: {user_context['lat']}, {user_context['lng']}\n"
            )

        skill_names = [s.name for s in matched_skills] if matched_skills else ["General"]
        skill_context = self.skills.build_context_for_skills(matched_skills)

        full_prompt = f"""{self.base_system_prompt}

## YOUR AVAILABLE SKILLS
{self.skills.get_skill_summaries()}

## CURRENTLY ACTIVE: {', '.join(skill_names)}

## CURRENT CONTEXT
{time_context}

## ACTIVE SKILL DATA
{skill_context}

## RESPONSE FORMAT
You MUST respond with valid JSON matching this exact schema:
{{
  "message": "your conversational response as a friendly local",
  "itinerary": null OR {{
    "places": [
      {{
        "id": "place-id",
        "name": "Place Name",
        "lat": 45.xxxx,
        "lng": 15.xxxx,
        "one_liner": "short description",
        "why_recommended": "why this place for this person",
        "practical_tip": "what to do when they get there",
        "visit_duration_min": 20,
        "category": "cafe|street_art|bar|viewpoint|market|architecture|courtyard"
      }}
    ],
    "total_duration_min": 90,
    "total_walking_min": 20,
    "weather_note": null or "relevant weather info"
  }},
  "follow_ups": ["suggestion 1", "suggestion 2", "suggestion 3"],
  "active_skills_used": ["skill_id_1"],
  "needs_more_info": false
}}

IMPORTANT: Return ONLY the JSON object. No markdown code blocks. No extra text.
"""
        return full_prompt

    def _send_gemini(self, gemini_history: list, full_message: str) -> str:
        """Synchronous Gemini call — run in executor to avoid blocking."""
        chat = self.model.start_chat(history=gemini_history)
        response = chat.send_message(full_message)
        return response.text.strip()

    def _parse_response(self, response_text: str) -> dict:
        """Parse the LLM JSON response with fallback for malformed output."""
        try:
            text = response_text
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            logger.warning("LLM returned non-JSON response, using fallback")
            result = {
                "message": response_text,
                "itinerary": None,
                "follow_ups": [],
                "active_skills": [],
                "needs_more_info": False,
            }

        if "active_skills_used" in result:
            result["active_skills"] = result.pop("active_skills_used")

        ALLOWED_KEYS = {"message", "itinerary", "follow_ups", "active_skills", "needs_more_info"}
        result = {k: v for k, v in result.items() if k in ALLOWED_KEYS}

        result.setdefault("message", "")
        result.setdefault("itinerary", None)
        result.setdefault("follow_ups", [])
        result.setdefault("active_skills", [])
        result.setdefault("needs_more_info", False)

        return result

    async def chat(self, message: str, session_id: str, user_context: dict | None = None) -> dict:
        """Process a user message and return agent response."""
        if not self.sessions.get(session_id):
            try:
                self.sessions[session_id] = self._load_history_from_storage(session_id)
            except Exception:
                logger.exception("Failed to hydrate history from storage")

        try:
            self._ensure_persistent_session(session_id)
        except Exception:
            logger.exception("Failed to ensure persistent session")

        history = self.sessions[session_id]

        context_text = message
        if history:
            recent = " ".join(m["content"] for m in history[-4:])
            context_text = recent + " " + message

        matched_skills = self.skills.match_skills(context_text)

        system_prompt = self._build_full_prompt(matched_skills, user_context)

        gemini_history = []
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        full_message = f"System instructions:\n{system_prompt}\n\nUser message:\n{message}"

        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(
            None, self._send_gemini, gemini_history, full_message
        )

        result = self._parse_response(response_text)

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result.get("message", "")})

        if self.repository:
            try:
                self.repository.add_chat_message(
                    session_id=session_id,
                    role="user",
                    content=message,
                )
                self.repository.add_chat_message(
                    session_id=session_id,
                    role="assistant",
                    content=result.get("message", ""),
                )
            except Exception:
                logger.exception("Failed to persist chat messages")

        if len(history) > 20:
            self.sessions[session_id] = history[-20:]

        return result
