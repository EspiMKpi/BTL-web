<div align="center">

# 🎬 VozFlix

**A modern movie & TV series streaming platform**

A full-stack SPA that lets you discover, browse, and track movies and TV series — powered by TMDB, stored in MongoDB, and built with a Python/FastAPI backend.

![Vite](https://img.shields.io/badge/Vite-6.3-646CFF?style=flat-square&logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.2-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Alpine.js](https://img.shields.io/badge/Alpine.js-3-8BC0D0?style=flat-square&logo=alpine.js&logoColor=white)

</div>

---

## ✨ Features

- 🏠 **Netflix-style Home Page** — Trending, top-rated, new releases, and personalized "Continue Watching" rails
- 🎥 **Movie & Series Browsing** — Detailed pages with cast, crew, seasons, and episodes
- 🎯 **Two-tier Recommender** — Content-based "More Like This" on every detail page (TF-IDF cosine over `overview + genres`) + per-user "Recommended For You" rails that aggregate the user's positive watch signals through the same model
- 🔍 **Search & Filters** — Real-time client-side search with genre/year/type filters
- 📋 **Watchlist Management** — Add, remove, and organize your personal watchlist
- 📊 **Watch History & Progress** — Track viewing progress across movies and series
- ⭐ **User Ratings** — Rate content and see community averages
- 💬 **Comments** — Per-title community comments with moderation
- 👤 **User Profiles** — View stats, recent activity, and manage account settings
- 🛠️ **Admin Panel** — Role-gated dashboard to ban users, hide movies, hide genres, and moderate comments
- 🔐 **JWT Authentication** — Secure register/login with bcrypt password hashing
- 🛡️ **Rate Limiting** — slowapi protects login/register against brute-force
- ⚡ **In-Memory Caching** — TTL-cached home rails for fast anonymous browsing
- 📱 **Responsive Design** — Fully responsive UI with mobile-friendly navigation
- 🎬 **Multi-Server Player** — 3 fallback streaming servers (VidLink / 2Embed / VidKing) with server switching if a title is unavailable on one provider

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vanilla HTML/CSS/JS + Alpine.js + Tailwind CSS 4 |
| **Build Tool** | Vite 6 |
| **Backend** | FastAPI + Motor (async MongoDB driver) + Pydantic |
| **Database** | MongoDB Atlas (or local MongoDB) |
| **External API** | [TMDB (The Movie Database)](https://www.themoviedb.org/) |
| **Video Embed** | VidLink.pro · 2Embed.cc · VidKing.net (multi-server fallback) |
| **Auth** | JWT (PyJWT) + bcrypt (passlib) |
| **Caching** | cachetools TTLCache (per-worker, 5 min) |
| **Rate Limiting** | slowapi (in-memory) |
| **Recommender** | scikit-learn (TF-IDF) + scipy (sparse matrix) + joblib (artifact persistence) |

## 🚀 Getting Started

### Prerequisites

- **Python** ≥ 3.11
- **Node.js** ≥ 18 (for Vite frontend)
- **MongoDB** — Atlas cluster (free tier) **or** local instance (see below)
- **TMDB API Key** — get one at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

### Installation

```bash
# Clone the repository
git clone https://github.com/EspiMKpi/BTL-web.git
cd BTL-web

# Install frontend dependencies
npm install

# Install Python backend dependencies
cd fastapi-backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux
cd ..
```

### Environment Variables

Create a `.env` file inside `fastapi-backend/`:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net
DB_NAME=movie_db
TMDB_API_KEY=your_tmdb_api_key_here
JWT_SECRET=your_super_secret_jwt_key
```

> For local MongoDB, use `MONGODB_URI=mongodb://localhost:27017` (see [Local MongoDB Setup](#-local-mongodb-setup) below).

### Running the App

```bash
# ── Frontend + FastAPI backend (recommended) ──
npm run dev:all          # Vite :5173 + FastAPI :8000

# Or run them separately:
npm run dev              # Frontend only  → http://localhost:5173
npm run dev:fastapi      # FastAPI only   → http://localhost:8000

# Or use the startup script directly:
cd fastapi-backend
./run.sh                 # Linux/macOS
run.bat                  # Windows
```

Open **http://localhost:5173** in your browser. Register a new account or use the [test account](#-test-accounts) below.

> The Vite proxy forwards `/api/*` requests to the FastAPI backend on `:8000`.

### One-time data setup

```bash
cd fastapi-backend

# Seed ~300 popular movies + TV series from TMDB into MongoDB
.venv\Scripts\python scripts/seed_tmdb.py

# Promote / create the admin account
.venv\Scripts\python scripts/create_admin.py

# Train the recommender (TF-IDF over overview + genres). Re-run after seeding
# more content or after bulk admin visibility toggles.
.venv\Scripts\python scripts/train_recommender.py
```

### Build for Production

```bash
# Build frontend
npm run build

# Run FastAPI in production mode
cd fastapi-backend
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000  # Windows
# uvicorn app.main:app --host 0.0.0.0 --port 8000                   # Linux/macOS
```

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/auth/register` | Register a new user | ❌ |
| `POST` | `/api/auth/login` | Login | ❌ |
| `GET` | `/api/auth/me` | Get current user | ✅ |

### Content

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/content/home` | Home page rails (includes "For You" rails when authenticated) | Optional |
| `GET` | `/api/content/movies/rails` | Movies page rails (Trending, Classics, "Movies For You" when auth) | Optional |
| `GET` | `/api/content/series/rails` | Series page rails (Currently Airing, "Shows For You" when auth) | Optional |
| `GET` | `/api/content/genres` | List all genres | ❌ |
| `GET` | `/api/content/browse/{genre_id}` | Browse by genre | ❌ |
| `GET` | `/api/content/search?q=` | Search movies and series | ❌ |
| `GET` | `/api/content/movie/{tmdb_id}` | Movie details (cache-first; TMDB on miss) | ❌ |
| `GET` | `/api/content/series/{tmdb_id}` | Series details + seasons + episodes | ❌ |

### Recommendations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/recommendations/similar/{content_type}/{tmdb_id}` | "More Like This" — content-based TF-IDF neighbours. `content_type` ∈ `{movie, series}`. 503 if model not yet trained. | ❌ |
| `GET` | `/api/recommendations/for-you/{content_type}` | Personalised feed seeded from the user's watch history + favorites. Empty list on cold-start (< 3 positive signals). | ✅ |

### Watchlist

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/watchlist` | Get user's watchlist | ✅ |
| `POST` | `/api/watchlist` | Add to watchlist | ✅ |
| `PATCH` | `/api/watchlist/{item_id}` | Update watchlist item | ✅ |
| `DELETE` | `/api/watchlist/{item_id}` | Remove from watchlist | ✅ |

### Watch History

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/history` | Get watch history (paginated) | ✅ |
| `GET` | `/api/history/continue-watching` | Continue watching list | ✅ |
| `POST` | `/api/history/progress` | Update watch progress (returns 202; persists in background) | ✅ |

### Ratings

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/ratings?tmdb_id=` | Get ratings for content | ❌ |
| `GET` | `/api/ratings/me` | Get current user's ratings | ✅ |
| `POST` | `/api/ratings` | Rate content | ✅ |
| `DELETE` | `/api/ratings` | Remove the current user's rating for a title | ✅ |

### Comments

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/comments/{tmdb_id}` | List comments for a title | ❌ |
| `POST` | `/api/comments` | Post a comment | ✅ |
| `DELETE` | `/api/comments/{comment_id}` | Delete your own comment | ✅ |

### Profile

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/profile` | Get user profile | ✅ |
| `PATCH` | `/api/profile` | Update profile | ✅ |
| `GET` | `/api/profile/stats` | Viewing statistics | ✅ |
| `GET` | `/api/profile/recent-activity` | Recent activity feed | ✅ |

### Admin

All `/api/admin/*` routes require `role === "admin"` (enforced via `get_admin_user`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/users` | List all users |
| `PATCH` | `/api/admin/users/{user_id}/ban` | Ban / unban a user |
| `GET` | `/api/admin/movies` | List all movies (incl. hidden) |
| `PATCH` | `/api/admin/movies/{tmdb_id}/visibility` | Hide / show a movie |
| `GET` | `/api/admin/genres` | List all genres (incl. hidden) |
| `PATCH` | `/api/admin/genres/{genre_id}/visibility` | Hide / show a genre |
| `GET` | `/api/admin/comments` | List all comments |
| `DELETE` | `/api/admin/comments/{comment_id}` | Delete a comment |

## 📁 Project Structure

```
BTL-web/
├── README.md                       # ← You are here
├── CLAUDE.md                       # Guidance for the Claude Code agent
├── package.json                    # Root — Vite, Alpine.js, Tailwind, concurrently
├── vite.config.js                  # Vite config (proxy /api → :8000)
│
├── src/                            # Frontend source
│   ├── index.html                  # Vite entry point
│   ├── js/
│   │   ├── main.js                 # Alpine.js stores, components & app logic
│   │   ├── api.js                  # Centralised API client (JWT, error handling)
│   │   ├── pages.js                # Page fragment loader
│   │   ├── router.js               # SPA page switching
│   │   └── content-helpers.js      # Shared posterUrl / getTitle / getYear helpers
│   └── css/
│       ├── base.css                # Reset & variables
│       ├── components.css          # Cards, nav, buttons
│       ├── pages.css               # Page-specific styles
│       ├── responsive.css          # Mobile breakpoints
│       └── tailwind.css            # Tailwind entry
│
├── public/
│   └── pages/                      # HTML page fragments (served raw)
│       ├── landing.html
│       ├── discover.html
│       ├── movies.html
│       ├── series.html
│       ├── detail.html             # Hero, tabs, "More Like This" rail
│       ├── watching.html
│       ├── watchlists.html
│       ├── profile.html
│       ├── admin.html              # Admin panel (movies / comments / users / genres)
│       ├── login.html
│       └── register.html
│
└── fastapi-backend/                # Python/FastAPI backend
    ├── .env                        # Environment variables
    ├── pyproject.toml              # pytest + coverage config
    ├── requirements.txt            # Pinned dependencies
    ├── run.sh / run.bat            # Startup scripts
    ├── RECOMMENDER_PLAN.md         # Design-of-record: content-based TF-IDF recommender
    ├── HISTORY_RECOMMENDER_PLAN.md # Design-of-record: per-user history-based recommender
    ├── movie-recommender-ml-model.ipynb  # Source notebook the recommender is based on
    ├── data/                       # GITIGNORED — generated recommender artifacts
    │   └── recommender/
    │       ├── movies/             # vectorizer.joblib, tfidf_matrix.npz, item_index.json, metadata.json
    │       └── series/             # same shape, separate matrix per content type
    ├── scripts/
    │   ├── seed_tmdb.py            # One-time seed of popular movies + TV from TMDB
    │   ├── create_admin.py         # Create / promote the admin user
    │   └── train_recommender.py    # Build TF-IDF artifacts from MongoDB
    ├── tests/
    │   ├── conftest.py             # Shared fixtures (mongomock, httpx, artifact_root, build_artifacts)
    │   ├── test_auth.py            # Auth endpoint tests
    │   ├── test_admin.py           # Admin panel (visibility & RBAC)
    │   ├── test_deps.py            # Dependency injection tests
    │   ├── test_content.py         # Content router tests
    │   ├── test_watchlist.py       # Watchlist CRUD tests
    │   ├── test_history.py         # History & progress tests
    │   ├── test_ratings.py         # Rating system tests
    │   ├── test_profile.py         # Profile & stats tests
    │   ├── test_library_service.py # Library service tests (incl. For-You rail wiring)
    │   ├── test_movie_service.py   # Movie service tests (mocked TMDB)
    │   ├── test_series_service.py  # Series service tests (mocked TMDB)
    │   ├── test_recommendation_service.py   # Content-based TF-IDF service
    │   ├── test_recommendations.py          # Content-based route
    │   ├── test_history_recommendation_service.py  # Per-user history-based service
    │   ├── test_history_recommendations.py         # Per-user route
    │   ├── test_security.py        # JWT & password tests
    │   └── test_health.py          # Health check & CORS tests
    └── app/
        ├── main.py                 # FastAPI app + CORS + rate limiting
        ├── database.py             # Motor async MongoDB client
        ├── utils.py                # sanitize() + is_movie_doc/is_series_doc helpers
        ├── core/
        │   ├── config.py           # Pydantic Settings from .env
        │   ├── security.py         # JWT + bcrypt (passlib)
        │   └── deps.py             # get_current_user / get_admin_user dependencies
        ├── models/
        │   └── schemas.py          # Pydantic request/response models
        ├── routers/
        │   ├── auth.py             # Register, login, me (rate-limited)
        │   ├── content.py          # Home / movies / series rails, genres, browse, search, details
        │   ├── watchlist.py        # Watchlist CRUD
        │   ├── history.py          # Watch history & progress (background tasks)
        │   ├── ratings.py          # User ratings
        │   ├── comments.py         # Comments CRUD
        │   ├── recommendations.py  # /similar + /for-you routes
        │   ├── admin.py            # Admin: users, movies, genres, comments
        │   └── profile.py          # Profile & stats
        └── services/
            ├── movie_service.py            # Movie fetch (MongoDB → TMDB → upsert)
            ├── series_service.py           # Series fetch with season/episode data
            ├── library_service.py          # Home / per-page rails, genre browse, profile stats, For-You wiring
            ├── recommendation_service.py   # Content-based TF-IDF inference (lazy load, kind+content_type validation)
            └── history_recommendation_service.py  # Per-user seed aggregation against the TF-IDF model
```

## 🗄️ Database Schema

The MongoDB database uses an **embedded document model** for content and **reference model** for user activity:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│    Users     │     │     Movies       │     │   Genres    │
├─────────────┤     ├──────────────────┤     ├─────────────┤
│ email       │     │ tmdb_id          │     │ genre_id    │
│ password    │     │ title            │     │ name        │
│ username    │     │ overview         │     └─────────────┘
│ avatar_url  │     │ genres[]         │
│ role        │     │ cast[] (embed)   │
└──────┬──────┘     │ crew[] (embed)   │
       │            └──────────────────┘
       │
       │            ┌──────────────────┐
       │            │     Series       │
       │            ├──────────────────┤
       │            │ tmdb_id          │
       │            │ name             │
       │            │ seasons[] (embed)│
       │            │   └─ episodes[]  │
       │            └──────────────────┘
       │
       ├───────┐    ┌──────────────────┐
       │       │    │  WatchHistory    │
       │       │    ├──────────────────┤
       │       │    │ user_id (ref)    │
       │       │    │ tmdb_id          │
       │       │    │ progress_seconds │
       │       │    │ completed        │
       │       │    └──────────────────┘
       │       │
       │       │    ┌──────────────────┐
       │       │    │  WatchlistItem   │
       │       │    ├──────────────────┤
       │       │    │ user_id (ref)    │
       │       │    │ content_type     │
       │       │    │ tmdb_id          │
       │       │    │ status           │
       │       │    └──────────────────┘
       │       │
       │       │    ┌──────────────────┐
       │       └───►│   UserRating     │
       │            ├──────────────────┤
       │            │ user_id (ref)    │
       │            │ tmdb_id          │
       │            │ rating (1-10)    │
       │            │ review           │
       │            └──────────────────┘
```

## 🧪 Testing

Tests use **pytest-asyncio** with **httpx.AsyncClient** (ASGI transport) and **mongomock-motor** for in-memory DB isolation — no external services or live database needed.

```bash
cd fastapi-backend

# Run all tests with coverage
.venv\Scripts\pytest

# Run specific test file
.venv\Scripts\pytest tests/test_auth.py -v

# Coverage report (HTML)
.venv\Scripts\pytest --cov-report=html
# Open htmlcov/index.html in browser
```

**206 tests** across 18 test files (minimum 60% coverage enforced in `pyproject.toml`; the suite currently sits at ~81%).

| Test File | What it Covers |
|-----------|---------------|
| `test_auth.py` | Register, login, `/me` |
| `test_admin.py` | Admin RBAC + visibility toggles (list, toggle, public filtering) |
| `test_deps.py` | JWT dependency injection, optional auth |
| `test_content.py` | Home rails, genres, browse, search, movie/series detail |
| `test_watchlist.py` | Watchlist CRUD, user isolation |
| `test_history.py` | Continue watching, history, progress updates |
| `test_ratings.py` | Public ratings, user ratings, create/delete |
| `test_profile.py` | Profile stats, recent activity, update |
| `test_library_service.py` | Home rails caching, genre browse, profile stats |
| `test_movie_service.py` | DB cache hit, TMDB fetch + upsert (mocked HTTP) |
| `test_series_service.py` | Series with seasons/episodes (mocked HTTP) |
| `test_recommendation_service.py` | TF-IDF inference, lazy load, `kind` / `content_type` validation |
| `test_recommendations.py` | `/similar` route — auth, 422, 503, hydration order, hidden filter |
| `test_history_recommendation_service.py` | Per-user seed aggregation, cold-start gate, recency weighting |
| `test_history_recommendations.py` | `/for-you` route — auth, 422, 503, cold-start, hydration |
| `test_security.py` | Password hashing, JWT lifecycle |
| `test_health.py` | Health check, CORS |

## 🗄️ Local MongoDB Setup

If you prefer a local MongoDB instance instead of Atlas:

### Option 1: MongoDB Community Server

1. Download from [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)
2. Install with default settings
3. The service runs automatically on `mongodb://localhost:27017`
4. Update `fastapi-backend/.env`:
   ```env
   MONGODB_URI=mongodb://localhost:27017
   DB_NAME=movie_db
   ```

### Option 2: Docker

```bash
docker run -d --name vozflix-mongo -p 27017:27017 mongo:7
```

Then set `MONGODB_URI=mongodb://localhost:27017` in `fastapi-backend/.env`.

### Seeding Data

The database starts empty. Content is fetched on-demand from TMDB when you browse movies/series. Genres are auto-upserted as content is fetched.

To pre-seed genres, you can run:

```bash
cd fastapi-backend
.venv\Scripts\python -c "
import asyncio
from app.database import connect_to_mongo, get_database, close_mongo_connection
async def seed():
    await connect_to_mongo()
    db = get_database()
    # Genres will be populated when movies are first fetched
    count = await db.genres.count_documents({})
    print(f'Genres in DB: {count}')
    await close_mongo_connection()
asyncio.run(seed())
"
```

## 🧪 Test Accounts

Two accounts are pre-configured for quick testing:

| Account | Email | Password | Notes |
|---------|-------|----------|-------|
| **User** | `tester@vozflix.com` | `Tester1234!` | Default tester role |
| **Admin** | `admin@vozflix.com` | `admin123` | Created via `python scripts/create_admin.py` |

The admin account unlocks the **Admin Panel** nav link, which exposes user-ban, movie-visibility, genre-visibility, and comment-moderation tabs.

> ⚠️ These accounts are for development/testing only. Do not use in production.

## 🔧 Key Architectural Decisions

### Two-Tier Data Fetching

Movies and series are fetched with a **cache-first** strategy:

```
Request → Check MongoDB → Found? → Return cached data
                        → Miss?  → Fetch from TMDB API → Upsert to MongoDB → Return
```

This minimizes external API calls and provides fast response times for repeat requests.

### Background Task Processing

Watch history progress updates (`POST /api/history/progress`) use FastAPI's `BackgroundTasks` so the client receives an immediate `202 Accepted` response while the MongoDB write happens asynchronously. Failures are logged with full context.

### In-Memory Caching

Home rails for anonymous users are cached in-memory with a 5-minute TTL using `cachetools.TTLCache`. This is per-worker and lost on restart — no external cache layer required.

### Rate Limiting

Login (`10/min`) and register (`5/min`) endpoints are rate-limited via `slowapi` to guard against brute-force attacks. The limiter is in-memory and per-worker.

### Vite Proxy

During development, Vite proxies all `/api/*` requests to the FastAPI backend on `:8000`. The proxy target is configured in `vite.config.js`.

### Recommender System

Two layers built on a single TF-IDF model:

1. **Content-based (`recommendation_service.py`)** — `scripts/train_recommender.py` fits a TF-IDF vectorizer over each title's `overview + genre names`, then writes per-content-type artifacts (`vectorizer.joblib`, `tfidf_matrix.npz`, `item_index.json`, `metadata.json`) to `fastapi-backend/data/recommender/{movies,series}/`. Inference is lazy on first request and computes cosine similarity via sparse dot-product — no dense N×N matrix is ever materialised. Powers the "More Like This" rail on every detail page.

2. **History-based (`history_recommendation_service.py`)** — for an authenticated user, treats completed watches (or progress ≥ 30 min) and favourites as *seeds*, then aggregates the top-N content-based neighbours of each seed weighted by `recency_decay × (1 / (rank + 1))`. Reuses the same TF-IDF artifact; no extra training, no extra collections. Powers the "Movies For You" / "Shows For You" rails on the home, movies, and series pages. Cold-start gate at < 3 positive signals returns an empty list so the rail is hidden rather than showing weak recommendations.

**Privacy / hard rule:** both layers read only `movies` and `series` (TMDB-sourced fields). `user_ratings` is intentionally off-limits — keeps the shared TF-IDF artifact PII-free and regenerable from public data alone.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Naming Conventions

| Scope | Convention | Example |
|-------|-----------|---------|
| Backend Python variables/functions/files | `snake_case` | `get_movie_by_id`, `movie_service.py` |
| FastAPI path params | `{param}` | `/api/content/movie/{tmdb_id}` |
| Frontend JS | `camelCase` | `switchPage`, `recommendationsApi.forYou` |
| CSS classes | `kebab-case` | `content-rail-wrapper`, `rail-arrow-left` |

## ⚠️ Disclaimer

This project is developed **strictly for educational and academic purposes only** (BTL — Bài Tập Lớn). It is a university coursework project and is **not** intended for commercial use, redistribution, or production deployment.

- **No copyrighted content is hosted or distributed** by this project. All movie/series metadata and images are sourced from the [TMDB API](https://www.themoviedb.org/) and are subject to [TMDB's terms of use](https://www.themoviedb.org/terms-of-use).
- **Video playback** is provided via third-party embed services (VidLink, 2Embed, VidKing). This project does not host, store, or distribute any video files. All streaming links point to external services.
- The developers make **no warranties** regarding the availability, accuracy, or legality of content accessed through third-party embed providers.
- This project **does not encourage piracy** or any form of copyright infringement. Users are responsible for complying with their local laws regarding online content.
- All trademarks, logos, and content referenced herein are the property of their respective owners.

## 📄 License

This project is for educational purposes only and carries **no license** for commercial use.

---

<div align="center">

**Built with ❤️ using Vite, FastAPI, Alpine.js, Python & MongoDB**

[Report Bug](https://github.com/EspiMKpi/BTL-web/issues) · [Request Feature](https://github.com/EspiMKpi/BTL-web/issues)

</div>
