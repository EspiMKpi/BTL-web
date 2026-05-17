"""
Recommendations router — content-based "more like this".

GET /api/recommendations/similar/{content_type}/{tmdb_id}
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.deps import get_current_user
from app.services import history_recommendation_service, recommendation_service
from app.services.library_service import (
    get_movies_by_tmdb_ids,
    get_series_by_tmdb_ids,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


async def _hydrate(content_type: str, ids: list[int]) -> list[dict]:
    """Fetch the docs for *ids* (public-visibility filtered) and return them in
    recommender order, silently dropping any that aren't in Mongo or got hidden
    between training and the request."""
    if content_type == "movie":
        docs = await get_movies_by_tmdb_ids(ids, include_hidden=False)
    else:
        docs = await get_series_by_tmdb_ids(ids, include_hidden=False)
    by_id = {d["tmdb_id"]: d for d in docs}
    return [by_id[i] for i in ids if i in by_id]


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
    return await _hydrate(content_type, ids)


@router.get("/for-you/{content_type}")
async def for_you(
    content_type: str = Path(..., pattern="^(movie|series)$"),
    limit: int = Query(10, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
):
    """Per-user "Recommended For You" — aggregated from the user's own watch
    history and favorites against the content-based TF-IDF neighbours.

    Returns [] when the user has too few positive signals (cold-start) — the
    frontend hides the rail in that case. 503 if the underlying TF-IDF
    artifact for *content_type* hasn't been trained yet.
    """
    try:
        ids = await history_recommendation_service.for_user(
            current_user["_id"], content_type, n=limit,
        )
    except recommendation_service.RecommenderNotTrained as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Recommender not trained for {content_type!r}. "
                   f"Run scripts/train_recommender.py.",
        ) from exc

    if not ids:
        return []
    return await _hydrate(content_type, ids)
