# BTL-web (VozFlix) — Agent Instructions

> **Read this file before making any changes to this project.**

## Project Overview

VozFlix is a movie streaming SPA with a TypeScript/Express backend that fetches movie data from the TMDB API and stores it in MongoDB Atlas. Frontend uses Vite dev server with ES modules.

## Tech Stack

| Layer | Technology |
|-------|----------|
| Frontend | Vanilla HTML/CSS/JS + Vite (SPA, ES modules) |
| Backend | Express 5 + TypeScript (compiled to JS) |
| Database | **MongoDB Atlas** (native `mongodb` driver) |
| Build | Vite (frontend), tsc (backend) |
| External API | TMDB (The Movie Database) |

## Dev Commands

```bash
# Frontend (Vite on :5173)
npm run dev

# Backend (Express on :3000)
cd database && npm run dev

# Both simultaneously
npm run dev:all
```

## MongoDB Atlas

- **Connection string** is stored in `database/.env` as `MONGODB_URI`
- **Database name:** `movie_db`
- **Collection:** `movies` (single collection, embedded document model)
- **Types:** See `database/src/types.ts` for all interfaces

## Express 5 Notes

- Route params use `:param` syntax
- `req.params.id` can be `string | string[]` — always normalize
- `app.listen()` returns the server synchronously; use callback pattern

## Naming Conventions

- **Backend TS:** Use **snake_case** for variables, functions, file names
  - Examples: `get_movie_by_id`, `movies_collection`, `connect_mongo`
  - Exception: Express/TypeScript mandated camelCase
- **Frontend JS:** camelCase where DOM APIs dictate
- **CSS:** kebab-case (e.g., `movie-card`, `nav-links`)

## File Structure

```
BTL-web/
├── AGENTS.md                  # ← YOU ARE HERE
├── package.json               # Root — Vite, concurrently
├── vite.config.js             # Vite config (proxy /api → :3000)
├── src/                       # Frontend source
│   ├── index.html             # Vite entry point
│   ├── js/                    # ES modules
│   │   ├── main.js            # Entry point, event delegation
│   │   ├── pages.js           # Page fragment loader
│   │   ├── router.js          # SPA page switching
│   │   └── actions.js         # Search, filters, toast
│   └── css/                   # Stylesheets
├── public/pages/              # HTML page fragments (served raw by Vite)
├── database/                  # Backend
│   ├── .env                   # MONGODB_URI, TMDB_API_KEY
│   ├── src/                   # TypeScript source
│   │   ├── index.ts           # Express server entry
│   │   ├── db.ts              # MongoDB connection
│   │   ├── movieService.ts    # Movie CRUD
│   │   └── types.ts           # TypeScript interfaces
│   ├── dist/                  # Compiled JS output
│   ├── tsconfig.json
│   └── package.json
```

## Key Patterns

### Two-Tier Data Fetching (`database/src/movieService.ts`)
```
Request → MongoDB → TMDB API → MongoDB (upsert) → Response
```

### Frontend Routing (`src/js/router.js`)
- Pages are HTML fragments in `public/pages/*.html`
- `pages.js` fetches them and injects into `#page-host`
- `switchPage(pageId)` toggles visibility

### Vite Proxy
- `/api/*` requests are proxied to `http://localhost:3000`
- Page fragments in `public/pages/` are served raw (no HMR injection)

## Do NOT

- Do NOT put HTML page fragments in `src/` — Vite injects HMR script into HTML files. Use `public/pages/`.
- Do NOT use camelCase for backend variable/function names
- Do NOT hardcode MongoDB connection string — always use `process.env.MONGODB_URI`
- Do NOT modify CSS or frontend HTML unless explicitly asked
- Do NOT add Redis or any external cache layer without discussion
