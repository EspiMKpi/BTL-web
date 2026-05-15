"""
Recommendation Engine
Core hybrid recommendation scoring and ranking engine
Combines all features: content-based, collaborative, popularity, behavior signals
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.models.recommendation_schemas import (
    RecommendationResponse,
    RecommendationScore,
    RecommendationLog,
)
from app.services.content_features_service import ContentFeaturesService
from app.services.user_behavior_service import UserBehaviorService
from app.services.user_vectorization_service import UserVectorizationService
from app.services.content_similarity_service import ContentSimilarityService
from app.services.recommendation_utils import ScoringUtils, SimilarityUtils, FilteringUtils
from app.core.recommendation_config import (
    RECOMMENDATION_WEIGHTS,
    CONTENT_FEATURE_WEIGHTS,
    BEHAVIOR_WEIGHTS,
    CANDIDATE_POOL_SIZE,
    RECOMMENDATION_LIMIT,
    MIN_RECOMMENDATION_SCORE,
    MAX_SAME_GENRE_IN_TOP_N,
    DIVERSITY_PENALTY,
    NEW_USER_STRATEGY,
    NEW_MOVIE_BOOST,
    CONTENT_FILTERS,
    RECOMMENDATION_CACHE_TTL,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Hybrid recommendation engine combining 5 scoring components"""

    def __init__(self, db):
        self.db = db
        self.movies_collection = db["movies"]
        self.watch_history_collection = db["watch_history"]
        self.user_ratings_collection = db["user_ratings"]
        self.watchlist_collection = db["watchlist_items"]
        self.recommendation_logs_collection = db["recommendation_logs"]
        self.recommendation_cache_collection = db["recommendation_cache"]

        # Initialize services
        self.features_service = ContentFeaturesService(db)
        self.behavior_service = UserBehaviorService(db)
        self.vector_service = UserVectorizationService(db)
        self.similarity_service = ContentSimilarityService(db)

    async def generate_recommendations(
        self,
        user_id: int,
        limit: int = RECOMMENDATION_LIMIT,
        use_cache: bool = True,
    ) -> List[RecommendationResponse]:
        """
        Generate personalized recommendations for a user.
        
        Algorithm Flow:
        1. Check cache
        2. Gather user profile (behavior, vector)
        3. Generate candidates (1000 movies not watched)
        4. Score each candidate with hybrid algorithm
        5. Apply diversity penalty
        6. Rank and return top N
        7. Log impressions
        
        Args:
            user_id: User ID
            limit: Max recommendations to return
            use_cache: Use cached recommendations if available
            
        Returns:
            List of RecommendationResponse objects
        """
        # Check cache first
        if use_cache:
            cached = await self._get_cached_recommendations(
                user_id, "personalized"
            )
            if cached:
                logger.info(f"Returning cached recommendations for user {user_id}")
                return cached

        logger.info(
            f"Generating new personalized recommendations for user {user_id}"
        )

        # Get user data
        behavior_signals = await self.behavior_service.get_user_behavior_signals(
            user_id
        )
        user_vector = await self.vector_service.get_user_vector(user_id)

        # Handle new user
        if not behavior_signals or not user_vector:
            recommendations = await self._handle_new_user(user_id, limit)
            await self._cache_recommendations(
                user_id, "personalized", recommendations
            )
            return recommendations

        # Get user's watched & watchlist
        watched_ids = await self._get_watched_movies(user_id)
        watchlist_ids = await self._get_watchlist_movies(user_id)

        # Generate candidates
        candidates = await self._generate_candidates(
            user_id, watched_ids, watchlist_ids, limit * 10
        )

        if not candidates:
            logger.warning(f"No candidates for user {user_id}")
            return []

        # Score candidates
        scored_candidates = []
        for movie_id in candidates:
            score_breakdown = await self._compute_hybrid_score(
                user_id, movie_id, behavior_signals, user_vector
            )
            if score_breakdown.final_score >= MIN_RECOMMENDATION_SCORE:
                scored_candidates.append(score_breakdown)

        if not scored_candidates:
            logger.warning(f"No movies passed score threshold for user {user_id}")
            return []

        # Sort by score
        scored_candidates.sort(key=lambda x: x.final_score, reverse=True)

        # Apply diversity penalty
        ranked = await self._apply_diversity_penalty(
            scored_candidates, limit
        )

        # Build response objects
        recommendations = []
        for rank, score_breakdown in enumerate(ranked[:limit], 1):
            movie = await self.movies_collection.find_one(
                {"id": score_breakdown.movie_id}
            )

            if not movie:
                continue

            rec = RecommendationResponse(
                movie_id=score_breakdown.movie_id,
                title=movie.get("title", "Unknown"),
                poster_path=movie.get("poster_path"),
                overview=movie.get("overview"),
                vote_average=movie.get("vote_average", 0),
                release_date=movie.get("release_date"),
                genres=[g.get("name", "") for g in movie.get("genres", [])],
                score=score_breakdown.final_score,
                reason=self._generate_recommendation_reason(score_breakdown),
                rank=rank,
            )
            recommendations.append(rec)

        # Cache recommendations
        await self._cache_recommendations(
            user_id, "personalized", recommendations
        )

        # Log impressions
        await self._log_recommendations(user_id, recommendations)

        logger.info(
            f"Generated {len(recommendations)} recommendations for user {user_id}"
        )

        return recommendations

    async def _compute_hybrid_score(
        self,
        user_id: int,
        movie_id: int,
        behavior_signals,
        user_vector,
    ) -> RecommendationScore:
        """
        Compute hybrid score from 5 components:
        - 25% Genre similarity
        - 25% Collaborative filtering
        - 15% Popularity
        - 20% Content similarity
        - 15% User behavior signals
        """
        movie = await self.movies_collection.find_one({"id": movie_id})

        # 1. Genre Similarity (25%)
        genre_sim = await self._compute_genre_similarity_score(
            user_id, movie_id
        )

        # 2. Collaborative Filtering (25%)
        collab_sim = await self._compute_collaborative_score(
            user_id, movie_id, user_vector
        )

        # 3. Popularity Score (15%)
        popularity_score = self._compute_popularity_score(movie)

        # 4. Content Similarity (20%)
        content_sim = await self._compute_content_similarity_score(
            user_id, movie_id
        )

        # 5. User Behavior Signals (15%)
        behavior_score = await self._compute_behavior_score(
            behavior_signals, movie_id
        )

        # Weighted combination
        final_score = (
            genre_sim * RECOMMENDATION_WEIGHTS["genre_similarity"]
            + collab_sim * RECOMMENDATION_WEIGHTS["collaborative_filtering"]
            + popularity_score * RECOMMENDATION_WEIGHTS["popularity"]
            + content_sim * RECOMMENDATION_WEIGHTS["content_similarity"]
            + behavior_score * RECOMMENDATION_WEIGHTS["user_behavior"]
        )

        # Apply modifiers
        recency_boost = ScoringUtils.apply_recency_boost(
            1.0, movie.get("release_date")
        )
        language_boost = await self._compute_language_boost(user_id, movie)

        final_score = final_score * recency_boost * language_boost

        return RecommendationScore(
            movie_id=movie_id,
            user_id=user_id,
            final_score=min(final_score, 1.0),
            genre_similarity_score=genre_sim,
            collaborative_filtering_score=collab_sim,
            popularity_score=popularity_score,
            content_similarity_score=content_sim,
            user_behavior_score=behavior_score,
            recency_boost=recency_boost,
            language_boost=language_boost,
            algorithm_version="1.0",
            computed_at=datetime.utcnow(),
        )

    async def _compute_genre_similarity_score(
        self, user_id: int, movie_id: int
    ) -> float:
        """
        Compute how well movie's genres match user's preferences.
        """
        genre_prefs = await self.behavior_service.get_user_genre_preferences(
            user_id, top_n=10
        )

        if not genre_prefs:
            return 0.5  # Neutral score for users with no history

        movie = await self.movies_collection.find_one({"id": movie_id})
        if not movie:
            return 0.0

        movie_genre_ids = {g.get("id") for g in movie.get("genres", [])}

        # Weight by preference score
        pref_map = {p["genre_id"]: p["score"] for p in genre_prefs}

        score = sum(
            pref_map.get(g_id, 0.1) for g_id in movie_genre_ids
        ) / max(len(movie_genre_ids), 1)

        return min(score, 1.0)

    async def _compute_collaborative_score(
        self,
        user_id: int,
        movie_id: int,
        user_vector,
    ) -> float:
        """
        Collaborative filtering: find similar users and see if they rated this movie.
        """
        if not user_vector:
            return 0.5

        # Find similar users
        similar_users = await self.vector_service.find_similar_users(
            user_id, top_n=50, min_similarity=0.4
        )

        if not similar_users:
            return 0.5

        # Check their ratings for this movie
        ratings = []
        for similar_user in similar_users:
            rating = await self.user_ratings_collection.find_one(
                {
                    "user_id": similar_user["user_id"],
                    "movie_id": movie_id,
                }
            )

            if rating:
                # Weight by similarity
                weighted_rating = (
                    rating.get("rating", 5.0) / 10.0
                ) * similar_user["similarity_score"]
                ratings.append(weighted_rating)

        if not ratings:
            return 0.5  # No data from similar users

        return min(sum(ratings) / len(ratings), 1.0)

    def _compute_popularity_score(self, movie: Dict) -> float:
        """
        Score based on TMDB popularity and ratings.
        """
        vote_avg = movie.get("vote_average", 5) / 10.0  # Normalize to 0-1
        vote_count = movie.get("vote_count", 0)
        popularity = movie.get("popularity", 0)

        # Normalize popularity (typical range 0-100, map to 0-1)
        popularity_norm = min(popularity / 100.0, 1.0)

        # Combine: 60% rating, 40% popularity
        score = vote_avg * 0.6 + popularity_norm * 0.4

        # Boost if many votes (more reliable)
        if vote_count > 1000:
            score = min(score * 1.1, 1.0)

        return score

    async def _compute_content_similarity_score(
        self, user_id: int, movie_id: int
    ) -> float:
        """
        Average similarity to movies user has highly rated.
        """
        # Get user's top-rated movies
        top_rated = await self.user_ratings_collection.find(
            {"user_id": user_id, "rating": {"$gte": 7}}
        ).sort("rating", -1).limit(20).to_list(None)

        if not top_rated:
            return 0.5

        similarities = []
        for rated_movie in top_rated:
            similar_movies = await self.similarity_service.get_similar_movies(
                rated_movie["movie_id"],
                limit=50,
                min_similarity=0.2,
            )

            # Check if target movie is in similar list
            for sim in similar_movies:
                if sim["movie_id"] == movie_id:
                    similarities.append(sim["similarity_score"])

        if not similarities:
            return 0.3  # Not similar to highly-rated movies

        return min(sum(similarities) / len(similarities), 1.0)

    async def _compute_behavior_score(
        self, behavior_signals, movie_id: int
    ) -> float:
        """
        Score based on user behavior: completion, drop rate, preferences.
        """
        if not behavior_signals:
            return 0.5

        # High completion rate = prefers finishing movies
        completion_factor = behavior_signals.average_completion_rate

        # Low drop rate = prefers watching to completion
        drop_penalty = 1.0 - behavior_signals.drop_rate

        # Rewatch rate indicates strong engagement
        rewatch_bonus = behavior_signals.rewatch_rate * 0.2

        score = (completion_factor * 0.5) + (drop_penalty * 0.3) + rewatch_bonus

        return min(score, 1.0)

    async def _compute_language_boost(
        self, user_id: int, movie: Dict
    ) -> float:
        """
        Boost if movie matches user's language preference.
        """
        user_prefs = await self.behavior_service.get_user_genre_preferences(
            user_id, top_n=1
        )

        # This is a simplified check; in production, track explicit language pref
        movie_language = movie.get("original_language", "unknown")

        # Default to 1.0 (no boost/penalty)
        if movie_language in ["en", "es", "fr", "de"]:
            return 1.05  # Slight boost for common languages

        return 1.0

    async def _generate_candidates(
        self,
        user_id: int,
        watched_ids: set,
        watchlist_ids: set,
        limit: int,
    ) -> List[int]:
        """
        Generate candidate movies to score.
        Strategy: Filter watched/watchlist, prefer popular & new, randomize.
        """
        # Get popular movies
        candidates_cursor = self.movies_collection.find(
            {
                "id": {"$nin": list(watched_ids | watchlist_ids)},
                "vote_average": {"$gte": CONTENT_FILTERS.get("min_rating", 3.5)},
                "vote_count": {"$gte": CONTENT_FILTERS.get("min_vote_count", 100)},
                "adult": {"$ne": True} if CONTENT_FILTERS.get("exclude_adult") else {},
            }
        ).sort("popularity", -1).limit(limit)

        candidates = []
        async for movie in candidates_cursor:
            candidates.append(movie["id"])

        return candidates

    async def _apply_diversity_penalty(
        self, scored_candidates: List[RecommendationScore], limit: int
    ) -> List[RecommendationScore]:
        """
        Apply diversity penalty: avoid recommending too many movies from same genre.
        """
        result = []
        genre_counts: Dict[int, int] = {}

        for score_obj in scored_candidates:
            movie = await self.movies_collection.find_one(
                {"id": score_obj.movie_id}
            )

            if not movie:
                continue

            # Get primary genre
            primary_genre_id = (
                movie.get("genres", [{}])[0].get("id", 0) if movie.get("genres")
                else 0
            )

            # Check if already hit genre limit
            max_same = MAX_SAME_GENRE_IN_TOP_N.get(
                f"top_{limit}", MAX_SAME_GENRE_IN_TOP_N.get("top_20", 5)
            )

            if genre_counts.get(primary_genre_id, 0) >= max_same:
                # Apply penalty
                score_obj.final_score = score_obj.final_score * DIVERSITY_PENALTY

            genre_counts[primary_genre_id] = genre_counts.get(primary_genre_id, 0) + 1
            result.append(score_obj)

            if len(result) >= len(scored_candidates):
                break

        # Re-sort after penalties
        result.sort(key=lambda x: x.final_score, reverse=True)
        return result

    async def _handle_new_user(
        self, user_id: int, limit: int
    ) -> List[RecommendationResponse]:
        """
        Handle new user with no watch history.
        Fallback: Return trending/popular movies.
        """
        logger.info(f"Handling new user {user_id}")

        # Get trending movies
        trending = await self.movies_collection.find(
            {
                "vote_average": {"$gte": 6.0},
                "vote_count": {"$gte": 100},
            }
        ).sort([("popularity", -1), ("vote_average", -1)]).limit(limit).to_list(None)

        recommendations = []
        for rank, movie in enumerate(trending, 1):
            rec = RecommendationResponse(
                movie_id=movie["id"],
                title=movie.get("title", "Unknown"),
                poster_path=movie.get("poster_path"),
                overview=movie.get("overview"),
                vote_average=movie.get("vote_average", 0),
                release_date=movie.get("release_date"),
                genres=[g.get("name", "") for g in movie.get("genres", [])],
                score=movie.get("popularity", 0) / 100.0,
                reason="Trending now",
                rank=rank,
            )
            recommendations.append(rec)

        return recommendations

    async def _get_watched_movies(self, user_id: int) -> set:
        """Get set of movie IDs user has watched."""
        watched = await self.watch_history_collection.find(
            {"user_id": user_id}
        ).to_list(None)

        return {w["movie_id"] for w in watched}

    async def _get_watchlist_movies(self, user_id: int) -> set:
        """Get set of movie IDs in user's watchlist."""
        watchlist = await self.watchlist_collection.find(
            {"user_id": user_id}
        ).to_list(None)

        return {w["movie_id"] for w in watchlist}

    def _generate_recommendation_reason(
        self, score_breakdown: RecommendationScore
    ) -> str:
        """Generate human-readable reason for recommendation."""
        # Find which component contributed most
        components = {
            "genre preference": score_breakdown.genre_similarity_score,
            "similar to favorites": score_breakdown.content_similarity_score,
            "user feedback": score_breakdown.user_behavior_score,
            "trending": score_breakdown.popularity_score,
            "users like you": score_breakdown.collaborative_filtering_score,
        }

        top_component = max(components, key=components.get)
        return f"Based on your {top_component}"

    async def _cache_recommendations(
        self,
        user_id: int,
        cache_type: str,
        recommendations: List[RecommendationResponse],
    ) -> None:
        """Cache recommendations with TTL."""
        ttl = RECOMMENDATION_CACHE_TTL.get(cache_type, 3600)

        await self.recommendation_cache_collection.update_one(
            {"user_id": user_id, "cache_type": cache_type},
            {
                "$set": {
                    "user_id": user_id,
                    "cache_type": cache_type,
                    "recommendations": [r.model_dump() for r in recommendations],
                    "created_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
                }
            },
            upsert=True,
        )

    async def _get_cached_recommendations(
        self, user_id: int, cache_type: str
    ) -> Optional[List[RecommendationResponse]]:
        """Get cached recommendations if not expired."""
        cached = await self.recommendation_cache_collection.find_one(
            {
                "user_id": user_id,
                "cache_type": cache_type,
                "expires_at": {"$gt": datetime.utcnow()},
            }
        )

        if cached:
            return [
                RecommendationResponse(**rec)
                for rec in cached.get("recommendations", [])
            ]

        return None

    async def _log_recommendations(
        self,
        user_id: int,
        recommendations: List[RecommendationResponse],
    ) -> None:
        """Log recommendation impressions for analytics."""
        for rec in recommendations:
            log = RecommendationLog(
                user_id=user_id,
                movie_id=rec.movie_id,
                recommendation_rank=rec.rank,
                score=rec.score,
                algorithm_version="1.0",
                shown_at=datetime.utcnow(),
            )

            await self.recommendation_logs_collection.insert_one(log.model_dump())
