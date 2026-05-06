"""
VozFlix FastAPI backend — replaces the Express/TypeScript server.
Run with: uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import close_mongo_connection, connect_to_mongo
from app.routers import auth, content, history, movies, profile, ratings, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="VozFlix API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — same origins as the Express cors() middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(content.router)
app.include_router(watchlist.router)
app.include_router(history.router)
app.include_router(ratings.router)
app.include_router(profile.router)


@app.get("/api/test")
async def health_check():
    return {"status": "ok"}
