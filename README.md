# VozFlix

A streaming platform web application inspired by Netflix. The frontend is built with HTML/CSS/JS and directly consumes The Movie Database (TMDB) API for content browsing, while the Spring Boot backend manages user authentication, sessions, and watchlists.

## Tech Stack

### Frontend
- HTML5, CSS3, JavaScript (Vanilla)
- Custom client-side router
- Responsive design

### Backend
- Java 21, Spring Boot 3.2
- MySQL 8.4 (JDBC)
- Redis (caching + sessions)
- Retrofit2 (TMDB API client)
- JWT (authentication)
- Maven

## Project Structure

```
BTL-web/
├── backend/                    # Spring Boot API
│   ├── src/main/
│   │   ├── java/com/vozflix/
│   │   │   ├── api/           # TMDB API interface
│   │   │   ├── config/        # App configuration
│   │   │   ├── controller/    # REST endpoints
│   │   │   ├── dao/           # JDBC data access
│   │   │   ├── dto/           # Data transfer objects
│   │   │   ├── entity/        # Domain models
│   │   │   ├── security/     # JWT & role security
│   │   │   └── service/      # Business logic
│   │   └── resources/
│   │       └── application.yml
│   ├── pom.xml
│   ├── Dockerfile
│   ├── .env.example
│   └── requirements.txt
├── frontend/                   # Frontend Docker setup
│   ├── Dockerfile              # Nginx container
│   └── nginx.conf              # Nginx configuration
├── database/
│   └── schema.sql             # MySQL schema
├── pages/                    # HTML pages
├── assets/
│   ├── css/
│   ├── fonts/
│   └── js/
├── docker-compose.yml
├── index.html
└── README.md
```

## Features

- **Frontend SPA** - Client-side routing between pages
- **Movie Browser** - Browse popular, top-rated, now-playing movies
- **TV Series** - Browse popular TV shows
- **Search** - Search movies and TV shows (cached in Redis)
- **Authentication** - JWT-based login/register
- **Session** - Theme preference stored in Redis
- **Role-based Access** - User, admin, curator roles
- **Watchlist** - Save movies to Continue Watching, Wishlist, Favorites, Completed
- **Filtering** - Filter by year, genre, type
- **User Profiles** - User account pages with stats
- **TMDB Integration** - Frontend directly consumes The Movie Database API for real-time movie/series data without backend overhead.

## Pages

| Page | Description |
|------|-------------|
| `index.html` | Landing page |
| `login.html` | User login |
| `register.html` | User registration |
| `discover.html` | Browse movies and TV shows |
| `movies.html` | Movies only |
| `series.html` | TV series only |
| `detail.html` | Movie/TV details |
| `watching.html` | Video player |
| `watchlists.html` | User watchlist |

## Setup

### Prerequisites

- Java 21+
- Maven 3.9+
- MySQL 8.4
- Redis
- Docker (optional)

### Backend Setup

```bash
cd backend

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required: DB_PASSWORD, TMDB_API_KEY
```

### Running Backend

**Local:**
```bash
mvn spring-boot:run
```

**Docker (full stack):**
```bash
docker-compose up --build
```

This starts all services:

| Service | URL |
|---------|-----|
| Frontend (Nginx) | `http://localhost:3000` |
| Backend API | `http://localhost:8080` |
| MySQL | `localhost:3306` |
| Redis | `localhost:6379` |

The Nginx frontend automatically proxies `/api/` requests to the backend.

### Frontend (local dev without Docker)

Open `index.html` in a browser, or serve with a local server:

```bash
python -m http.server 8000
```

## API Endpoints

### Authentication (Public)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user

### Session (Authenticated)
- `GET /api/session/theme` - Get user theme
- `PUT /api/session/theme` - Set user theme

### Movies
- `GET /api/movies/popular` - Popular movies
- `GET /api/movies/top-rated` - Top rated movies
- `GET /api/movies/now-playing` - Now playing movies
- `GET /api/movies/{movieId}` - Movie details
- `GET /api/movies/{movieId}/credits` - Movie credits
- `GET /api/movies/{movieId}/images` - Movie images
- `GET /api/movies/search` - Search movies
- `GET /api/movies/discover` - Discover movies with filters
- `GET /api/movies/genres` - Get movie genres
- `POST /api/movies/sync/genres` - Sync genres from TMDB

### TV Series
- `GET /api/series/popular` - Popular TV shows
- `GET /api/series/top-rated` - Top rated TV shows
- `GET /api/series/{tvId}` - TV show details
- `GET /api/series/{tvId}/season/{seasonNumber}` - Season details
- `GET /api/series/{tvId}/credits` - TV show credits
- `GET /api/series/search` - Search TV shows
- `GET /api/series/genres` - Get TV genres

### Search
- `GET /api/search` - Multi-search (cached)
- `GET /api/search/movies` - Search movies only (cached)
- `GET /api/search/series` - Search TV only (cached)

### Health
- `GET /api/health` - Health check

## Authentication

### Register
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"john","email":"john@example.com","password":"pass123"}'
```

### Login
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com","password":"pass123"}'
```

Response includes JWT token.

### Authenticated Requests
Include token in header:
```bash
curl http://localhost:8080/api/session/theme \
  -H "Authorization: Bearer <token>"
```

## User Roles

| Role | Description |
|------|-------------|
| `user` | Default user |
| `admin` | Admin access |
| `curator` | Content curator |

Access is controlled via `@RequireRole` annotation.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | 8080 | Server port |
| `DB_HOST` | localhost | MySQL host |
| `DB_PORT` | 3306 | MySQL port |
| `DB_NAME` | movie_db | Database name |
| `DB_USER` | root | MySQL user |
| `DB_PASSWORD` | - | MySQL password |
| `SPRING_DATA_REDIS_HOST` | localhost | Redis host |
| `SPRING_DATA_REDIS_PORT` | 6379 | Redis port |
| `TMDB_API_KEY` | - | TMDB API key |
| `JWT_SECRET` | - | JWT signing secret |
| `JWT_EXPIRATION` | 86400000 | JWT expiry (ms) |
| `SESSION_TTL` | 86400 | Session TTL (seconds) |
| `SEARCH_CACHE_TTL` | 3600 | Search cache TTL (seconds) |

## Database Schema

Tables in `movie_db`:

- `users` - User accounts (id, username, email, password_hash, role, is_active)
- `movies` - Cached movie data
- `series` - Cached TV show data
- `genres` - Genre reference
- `seasons` - TV season data
- `episodes` - TV episode data
- `casts` - Cast and crew
- `watchlist_items` - User watchlists
- `watch_history` - Watch history
- `user_ratings` - User ratings/reviews

## Getting a TMDB API Key

1. Go to [The Movie Database](https://www.themoviedb.org/)
2. Create an account
3. Go to Settings > API
4. Generate an API key

## License

ISC