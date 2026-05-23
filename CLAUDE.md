# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

VozFlix is a full-stack movie/TV streaming SPA. Two halves live in one repo:

- **`src/` + `public/`** — Vite-served frontend (Vanilla JS + Alpine.js + Tailwind 4). HTML page *fragments* live in `public/pages/` and are loaded into a single shell (`src/index.html`) by `src/js/pages.js`. There is no router framework; `src/js/router.js` does hash-based SPA switching.
- **`fastapi-backend/`** — Python/FastAPI server (Motor async MongoDB, JWT auth, TMDB integration, FP-Growth + GRU4Rec recommenders). Vite proxies `/api/*` → `http://localhost:8000` (see `vite.config.js`).

The backend was previously Express/TypeScript — many module docstrings still mention "mirrors database/src/...". Treat those as historical breadcrumbs; the FastAPI code is the source of truth.

## Common commands

```bash
# Frontend + backend together (recommended)
npm run dev:all                  # Vite :5173 + FastAPI :8000

# Separately
npm run dev                      # Vite only
npm run dev:fastapi              # FastAPI with --reload

# Build
npm run build                    # outputs to dist/

# Backend tests (run from fastapi-backend/)
.venv\Scripts\pytest                              # all tests, coverage gate at 60%
.venv\Scripts\pytest tests/test_auth.py -v        # one file
.venv\Scripts\pytest tests/test_auth.py::test_x   # one test
.venv\Scripts\pytest --cov-report=html            # HTML coverage → htmlcov/

# One-time data setup (from fastapi-backend/) — run in this order for the demo
.venv\Scripts\python scripts/seed_tmdb.py         # seed ~300 popular titles from TMDB
.venv\Scripts\python scripts/create_admin.py      # create/promote admin user
.venv\Scripts\python scripts/seed_demo_users.py   # 40 synthetic users + watch_history (idempotent; --wipe to remove)
.venv\Scripts\python scripts/train_fpgrowth.py    # FP-Growth rules.json → data/recommender/fpgrowth/{movies,series}/
.venv\Scripts\python scripts/train_gru4rec.py     # GRU4Rec model.pt → data/recommender/gru4rec/{movies,series}/
```

There is no frontend test suite and no linter configured.

## Backend architecture

### Request flow

`app/main.py` mounts every router under `/api/*`. Each route depends on either:
- `get_current_user` — required JWT, raises 401/403 (banned users blocked here).
- `get_optional_current_user` — returns `None` when no/invalid token (used by content rails).
- `get_admin_user` — adds `role == "admin"` check on top of `get_current_user`.

These are in `app/core/deps.py`. Auth uses PyJWT + bcrypt (passlib). The `MongoJSONResponse` class in `main.py` plus `ENCODERS_BY_TYPE[ObjectId] = str` handle `ObjectId`/`datetime` serialization globally — services and routes return raw Mongo dicts and the response layer flattens them. The `sanitize()` helper in `app/utils.py` is also available when you need to flatten a doc before any other processing.

### Cache-first content fetch

`movie_service.get_movie_by_id` and `series_service.get_series_by_id` follow: **MongoDB → miss → TMDB → upsert → return**. This is the primary mechanism that keeps TMDB calls down — never bypass it by hitting TMDB directly from a router. Genres are auto-upserted as titles are fetched.

Home rails for *anonymous* users are cached in `library_service` via `cachetools.TTLCache` (5 min, per-worker). Authenticated rails are not cached because they include per-user "For You" data. Call `library_service.clear_home_cache()` after admin visibility toggles — the admin router already does this.

### Recommender system (two algorithms, two models per algorithm)

Both inference services live under `app/services/`. Movies and series are trained as separate artifacts — there is no cross-type recommendation.

1. **`recommendation_service.py` — FP-Growth association rules** (`mlxtend`). `scripts/train_fpgrowth.py` reads positive-signal `watch_history` (completed or progress ≥ 30 min), groups by user into transactions, mines frequent itemsets, derives 1-item-antecedent rules above `min_confidence`, and writes `rules.json` + `metadata.json` under `data/recommender/fpgrowth/{movies,series}/`. Inference is a single dict lookup. Powers `GET /api/recommendations/related/{type}/{tmdb_id}` ("More Like This" / "Vì bạn đã xem") — **public, no auth**. If `min_support=0.05` yields fewer than 10 rules, training halves it down to 0.01 so demo runs with sparse data still produce something.

