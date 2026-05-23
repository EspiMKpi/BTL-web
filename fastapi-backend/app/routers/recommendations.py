"""
Recommendations router.

GET /api/recommendations/related/{content_type}/{tmdb_id}  — FP-Growth, public
GET /api/recommendations/next/{content_type}               — GRU4Rec, auth
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


@router.get("/related/{content_type}/{tmdb_id}")
async def related(
    content_type: str = Path(..., pattern="^(movie|series)$"),
    tmdb_id: int = Path(..., ge=1),
    limit: int = Query(10, ge=1, le=30),
):
    """Items frequently watched alongside *tmdb_id* (FP-Growth association
    rules with 1-item antecedents, ranked by lift).

    Empty list when:
      - tmdb_id never appeared as antecedent in any mined rule (cold-start
        item — no co-watch pairs above the support / confidence thresholds);
      - all candidates were hidden between training and request time.

    503 when artifacts for the requested content_type haven't been built yet.
    """
    try:
        ids = recommendation_service.related_items(content_type, tmdb_id, top_n=limit)
    except recommendation_service.RecommenderNotTrained as exc:
        raise HTTPException(
            status_code=503,
            detail=f"FP-Growth recommender not trained for {content_type!r}. "
                   f"Run scripts/train_fpgrowth.py.",
        ) from exc

    if not ids:
        return []
    return await _hydrate(content_type, ids)


@router.get("/next/{content_type}")
async def next_in_sequence(
    content_type: str = Path(..., pattern="^(movie|series)$"),
    limit: int = Query(10, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
):
    """Per-user sequential prediction (GRU4Rec). Empty list when the user
    has < 3 positive-signal items known to the trained vocab; the frontend
    hides the rail in that case. 503 if the model artifact for *content_type*
    hasn't been built yet.
    """
    try:
        ids = await history_recommendation_service.next_in_sequence(
            current_user["_id"], content_type, n=limit,
        )
    except recommendation_service.RecommenderNotTrained as exc:
        raise HTTPException(
            status_code=503,
            detail=f"GRU4Rec recommender not trained for {content_type!r}. "
                   f"Run scripts/train_gru4rec.py.",
        ) from exc

    if not ids:
        return []
    return await _hydrate(content_type, ids)
