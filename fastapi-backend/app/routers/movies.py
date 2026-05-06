"""
Movies router — mirrors database/src/routes/movies.ts.
GET /:id  (legacy route)
"""

from fastapi import APIRouter, HTTPException

from app.services.movie_service import get_movie_by_id

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("/{movie_id}")
async def get_movie(movie_id: int):
    try:
        return await get_movie_by_id(movie_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
