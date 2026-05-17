"""
Recommendations router — content-based "more like this".

GET /api/recommendations/similar/{content_type}/{tmdb_id}
"""

from fastapi import APIRouter, HTTPException, Path, Query

from app.services import recommendation_service
from app.services.library_service import (
    get_movies_by_tmdb_ids,
    get_series_by_tmdb_ids,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/similar/{content_type}/{tmdb_id}")
async def similar(
    content_type: str = Path(..., pattern="^(movie|series)$"),
    tmdb_id: int = Path(..., ge=1),
    limit: int = Query(10, ge=1, le=30),
):
    """Return up to *limit* similar items, ranked by cosine similarity.

    Empty list when:
      - the source tmdb_id wasn't in the trained index (e.g. seeded after the
        last training run, or hidden when training ran);
      - the recommender finds no positive-similarity neighbours;
      - all candidates were hidden between training and request time.

    503 when artifacts for the requested content_type haven't been built yet.
    """
    try:
        ids = recommendation_service.similar_to(content_type, tmdb_id, top_n=limit)
    except recommendation_service.RecommenderNotTrained as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Recommender not trained for {content_type!r}. "
                   f"Run scripts/train_recommender.py.",
        ) from exc

    if not ids:
        return []

    if content_type == "movie":
        docs = await get_movies_by_tmdb_ids(ids, include_hidden=False)
    else:
        docs = await get_series_by_tmdb_ids(ids, include_hidden=False)

    by_id = {d["tmdb_id"]: d for d in docs}
    # Preserve recommender order; drop any item whose visibility flipped to
    # hidden (or was deleted) since the last training run.
    return [by_id[i] for i in ids if i in by_id]