2. **`history_recommendation_service.py` — GRU4Rec sequential** (`torch`). `scripts/train_gru4rec.py` builds per-user chronological positive-signal sequences, deduplicates per `(user, tmdb_id)` keeping the latest, generates sliding-window `(context, target)` training pairs with left padding, and trains a single-layer GRU. Model architecture (`GRU4RecModel`) is defined in this service so training + inference share the class. Artifacts: `model.pt` + `item_vocab.json` + `metadata.json` under `data/recommender/gru4rec/{movies,series}/`. Inference loads the state_dict lazily on first request, masks out items the user has already touched, and caches the result for 10 min per `(user_id, content_type, limit)` via `cachetools.TTLCache`. Cold-start gate: < 3 in-vocab positive signals → empty list → frontend hides the rail. Powers `GET /api/recommendations/next/{type}` — **auth required**.

Both services raise `recommendation_service.RecommenderNotTrained` if the artifact directory is missing — the router translates that to HTTP 503.

**Privacy posture (changed from the original TF-IDF design):** training now reads `watch_history` (still ignores `user_ratings`). Artifacts contain item IDs and learned embeddings but no user identifiers. The old "regenerable from TMDB alone" guarantee no longer holds; rebuilding requires watch_history. For demos without real users, use `scripts/seed_demo_users.py` (40 synthetic users with `random.seed(42)`; `is_demo_seed=True` flag + `--wipe` for clean reseeding).

After bulk content seeding *or* large admin visibility toggles, the artifacts go stale until the train scripts are re-run. Stale artifacts don't crash — inference returns `[]` for tmdb_ids not in the trained vocab.

### Other backend conventions

- **Background tasks**: `POST /api/history/progress` returns `202` immediately and persists via `BackgroundTasks`. Pattern to follow for any high-frequency write where the client doesn't need the result.
- **Rate limiting**: `slowapi` in-memory per-worker. Currently on login (`10/min`) and register (`5/min`).
- **Watchlist uniqueness**: `(user_id, tmdb_id)` unique index is created at startup in `database.py` (the old 3-field index is dropped first — leave that migration code in place).
- **Hidden content filtering**: routes accessible to the public must pass through `library_service.public_content_filter()` so admin-hidden movies and movies tagged with hidden genres are stripped. Don't query `db.movies.find(...)` directly without it for user-facing surfaces.
- **Doc-type sanity**: `is_movie_doc` / `is_series_doc` in `app/utils.py` guard against series docs that ended up in the movies collection (and vice versa). Apply these after any Mongo read that mixes collections or after TMDB upserts.

## Frontend architecture

- **State**: Alpine.js stores defined in `src/js/main.js` (`auth`, `nav`, `toast`, etc.). JWT lives in `localStorage` under key `token` — `apiFetch` reads it and dispatches an `auth:expired` event on 401 so the UI can redirect to login.
- **API client**: `src/js/api.js` exports per-domain objects (`contentApi`, `watchlistApi`, `recommendationsApi`, …). Routes are not hardcoded in components — go through these wrappers.
- **Routing**: `src/js/router.js` parses `#/pageId` or `#/pageId/contentType/contentId`. `switchPage(...)` is the single entry point (also exposed as `window.switchPage`). Page fragments are loaded once on init by `src/js/pages.js`; switching is a class toggle + anime.js transition.
- **Page fragments** in `public/pages/*.html` are static HTML with Alpine directives. They're served from Vite's `publicDir`, not bundled.

## Tests

`pytest-asyncio` (auto mode) + `httpx.AsyncClient` with `ASGITransport` + `mongomock-motor`. `tests/conftest.py` auto-replaces the Motor client with a mock for every test, so tests never touch a real DB. Recommender tests build artifacts in a tmp dir via the `build_fpgrowth_artifacts` / `build_gru4rec_artifacts` fixtures (paired with `fpgrowth_artifact_root` / `gru4rec_artifact_root` to redirect `ARTIFACT_ROOT` and clear cached module state); route tests that need recommendations use these fixtures rather than mocking the services.

Coverage gate is `--cov-fail-under=60` (currently ~81%).

## Naming conventions

| Scope | Convention |
|-------|-----------|
| Backend Python | `snake_case` (files, vars, functions) |
| FastAPI path params | `{tmdb_id}`, `{content_type}`, `{user_id}` |
| Frontend JS | `camelCase` |
| CSS classes | `kebab-case` |

## Notes

- `fastapi-backend/data/` is gitignored — recommender artifacts must be rebuilt locally with `scripts/train_fpgrowth.py` and `scripts/train_gru4rec.py` (the older `train_recommender.py` was removed when the recommender moved off TF-IDF). Do not commit anything under `data/`.
- The Vite dev proxy only forwards `/api/*`. New backend routes that aren't under `/api/` won't be reachable from the frontend without proxy config changes.
- `dist/` exists in the working tree but is build output — don't edit it.
- Disclaimer in `README.md` is load-bearing: this is a university coursework project (BTL = Bài Tập Lớn), not a production deployment, and explicitly does not host video content (third-party embeds only).
