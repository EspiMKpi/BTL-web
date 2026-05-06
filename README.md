<div align="center">

# 🎬 VozFlix

**A modern movie & TV series streaming platform**

A full-stack SPA that lets you discover, browse, and track movies and TV series — powered by TMDB, stored in MongoDB Atlas, and built with a clean TypeScript backend.

![Vite](https://img.shields.io/badge/Vite-6.3-646CFF?style=flat-square&logo=vite&logoColor=white)
![Express](https://img.shields.io/badge/Express-5-000000?style=flat-square&logo=express&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.2-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Alpine.js](https://img.shields.io/badge/Alpine.js-3-8BC0D0?style=flat-square&logo=alpine.js&logoColor=white)

</div>

---

## ✨ Features

- 🏠 **Netflix-style Home Page** — Trending, top-rated, new releases, and personalized "Continue Watching" rails
- 🎥 **Movie & Series Browsing** — Detailed pages with cast, crew, seasons, and episodes
- 🔍 **Search & Filters** — Real-time client-side search with genre/year/type filters
- 📋 **Watchlist Management** — Add, remove, and organize your personal watchlist
- 📊 **Watch History & Progress** — Track viewing progress across movies and series
- ⭐ **User Ratings** — Rate content and see community averages
- 👤 **User Profiles** — View stats, recent activity, and manage account settings
- 🔐 **JWT Authentication** — Secure register/login with bcrypt password hashing
- 🛡️ **Security** — Helmet, CORS, and rate limiting out of the box
- 📱 **Responsive Design** — Fully responsive UI with mobile-friendly navigation

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vanilla HTML/CSS/JS + Alpine.js + Tailwind CSS 4 |
| **Build Tool** | Vite 6 |
| **Backend** | Express 5 + TypeScript |
| **Database** | MongoDB Atlas (Mongoose ODM) |
| **External API** | [TMDB (The Movie Database)](https://www.themoviedb.org/) |
| **Auth** | JWT + bcryptjs |

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18
- **MongoDB Atlas** cluster (free tier works)
- **TMDB API Key** — get one at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

### Installation

```bash
# Clone the repository
git clone https://github.com/EspiMKpi/BTL-web.git
cd BTL-web

# Install frontend dependencies
npm install

# Install backend dependencies
cd database
npm install
cd ..
```

### Environment Variables

Create a `.env` file inside the `database/` directory:

```env
# database/.env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net
DB_NAME=movie_db
TMDB_API_KEY=your_tmdb_api_key_here
JWT_SECRET=your_super_secret_jwt_key
```

### Running the App

```bash
# Run frontend (Vite) and backend (Express) simultaneously
npm run dev:all

# Or run them separately:
npm run dev          # Frontend → http://localhost:5173
npm run dev:api      # Backend  → http://localhost:3000
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Build for Production

```bash
# Build frontend
npm run build

# Build backend
cd database && npm run build
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
| `GET` | `/api/content/home` | Home page rails | Optional |
| `GET` | `/api/content/genres` | List all genres | ❌ |
| `GET` | `/api/content/browse/:genre_id` | Browse by genre | ❌ |
| `GET` | `/api/content/movie/:id` | Movie details | ❌ |
| `GET` | `/api/content/series/:id` | Series details + episodes | ❌ |

### Watchlist

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/watchlist` | Get user's watchlist | ✅ |
| `POST` | `/api/watchlist` | Add to watchlist | ✅ |
| `PATCH` | `/api/watchlist/:id` | Update watchlist item | ✅ |
| `DELETE` | `/api/watchlist/:id` | Remove from watchlist | ✅ |

### Watch History

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/history` | Get watch history | ✅ |
| `GET` | `/api/history/continue-watching` | Continue watching list | ✅ |
| `POST` | `/api/history/progress` | Update watch progress | ✅ |

### Ratings

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/ratings?tmdb_id=` | Get ratings for content | ❌ |
| `GET` | `/api/ratings/me` | Get current user's ratings | ✅ |
| `POST` | `/api/ratings` | Rate content | ✅ |

### Profile

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/profile` | Get user profile | ✅ |
| `PATCH` | `/api/profile` | Update profile | ✅ |
| `GET` | `/api/profile/stats` | Viewing statistics | ✅ |
| `GET` | `/api/profile/recent-activity` | Recent activity feed | ✅ |

## 📁 Project Structure

```
BTL-web/
├── AGENTS.md                    # Agent/contributor instructions
├── README.md                    # ← You are here
├── package.json                 # Root — Vite, Alpine.js, Tailwind
├── vite.config.js               # Vite config (proxy /api → :3000)
│
├── src/                         # Frontend source
│   ├── index.html               # Vite entry point
│   ├── js/
│   │   ├── main.js              # Alpine.js app state & auth store
│   │   ├── pages.js             # Page fragment loader
│   │   ├── router.js            # SPA page switching
│   │   └── actions.js           # Search, filters, toast
│   └── css/
│       ├── base.css             # Reset & variables
│       ├── components.css       # Cards, nav, buttons
│       ├── pages.css            # Page-specific styles
│       ├── responsive.css       # Mobile breakpoints
│       └── tailwind.css         # Tailwind entry
│
├── public/
│   └── pages/                   # HTML page fragments (served raw)
│       ├── discover.html
│       ├── movies.html
│       ├── series.html
│       ├── detail.html
│       ├── watching.html
│       ├── watchlists.html
│       ├── login.html
│       └── register.html
│
└── database/                    # Backend
    ├── .env                     # Environment variables
    ├── package.json             # Express, Mongoose, JWT, bcrypt
    ├── tsconfig.json            # TypeScript config
    └── src/
        ├── index.ts             # Express server entry
        ├── db.ts                # MongoDB/Mongoose connection
        ├── movieService.ts      # Movie CRUD (TMDB ↔ MongoDB)
        ├── seriesService.ts     # Series CRUD with episodes
        ├── libraryService.ts    # Home rails, genre browse, profile stats
        ├── types.ts             # TypeScript interfaces (ERD models)
        ├── middleware/
        │   └── auth.ts          # JWT auth middleware
        ├── models/
        │   ├── User.ts          # User model (bcrypt pre-save hook)
        │   ├── Movie.ts         # Movie document
        │   ├── Series.ts        # Series document
        │   ├── Genre.ts         # Genre reference
        │   ├── WatchHistory.ts  # Watch progress tracking
        │   ├── WatchlistItem.ts # User watchlist
        │   └── UserRating.ts    # User ratings
        └── routes/
            ├── auth.ts          # Register, login, me
            ├── content.ts       # Home rails, genres, browse, details
            ├── movies.ts        # Legacy movie route
            ├── watchlist.ts     # Watchlist CRUD
            ├── history.ts       # Watch history & progress
            ├── ratings.ts       # User ratings
            └── profile.ts       # Profile & stats
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

## 🧪 Test Account

A test account is pre-configured for quick testing:

| Field | Value |
|-------|-------|
| **Email** | `tester@vozflix.com` |
| **Password** | `Tester1234!` |

> ⚠️ This account is for development/testing only. Do not use in production.

## 🔧 Key Architectural Decisions

### Two-Tier Data Fetching

Movies and series are fetched with a **cache-first** strategy:

```
Request → Check MongoDB → Found? → Return cached data
                        → Miss?  → Fetch from TMDB API → Upsert to MongoDB → Return
```

This minimizes external API calls and provides fast response times for repeat requests.

### Vite Proxy

During development, Vite proxies all `/api/*` requests to the Express backend at `http://localhost:3000`, so the frontend and backend share the same origin without CORS issues.

### Page Fragments

HTML pages live in `public/pages/` (not `src/`) to avoid Vite's HMR script injection. They are loaded dynamically by the SPA router.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Naming Conventions

| Scope | Convention | Example |
|-------|-----------|---------|
| Backend TS variables/functions | `snake_case` | `get_movie_by_id`, `movies_collection` |
| Frontend JS | `camelCase` | `switchPage`, `showNotification` |
| CSS classes | `kebab-case` | `movie-card`, `nav-links` |

## 📄 License

This project is for educational purposes (BTL — Bài Tập Lớn).

---

<div align="center">

**Built with ❤️ using Vite, Express, TypeScript & MongoDB**

[Report Bug](https://github.com/EspiMKpi/BTL-web/issues) · [Request Feature](https://github.com/EspiMKpi/BTL-web/issues)

</div>
