# Proposed features audit (post-main sync)

Date: 2026-03-28  
Branch audited: `cursor/proposed-features-audit-7234`

## Scope

This audit re-checks roadmap items listed in `docs/future-vision.md` against the current codebase after syncing with `main`.

## Current status by proposed feature

### "Next (post-hackathon)" items

| Proposed feature | Status | Evidence |
| --- | --- | --- |
| Community-submitted places | **Not implemented** | No submission API/UI or moderation flow found in backend/frontend. |
| Live event scraping | **Not implemented** | No scraper, event ingestion pipeline, event storage, or event skill/provider integration in `agent/`. |
| Weather API integration | **Partially implemented** | Data model supports `weather_note` (`agent/main.py`, `frontend/lib/types.ts`) but no weather provider/client is integrated. |
| Multi-language (Croatian + English) | **Partially implemented** | Prompt style includes occasional Croatian wording (`agent/system_prompt.md`), but no locale switch, translations, or i18n infrastructure exists. |
| Walking navigation | **Partially implemented** | Responses include walk ordering + `total_walking_min`, and map pins exist (`frontend/components/Map/ZagrebMap.tsx`), but no route geometry, turn-by-turn, or external directions integration. |
| TOON (or similar) token optimization | **Not implemented** | No prompt compression/summarization format layer found. |

### "Future (vision)" items

| Proposed feature | Status | Evidence |
| --- | --- | --- |
| Per-user personal agents | **Partially implemented** | In-memory session history exists by conversation ID (`agent/zagreb_agent.py`), but no persistent per-user profile/preferences. |
| Agent-to-agent communication | **Not implemented** | Single-agent architecture only; no multi-agent orchestration. |
| Business partnerships | **Not implemented** | No partner metadata, ranking logic, or sponsorship controls. |
| Scale to other cities | **Partially implemented** | Skill-pack pattern is reusable, but prompts/content are Zagreb-hardcoded and there is no city abstraction. |
| Open skill marketplace | **Not implemented** | No external skill publishing/discovery/validation workflow. |

## What is already delivered (do not re-propose)

These are already implemented in the current branch/repo:

- Chat-based local friend experience (FastAPI + Next.js chat flow)
- Six specialized skills loaded from disk
- 38 curated places across current skills
- Interactive map visualization with place pins
- Mobile-friendly PWA shell and install metadata
- Skill-aware itinerary JSON contract including walking duration and optional weather note field

## Gap-only change proposals

The proposals below focus only on features that are still missing or partial.

### P0 — complete partially implemented core UX promises

1) **Weather API integration (complete existing partial model)**
- Add `agent/services/weather.py` with provider abstraction (start with Open-Meteo, no key required).
- Resolve weather by user location when available; fallback to city center coordinates.
- Populate `weather_note` server-side before/after LLM call so itinerary data is deterministic.
- Add short TTL cache (e.g., 10-15 min) to avoid repeated external calls.

2) **Walking navigation v1**
- Extend itinerary schema with optional route metadata:
  - `route_polyline` (encoded polyline or GeoJSON LineString)
  - `navigation_url` (deep link to external map app)
- Use OSRM public API (or configurable provider) to compute route geometry across suggested places.
- Render route line on `ZagrebMap` and show "Open in Maps" CTA.

3) **Localization baseline (EN/HR)**
- Add `locale` to chat request payload and pass through `user_context`.
- Introduce frontend dictionary files for static UI strings (header, errors, placeholders).
- In backend prompt assembly, pin response language based on requested locale.

### P1 — implement currently missing growth features

4) **Community-submitted places (moderated)**
- Frontend: submission form with structured fields matching `places.json` schema.
- Backend: `/submissions` endpoint storing pending entries (JSON or SQLite).
- Add moderation workflow (approve/reject), and only approved entries are merged into active skill datasets.

5) **Live events ingestion**
- Create `agent/events/` module with provider adapters (RSS/JSON endpoints first; HTML scraping optional later).
- Normalize events into a shared schema with `start_at`, `venue`, `tags`, `source_url`.
- Add an `events` skill that activates on "what's happening today/tonight" prompts.

6) **Token optimization layer**
- Implement context budget manager in `skill_loader`/agent prompt builder:
  - include only top-N matched places
  - keep dense summaries for non-active skills
  - hard cap prompt tokens by section
- Add debug logging for context size to monitor prompt growth.

### P2 — longer-horizon architecture

7) **Per-user personal agents**
- Add user identity + persistent preference store (initially SQLite/Postgres table).
- Persist likes/dislikes, time budget patterns, and favorite categories.
- Inject compact user profile summary into prompt context.

8) **Multi-city foundation**
- Introduce city config abstraction (`city_id`, center coords, language defaults, skill directory).
- Move Zagreb-specific constants into `cities/zagreb/*`.
- Keep API shape stable while supporting `?city=zagreb` now and additional cities later.

## Suggested implementation order

1. Weather API integration  
2. Walking navigation v1  
3. Localization baseline  
4. Community submissions + moderation  
5. Live events ingestion  
6. Token optimization layer  
7. Per-user personalization  
8. Multi-city foundation

This order maximizes immediate user-visible value first while reducing future refactor risk.
