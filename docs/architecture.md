# Architecture

## System diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
│                     (mobile browser)                         │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────┐               │
│  │        VERCEL (Next.js Frontend)          │               │
│  │                                           │               │
│  │  ┌─────────────────────────────────────┐  │               │
│  │  │  App Pages                          │  │               │
│  │  │  ├── Chat Interface                 │  │               │
│  │  │  ├── Interactive Map (Leaflet)      │  │               │
│  │  │  ├── Mood Selector                  │  │               │
│  │  │  └── Place Cards                    │  │               │
│  │  └─────────────────────────────────────┘  │               │
│  │                                           │               │
│  │  ┌─────────────────────────────────────┐  │               │
│  │  │  /api/chat (Route Handler)          │  │               │
│  │  │  Proxies requests to VPS            │  │               │
│  │  │  (eliminates CORS)                  │  │               │
│  │  └──────────────┬──────────────────────┘  │               │
│  └─────────────────┼─────────────────────────┘               │
│                    │                                         │
│                    │  HTTPS POST                             │
│                    ▼                                         │
│  ┌───────────────────────────────────────────┐               │
│  │        VPS (Agent Backend)                │               │
│  │                                           │               │
│  │  ┌─────────────────────────────────────┐  │               │
│  │  │  FastAPI Server                     │  │               │
│  │  │  ├── POST /chat                     │  │               │
│  │  │  ├── GET /health                    │  │               │
│  │  │  └── Session & account data (SQLite)│  │               │
│  │  └──────────────┬──────────────────────┘  │               │
│  │                 │                          │               │
│  │  ┌──────────────▼──────────────────────┐  │               │
│  │  │  ZeroClaw Agent                     │  │               │
│  │  │  ├── System Prompt (personality)    │  │               │
│  │  │  ├── Skill Loader (matches skills)  │  │               │
│  │  │  ├── Context Builder                │  │               │
│  │  │  └── Response Parser                │  │               │
│  │  └──────────────┬──────────────────────┘  │               │
│  │                 │                          │               │
│  │  ┌──────────────▼──────────────────────┐  │               │
│  │  │  Skills System                      │  │               │
│  │  │  ├── graffiti/                      │  │               │
│  │  │  ├── architecture/                  │  │               │
│  │  │  ├── local_bars/                    │  │               │
│  │  │  ├── coffee_culture/                │  │               │
│  │  │  ├── hidden_courtyards/             │  │               │
│  │  │  └── food_markets/                  │  │               │
│  │  └─────────────────────────────────────┘  │               │
│  │                 │                          │               │
│  │                 ▼                          │               │
│  │  ┌─────────────────────────────────────┐  │               │
│  │  │  Google Cloud — Gemini 2.0 Flash    │  │               │
│  │  │  (LLM API via Vertex AI)            │  │               │
│  │  └─────────────────────────────────────┘  │               │
│  └───────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Tech stack

| Layer | Technology | Why |
|-------|------------|-----|
| Frontend | Next.js 14 (App Router) | Proxy API routes, Vercel deploy |
| Styling | Tailwind CSS | Fast, mobile-first |
| Map | Leaflet + react-leaflet | Free, lightweight |
| Icons | Lucide React | Clean, consistent |
| Backend | FastAPI (Python) | Async, fast, easy |
| Agent framework | ZeroClaw | Agent orchestration |
| LLM | Gemini 2.0 Flash (Google Cloud) | Free credits, fast, large context |
| Hosting (frontend) | Vercel | Free, instant deploy |
| Hosting (backend) | VPS | Agent runtime |
| Data | SQLite (accounts/chats/preferences/contributions) + JSON/Markdown (skills) | Persistent MVP state, simple ops |
