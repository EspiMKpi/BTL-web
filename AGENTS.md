# BTL-web (VozFlix) — Agent Instructions

> **Read this file before making any changes to this project.**

## Project Overview

VozFlix is a movie streaming SPA with a Python/FastAPI backend that fetches movie data from the TMDB API and stores it in MongoDB (Atlas or local). Frontend uses Vite dev server with ES modules.

## Tech Stack

| Layer | Technology |
|-------|----------|
| Frontend | Vanilla HTML/CSS/JS + Alpine.js + Tailwind CSS 4 + Vite (SPA, ES modules) |
| Backend | FastAPI + Motor (async MongoDB driver) + Pydantic |
| Database | **MongoDB** (native `motor` async driver) |
| Build | Vite (frontend) |
| External API | TMDB (The Movie Database) |
| Auth | JWT (PyJWT) + bcrypt (passlib) |
| Caching | cachetools TTLCache (per-worker, 5 min TTL) |
| Rate Limiting | slowapi (in-memory, per-worker) |

## Dev Commands

```bash
# Frontend (Vite on :5173)
npm run dev

# Backend (FastAPI on :8000)
cd fastapi-backend && .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000 --app-dir .

# Both simultaneously
npm run dev:all

# Tests (with coverage)
cd fastapi-backend && .\.venv\Scripts\pytest.exe

# Or use startup scripts
cd fastapi-backend && run.bat      # Windows
cd fastapi-backend && ./run.sh     # Linux/macOS
```

## MongoDB

- **Connection string** is stored in `fastapi-backend/.env` as `MONGODB_URI`
- **Database name:** `movie_db`
- **Collections:** `movies`, `series`, `genres`, `users`, `watch_history`, `watchlist_items`, `user_ratings`
- **Types:** See `fastapi-backend/app/models/schemas.py` for all Pydantic models

## FastAPI Notes

- Route params use `:param` syntax (same as Express)
- Background tasks via `BackgroundTasks` for async writes (e.g., watch progress)
- Rate limiting via `slowapi` on auth endpoints
- Home rails cached in-memory with `cachetools.TTLCache` (anonymous only)

## Naming Conventions

- **Backend Python:** Use **snake_case** for variables, functions, file names
  - Examples: `get_movie_by_id`, `movies_collection`, `connect_mongo`
- **Frontend JS:** camelCase where DOM APIs dictate
- **CSS:** kebab-case (e.g., `movie-card`, `nav-links`)

## File Structure

```
BTL-web/
├── AGENTS.md                  # ← YOU ARE HERE
├── package.json               # Root — Vite, concurrently
├── vite.config.js             # Vite config (proxy /api → :8000)
├── src/                       # Frontend source
│   ├── index.html             # Vite entry point
│   ├── js/                    # ES modules
│   │   ├── main.js            # Entry point, Alpine.js app
│   │   ├── pages.js           # Page fragment loader
│   │   ├── router.js          # SPA page switching
│   │   ├── api.js             # Centralized API client (JWT, error handling)
│   │   └── content-helpers.js # Shared content utilities (posterUrl, getTitle, etc.)
│   └── css/                   # Stylesheets
├── public/pages/              # HTML page fragments (served raw by Vite)
└── fastapi-backend/           # Python/FastAPI backend
    ├── .env                   # MONGODB_URI, TMDB_API_KEY, JWT_SECRET
    ├── pyproject.toml         # pytest + coverage config
    ├── requirements.txt       # Pinned dependencies
    ├── run.sh / run.bat       # Startup scripts
    ├── tests/                 # pytest-asyncio + mongomock-motor tests
    │   ├── conftest.py        # Shared fixtures
    │   ├── test_auth.py       # Auth endpoint tests
    │   └── test_deps.py       # Dependency injection tests
    └── app/
        ├── main.py            # FastAPI app + CORS + rate limiting
        ├── database.py        # Motor async MongoDB client
        ├── core/
        │   ├── config.py      # Pydantic Settings from .env
        │   ├── security.py    # JWT + bcrypt
        │   └── deps.py        # get_current_user dependency
        ├── models/
        │   └── schemas.py     # Pydantic request/response models
        ├── routers/
        │   ├── auth.py        # Register, login, me (rate-limited)
        │   ├── content.py     # Home rails, genres, browse, search, series rails
        │   ├── movies.py      # Legacy movie route
        │   ├── watchlist.py   # Watchlist CRUD
        │   ├── history.py     # Watch history + background tasks
        │   ├── ratings.py     # User ratings
        │   └── profile.py     # Profile & stats
        └── services/
            ├── movie_service.py   # Movie fetch (MongoDB → TMDB → upsert)
            ├── series_service.py  # Series fetch with episodes
            └── library_service.py # Home rails (cached), genre browse, stats
```

## Key Patterns

### Two-Tier Data Fetching (`app/services/movie_service.py`)
```
Request → MongoDB → TMDB API → MongoDB (upsert) → Response
```

### Frontend Routing (`src/js/router.js`)
- Pages are HTML fragments in `public/pages/*.html`
- `pages.js` fetches them and injects into `#page-host`
- `switchPage(pageId)` toggles visibility

### Vite Proxy
- `/api/*` requests are proxied to `http://localhost:8000`
- Page fragments in `public/pages/` are served raw (no HMR injection)

## Do NOT

- Do NOT put HTML page fragments in `src/` — Vite injects HMR script into HTML files. Use `public/pages/`.
- Do NOT use camelCase for backend variable/function names
- Do NOT hardcode MongoDB connection string — always use `settings.MONGODB_URI`
- Do NOT modify CSS or frontend HTML unless explicitly asked
- Do NOT add Redis or any external cache layer without discussion
