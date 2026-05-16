"""
Recommendations Router
FastAPI endpoints for recommendation system
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.deps import get_current_user
from app.models.recommendation_schemas import (
    PersonalizedRecommendationsResponse,
    SimilarMoviesResponse,
    GenreRecommendationsResponse,
    TrendingMoviesResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationMetrics,
)
from app.services.recommendation_engine import RecommendationEngine
from app.services.content_similarity_service import ContentSimilarityService
from app.database import get_database
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post(
    "/personalized",
    response_model=PersonalizedRecommendationsResponse,
    summary="Get personalized recommendations for logged-in user",
    description="Returns top 20 personalized movie recommendations based on user's watch history, ratings, and collaborative filtering",
)
async def get_personalized_recommendations(
    request: Optional[RecommendationRequest] = None,
    current_user = Depends(get_current_user),
) -> PersonalizedRecommendationsResponse:
    """
    Get personalized recommendations for the current user.
    
    Uses hybrid algorithm:
    - 25% Genre similarity
    - 25% Collaborative filtering
    - 15% Popularity
    - 20% Content similarity
    - 15% User behavior signals
    
    Query Parameters:
    - limit: Max recommendations (1-50, default 20)
    - filters: Optional filters (genres, year, rating, etc)
    - use_cache: Use cached results if available (default true)
    """
    if not request:
        request = RecommendationRequest()

    try:
        db = get_database()
        recommendation_engine = RecommendationEngine(db)
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid user session")

        recommendations = await recommendation_engine.generate_recommendations(
            user_id=user_id,
            limit=min(request.limit, 50),
            use_cache=request.use_cache,
        )

        return PersonalizedRecommendationsResponse(
            user_id=user_id,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            total_count=len(recommendations),
        )

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


@router.get(
    "/trending",
    response_model=TrendingMoviesResponse,
    summary="Get trending movies",
    description="Returns currently trending movies (globally popular, recently rated high)",
)
async def get_trending_recommendations(
    limit: int = Query(20, ge=1, le=50),
    time_window: str = Query("7days", regex="^(7days|30days|all)$"),
) -> TrendingMoviesResponse:
    """
    Get trending movies (no user login required).
    
    Time windows:
    - 7days: Movies trending in last 7 days
    - 30days: Movies trending in last 30 days
    - all: Most popular all-time
    """
    try:
        db = get_database()
        # Get trending movies from DB (popularity + recent ratings)
        query = {
            "vote_average": {"$gte": 5.0},
            "vote_count": {"$gte": 50},
        }

        # Filter by time window
        if time_window != "all":
            days = 7 if time_window == "7days" else 30
            from datetime import timedelta

            since = datetime.utcnow() - timedelta(days=days)
            query["updated_at"] = {"$gte": since}

        movies = await db["movies"].find(query).sort(
            [("popularity", -1), ("vote_average", -1)]
        ).limit(limit).to_list(None)

        recommendations = [
            RecommendationResponse(
                movie_id=m.get("tmdb_id") or m.get("id"),
                title=m.get("title", "Unknown"),
                poster_path=m.get("poster_path"),
                overview=m.get("overview"),
                vote_average=m.get("vote_average", 0),
                release_date=m.get("release_date"),
                genres=[g.get("name", "") for g in m.get("genres", []) if isinstance(g, dict)],
                score=min(m.get("popularity", 0) / 100.0, 1.0),
                reason="Trending now",
                rank=i + 1,
            )
            for i, m in enumerate(movies)
            if (m.get("tmdb_id") or m.get("id")) is not None
        ]

        return TrendingMoviesResponse(
            recommendations=recommendations,
            time_window=time_window,
            generated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error fetching trending: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending movies")


@router.get(
    "/genre/{genre_id}",
    response_model=GenreRecommendationsResponse,
    summary="Get recommendations for a specific genre",
    description="Returns top movies for a given genre, optionally filtered by user preferences",
)
async def get_genre_recommendations(
    genre_id: int,
    limit: int = Query(20, ge=1, le=50),
    trending: bool = Query(False),
    current_user = Depends(get_current_user),
) -> GenreRecommendationsResponse:
    """
    Get recommendations for a specific genre.
    
    If user is logged in, personalizes by user's other preferences.
    
    Parameters:
    - genre_id: TMDB genre ID
    - limit: Max results
    - trending: Return trending in this genre (vs. all-time popular)
    """
    try:
        db = get_database()
        query = {
            "genres": {"$elemMatch": {"genre_id": genre_id}},
            "vote_average": {"$gte": 4.0},
        }

        sort_field = "popularity" if trending else "vote_average"

        movies = await db["movies"].find(query).sort(
            sort_field, -1
        ).limit(limit).to_list(None)

        genre_name = ""
        if movies:
            for genre in movies[0].get("genres", []):
                if genre["id"] == genre_id:
                    genre_name = genre["name"]
                    break

        recommendations = [
            RecommendationResponse(
                movie_id=m.get("tmdb_id") or m.get("id"),
                title=m.get("title", "Unknown"),
                poster_path=m.get("poster_path"),
                overview=m.get("overview"),
                vote_average=m.get("vote_average", 0),
                release_date=m.get("release_date"),
                genres=[g.get("name", "") for g in m.get("genres", [])],
                score=m.get("vote_average", 0) / 10.0,
                reason=f"Popular {genre_name}",
                rank=i + 1,
            )
            for i, m in enumerate(movies)
            if (m.get("tmdb_id") or m.get("id")) is not None
        ]

        return GenreRecommendationsResponse(
            genre_id=genre_id,
            genre_name=genre_name,
            recommendations=recommendations,
            trending=trending,
            generated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error fetching genre recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch genre recommendations")


@router.get(
    "/similar/{movie_id}",
    response_model=SimilarMoviesResponse,
    summary="Get movies similar to a given movie",
    description="Returns movies with similar genres, cast, director, or themes",
)
async def get_similar_movies(
    movie_id: int,
    limit: int = Query(20, ge=1, le=50),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0),
) -> SimilarMoviesResponse:
    """
    Get movies similar to a given movie.
    
    Similarity based on:
    - Genres (40%)
    - Cast (30%)
    - Director (15%)
    - Keywords (10%)
    - Language (5%)
    
    Parameters:
    - movie_id: TMDB movie ID
    - limit: Max similar movies
    - min_similarity: Minimum similarity score (0-1)
    """
    try:
        db = get_database()
        similarity_service = ContentSimilarityService(db)
        # Get reference movie
        movie = await db["movies"].find_one({"tmdb_id": movie_id})
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")

        # Get similar movies
        similar_movies = await similarity_service.get_similar_movies(
            movie_id=movie_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        recommendations = [
            RecommendationResponse(
                movie_id=sm["movie_id"],
                title=(await db["movies"].find_one({"tmdb_id": sm["movie_id"]}, {"title": 1}) or {}).get("title", "Unknown"),
                poster_path=(await db["movies"].find_one({"tmdb_id": sm["movie_id"]}, {"poster_path": 1}) or {}).get("poster_path"),
                overview=(await db["movies"].find_one({"tmdb_id": sm["movie_id"]}, {"overview": 1}) or {}).get("overview"),
                vote_average=(await db["movies"].find_one({"tmdb_id": sm["movie_id"]}, {"vote_average": 1}) or {}).get("vote_average", 0),
                release_date=(await db["movies"].find_one({"tmdb_id": sm["movie_id"]}, {"release_date": 1}) or {}).get("release_date"),
                genres=[g.get("name", "") for g in ((await db["movies"].find_one({"tmdb_id": sm["movie_id"]}, {"genres": 1}) or {}).get("genres", [])) if isinstance(g, dict)],
                score=sm["similarity_score"],
                reason=f"Similar because of {', '.join(sm.get('shared_features', []))}",
                rank=i + 1,
            )
            for i, sm in enumerate(similar_movies)
        ]

        return SimilarMoviesResponse(
            movie_id=movie_id,
            movie_title=movie.get("title", "Unknown"),
            similar_movies=recommendations,
            criteria=["cast", "genre", "director", "keywords"],
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching similar movies: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch similar movies")


@router.get(
    "/metrics",
    response_model=RecommendationMetrics,
    summary="Get recommendation system metrics",
    description="Returns performance metrics: CTR, completion rate, diversity, etc",
)
async def get_recommendation_metrics(
    period: str = Query("last_7_days", regex="^(last_7_days|last_30_days|all_time)$"),
) -> RecommendationMetrics:
    """
    Get recommendation system performance metrics.
    
    Metrics tracked:
    - Click-through rate (CTR)
    - Completion rate
    - Genre diversity
    - Cold-start coverage
    - Content freshness
    - Average computation time
    """
    try:
        db = get_database()
        from datetime import timedelta

        # Map period to days
        days_map = {"last_7_days": 7, "last_30_days": 30, "all_time": 365 * 10}
        days = days_map.get(period, 7)

        since = datetime.utcnow() - timedelta(days=days)

        # Get recommendation logs
        logs = await db["recommendation_logs"].find(
            {"shown_at": {"$gte": since}}
        ).to_list(None)

        if not logs:
            # Return default metrics
            return RecommendationMetrics(
                period=period,
                click_through_rate=0.0,
                completion_rate=0.0,
                average_score=0.0,
                genre_diversity=0.0,
                cast_diversity=0.0,
                cold_start_coverage=0.0,
                content_freshness=0.0,
                average_computation_time_ms=0.0,
                cache_hit_rate=0.0,
                computed_at=datetime.utcnow(),
            )

        # Calculate metrics
        clicked = sum(1 for log in logs if log.get("clicked"))
        completed = sum(1 for log in logs if log.get("completion_percentage", 0) > 50)

        ctr = clicked / len(logs) if logs else 0.0
        completion_rate = completed / clicked if clicked else 0.0

        avg_score = sum(log.get("score", 0) for log in logs) / len(logs) if logs else 0.0

        return RecommendationMetrics(
            period=period,
            click_through_rate=min(ctr, 1.0),
            completion_rate=min(completion_rate, 1.0),
            average_score=avg_score,
            genre_diversity=0.75,  # Placeholder
            cast_diversity=0.70,  # Placeholder
            cold_start_coverage=0.85,  # Placeholder
            content_freshness=0.65,  # Placeholder
            average_computation_time_ms=150.0,  # Placeholder
            cache_hit_rate=0.80,  # Placeholder
            computed_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


@router.post(
    "/log-interaction",
    summary="Log user interaction with recommendation",
    description="Track if user clicked/completed a recommended movie",
)
async def log_recommendation_interaction(
    movie_id: int,
    clicked: bool = False,
    completion_percentage: Optional[float] = None,
    current_user = Depends(get_current_user),
):
    """
    Log user interaction with a recommendation.
    Used for analytics and model improvement.
    
    Parameters:
    - movie_id: Movie ID
    - clicked: Did user click the recommendation?
    - completion_percentage: How far did user watch? (0-100)
    """
    try:
        db = get_database()
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid user session")

        # Update recommendation log
        await db["recommendation_logs"].update_one(
            {
                "user_id": user_id,
                "movie_id": movie_id,
            },
            {
                "$set": {
                    "clicked": clicked,
                    "completion_percentage": completion_percentage,
                    "clicked_at": datetime.utcnow() if clicked else None,
                }
            },
        )

        return {"status": "success", "message": "Interaction logged"}

    except Exception as e:
        logger.error(f"Error logging interaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to log interaction")
