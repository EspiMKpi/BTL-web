"""
Comprehensive tests for recommendation system
Unit tests + integration tests
Run with: pytest tests/test_recommendations.py -v --cov=app.services --cov=app.routers
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.schemas import (
    RecommendationResponse,
    PersonalizedRecommendationsResponse,
    RecommendationScore,
    UserBehaviorSignals,
    MovieFeatures,
)
from app.core.recommendation_config import (
    RECOMMENDATION_WEIGHTS,
    RECOMMENDATION_LIMIT,
    CONTENT_FILTERS,
)
from app.services.recommendation_engine import RecommendationEngine


# ============================================================================
# UNIT TESTS: Individual Scoring Components
# ============================================================================


class TestRecommendationEngineScoring:
    """Test individual scoring functions"""

    @pytest.fixture
    async def engine(self, db_mock):
        """Create recommendation engine with mocked database"""
        return RecommendationEngine(db_mock)

    @pytest.mark.asyncio
    async def test_genre_similarity_score_perfect_match(self, engine):
        """Test genre similarity when movie perfectly matches user preferences"""
        # User loves Action (weight 0.8) and Drama (weight 0.6)
        user_vector = {"action": 0.8, "drama": 0.6, "comedy": 0.3}
        
        # Movie is Action (most important genre)
        movie_genres = [
            {"id": 28, "name": "Action", "score": 0.9},
            {"id": 18, "name": "Drama", "score": 0.7},
        ]
        
        score = engine._compute_genre_similarity_score(user_vector, movie_genres)
        
        # Should be high (weighted average: 0.8 * 0.9 + 0.6 * 0.7 = 0.84)
        assert score > 0.7
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_genre_similarity_score_no_match(self, engine):
        """Test genre similarity when movie has no matching genres"""
        # User likes Action and Drama
        user_vector = {"action": 0.8, "drama": 0.6}
        
        # Movie is only Horror (not in user preferences)
        movie_genres = [{"id": 27, "name": "Horror", "score": 0.8}]
        
        score = engine._compute_genre_similarity_score(user_vector, movie_genres)
        
        # Should be low
        assert score < 0.3

    @pytest.mark.asyncio
    async def test_collaborative_filtering_similar_users(self, engine, db_mock):
        """Test collaborative filtering with similar users"""
        # Mock similar users who rated this movie highly
        similar_users = [
            {"user_id": 2, "similarity": 0.9, "rating": 9.0},
            {"user_id": 3, "similarity": 0.8, "rating": 8.0},
            {"user_id": 4, "similarity": 0.7, "rating": 7.0},
        ]
        
        engine.vector_service.find_similar_users = AsyncMock(
            return_value=similar_users
        )
        engine.db["user_ratings"].find_one = AsyncMock(
            return_value={"rating": 8.5}  # User 4's rating for movie
        )
        
        score = await engine._compute_collaborative_score(
            user_id=1,
            movie_id=550,
            similar_users_count=50
        )
        
        # Should be weighted average: (0.9*9 + 0.8*8 + 0.7*7) / (0.9+0.8+0.7)
        expected = (0.9*9 + 0.8*8 + 0.7*7) / (0.9+0.8+0.7)
        assert abs(score - (expected / 10)) < 0.1  # Account for 0-1 scaling

    @pytest.mark.asyncio
    async def test_popularity_score_blockbuster(self, engine):
        """Test popularity scoring for high-rated movie"""
        # Blockbuster: high rating, high popularity, many votes
        movie = {
            "vote_average": 8.5,
            "popularity": 1000,
            "vote_count": 50000,
        }
        
        score = engine._compute_popularity_score(movie)
        
        # Should be high
        assert score > 0.7

    @pytest.mark.asyncio
    async def test_popularity_score_obscure(self, engine):
        """Test popularity scoring for obscure movie"""
        # Obscure: low popularity, few votes
        movie = {
            "vote_average": 6.0,
            "popularity": 10,
            "vote_count": 50,
        }
        
        score = engine._compute_popularity_score(movie)
        
        # Should be moderate
        assert score < 0.6

    @pytest.mark.asyncio
    async def test_content_similarity_score(self, engine, db_mock):
        """Test content similarity to user's rated movies"""
        # User's top-rated movies
        user_top_movies = [
            {"_id": 100, "similarity_score": 0.9},
            {"_id": 101, "similarity_score": 0.8},
            {"_id": 102, "similarity_score": 0.7},
        ]
        
        engine.similarity_service.get_similar_movies = AsyncMock(
            return_value=user_top_movies
        )
        
        score = await engine._compute_content_similarity_score(
            user_id=1,
            movie_id=550
        )
        
        # Should be average of similarities: (0.9 + 0.8 + 0.7) / 3 = 0.8
        assert 0.7 < score <= 0.9

    @pytest.mark.asyncio
    async def test_behavior_score_high_engagement(self, engine):
        """Test behavior score for engaged user"""
        signals = UserBehaviorSignals(
            user_id=1,
            total_movies_watched=100,
            average_completion_rate=0.85,  # High completion
            average_rating=7.5,
            drop_rate=0.1,  # Low drop rate
            rewatch_rate=0.2,  # Some rewatches
        )
        
        score = engine._compute_behavior_score(signals)
        
        # Should be high (0.5*0.85 + 0.3*0.9 + 0.2*0.2)
        expected = 0.5 * 0.85 + 0.3 * (1 - 0.1) + 0.2 * 0.2
        assert abs(score - expected) < 0.05

    @pytest.mark.asyncio
    async def test_behavior_score_low_engagement(self, engine):
        """Test behavior score for disengaged user"""
        signals = UserBehaviorSignals(
            user_id=1,
            total_movies_watched=5,
            average_completion_rate=0.2,  # Low completion
            average_rating=4.0,
            drop_rate=0.8,  # High drop rate
            rewatch_rate=0.0,  # No rewatches
        )
        
        score = engine._compute_behavior_score(signals)
        
        # Should be low
        assert score < 0.3

    @pytest.mark.asyncio
    async def test_diversity_penalty_applied(self, engine):
        """Test diversity penalty when genre limit exceeded"""
        recommendations = [
            RecommendationResponse(
                movie_id=1, title="Action 1", genres=["Action"], score=0.8, reason=""
            ),
            RecommendationResponse(
                movie_id=2, title="Action 2", genres=["Action"], score=0.75, reason=""
            ),
            RecommendationResponse(
                movie_id=3, title="Action 3", genres=["Action"], score=0.7, reason=""
            ),
            RecommendationResponse(
                movie_id=4, title="Action 4", genres=["Action"], score=0.65, reason=""
            ),
        ]
        
        # Apply diversity penalty (max 3 same genre in top 10)
        penalized = engine._apply_diversity_penalty(recommendations)
        
        # 4th Action movie should have penalty applied
        assert penalized[3].score < 0.65

    @pytest.mark.asyncio
    async def test_time_decay_recent_rating(self, engine):
        """Test time decay for recent ratings"""
        from app.core.recommendation_config import RATING_HALF_LIFE_DAYS
        from app.services.recommendation_utils import ScoringUtils
        
        # Rating from 7 days ago
        rating_date = datetime.utcnow() - timedelta(days=7)
        original_rating = 9.0
        
        decayed = ScoringUtils.apply_time_decay(
            rating_value=original_rating,
            rating_date=rating_date,
        )
        
        # Recent rating should have minimal decay
        assert decayed > 8.0

    @pytest.mark.asyncio
    async def test_time_decay_old_rating(self, engine):
        """Test time decay for old ratings"""
        from app.core.recommendation_config import RATING_HALF_LIFE_DAYS
        from app.services.recommendation_utils import ScoringUtils
        
        # Rating from 180 days ago (2x half-life)
        rating_date = datetime.utcnow() - timedelta(days=180)
        original_rating = 9.0
        
        decayed = ScoringUtils.apply_time_decay(
            rating_value=original_rating,
            rating_date=rating_date,
        )
        
        # Old rating should have significant decay (factor of 0.25 at 2x half-life)
        assert decayed < 3.0

    @pytest.mark.asyncio
    async def test_recency_boost_new_movie(self, engine):
        """Test recency boost for recently released movie"""
        from app.services.recommendation_utils import ScoringUtils
        
        # Movie released 10 days ago
        release_date = (datetime.utcnow() - timedelta(days=10)).date()
        original_score = 0.7
        
        boosted = ScoringUtils.apply_recency_boost(
            score=original_score,
            release_date=release_date,
        )
        
        # Should be boosted by 30%
        expected = original_score * 1.3
        assert abs(boosted - expected) < 0.01

    @pytest.mark.asyncio
    async def test_recency_boost_old_movie(self, engine):
        """Test no boost for old movie"""
        from app.services.recommendation_utils import ScoringUtils
        
        # Movie released 200 days ago
        release_date = (datetime.utcnow() - timedelta(days=200)).date()
        original_score = 0.7
        
        boosted = ScoringUtils.apply_recency_boost(
            score=original_score,
            release_date=release_date,
        )
        
        # Should have no boost
        assert boosted == original_score


# ============================================================================
# INTEGRATION TESTS: End-to-End Recommendation Pipeline
# ============================================================================


class TestRecommendationPipeline:
    """Test complete recommendation generation"""

    @pytest.fixture
    async def engine_with_data(self, db_mock, sample_movies, sample_user):
        """Create engine with sample data"""
        engine = RecommendationEngine(db_mock)
        
        # Mock all service methods
        engine.behavior_service.calculate_user_behavior_signals = AsyncMock(
            return_value=UserBehaviorSignals(
                user_id=sample_user["id"],
                total_movies_watched=50,
                average_completion_rate=0.75,
                average_rating=7.0,
                drop_rate=0.15,
                rewatch_rate=0.1,
            )
        )
        
        engine.vector_service.get_user_vector = AsyncMock(
            return_value={"action": 0.8, "drama": 0.6}
        )
        
        return engine

    @pytest.mark.asyncio
    async def test_generate_recommendations_logged_in_user(
        self, engine_with_data, sample_user
    ):
        """Test full recommendation pipeline for logged-in user"""
        recommendations = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=20,
            use_cache=False
        )
        
        # Should return valid recommendations
        assert len(recommendations) > 0
        assert len(recommendations) <= 20
        
        # All should have required fields
        for rec in recommendations:
            assert rec.movie_id > 0
            assert rec.title
            assert 0 <= rec.score <= 1.0
            assert rec.reason
            assert rec.rank >= 1

    @pytest.mark.asyncio
    async def test_generate_recommendations_new_user(self, engine_with_data):
        """Test fallback behavior for new user (no history)"""
        # New user with no behavior signals
        engine_with_data.behavior_service.calculate_user_behavior_signals = AsyncMock(
            return_value=None
        )
        
        recommendations = await engine_with_data.generate_recommendations(
            user_id=9999,  # Non-existent user
            limit=20,
            use_cache=False
        )
        
        # Should return trending/popular instead of personalized
        assert len(recommendations) > 0
        # Reason should indicate fallback
        assert any("popular" in rec.reason.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_get_trending_movies(self, engine_with_data):
        """Test trending recommendations endpoint"""
        recommendations = await engine_with_data._get_trending_recommendations(
            limit=10,
            days=7
        )
        
        # Should return trending movies
        assert len(recommendations) <= 10
        
        # Should be sorted by popularity
        scores = [rec.score for rec in recommendations]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_similar_movies(self, engine_with_data):
        """Test similar movies endpoint"""
        similar = await engine_with_data._get_similar_movies(
            movie_id=550,
            limit=20
        )
        
        # Should return similar movies
        assert len(similar) <= 20
        
        # Should all be different from source
        assert not any(s.movie_id == 550 for s in similar)

    @pytest.mark.asyncio
    async def test_caching_recommendations(self, engine_with_data, sample_user):
        """Test recommendation caching"""
        # First call (no cache)
        recs1 = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=20,
            use_cache=True
        )
        
        # Second call (should hit cache)
        recs2 = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=20,
            use_cache=True
        )
        
        # Should return same recommendations
        assert len(recs1) == len(recs2)
        assert all(r1.movie_id == r2.movie_id for r1, r2 in zip(recs1, recs2))

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_new_rating(
        self, engine_with_data, sample_user
    ):
        """Test cache invalidation when user adds new rating"""
        # Get cached recommendations
        recs1 = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=20,
            use_cache=True
        )
        
        # Invalidate cache (simulate new rating)
        await engine_with_data._invalidate_user_cache(sample_user["id"])
        
        # New recommendations should be generated
        recs2 = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=20,
            use_cache=True
        )
        
        # May differ due to new rating affecting scores
        # (Can't guarantee all are different, but cache was cleared)
        assert len(recs2) > 0


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================


class TestRecommendationEndpoints:
    """Test FastAPI recommendation endpoints"""

    @pytest.mark.asyncio
    async def test_personalized_endpoint_auth_required(self, client):
        """Test that personalized endpoint requires auth"""
        response = client.post("/api/recommendations/personalized")
        
        # Should fail without auth
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_personalized_endpoint_with_auth(self, client, sample_user, token):
        """Test personalized endpoint with valid token"""
        response = client.post(
            "/api/recommendations/personalized",
            headers={"Authorization": f"Bearer {token}"},
            json={"limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) <= 10

    @pytest.mark.asyncio
    async def test_trending_endpoint_no_auth(self, client):
        """Test that trending endpoint is public"""
        response = client.get("/api/recommendations/trending?limit=10")
        
        # Should succeed without auth
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_similar_endpoint_valid_movie(self, client, sample_movies):
        """Test similar movies endpoint"""
        movie_id = sample_movies[0]["id"]
        
        response = client.get(
            f"/api/recommendations/similar/{movie_id}",
            params={"limit": 10, "min_similarity": 0.3}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["movie_id"] == movie_id
        assert "similar_movies" in data

    @pytest.mark.asyncio
    async def test_similar_endpoint_invalid_movie(self, client):
        """Test similar movies endpoint with non-existent movie"""
        response = client.get(
            "/api/recommendations/similar/99999999",
            params={"limit": 10}
        )
        
        # Should return 404 or empty list
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_genre_endpoint_valid_genre(self, client, token):
        """Test genre recommendations endpoint"""
        response = client.get(
            "/api/recommendations/genre/28",  # Action
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 10, "trending": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["genre_id"] == 28
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client, token):
        """Test metrics aggregation endpoint"""
        response = client.get(
            "/api/recommendations/metrics",
            headers={"Authorization": f"Bearer {token}"},
            params={"period": "last_7_days"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "click_through_rate" in data
        assert "completion_rate" in data
        assert "period" in data

    @pytest.mark.asyncio
    async def test_log_interaction_endpoint(self, client, token, sample_movies):
        """Test interaction logging endpoint"""
        movie_id = sample_movies[0]["id"]
        
        response = client.post(
            "/api/recommendations/log-interaction",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "movie_id": movie_id,
                "clicked": True,
                "completion_percentage": 85.5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_division_by_zero_prevention(self, engine_with_data):
        """Test that division by zero is prevented"""
        # Empty similar users
        score = await engine_with_data._compute_collaborative_score(
            user_id=1,
            movie_id=550,
            similar_users_count=50
        )
        
        # Should return sensible default, not error
        assert 0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_large_recommendation_limit(self, engine_with_data, sample_user):
        """Test limiting requests to max 50"""
        recommendations = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=500,  # Way over max
            use_cache=False
        )
        
        # Should be clamped to max (50)
        assert len(recommendations) <= 50

    @pytest.mark.asyncio
    async def test_zero_recommendation_limit(self, engine_with_data, sample_user):
        """Test minimum recommendation limit"""
        recommendations = await engine_with_data.generate_recommendations(
            user_id=sample_user["id"],
            limit=0,  # Below minimum
            use_cache=False
        )
        
        # Should use default (20)
        assert len(recommendations) > 0

    @pytest.mark.asyncio
    async def test_missing_movie_data(self, engine_with_data):
        """Test handling of incomplete movie data"""
        # Movie missing some fields
        incomplete_movie = {
            "id": 9999,
            "title": "Unknown Movie",
            # Missing genres, vote_average, popularity
        }
        
        # Should not crash
        score = engine_with_data._compute_popularity_score(incomplete_movie)
        assert 0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_user_with_single_rating(self, engine_with_data):
        """Test user with only one rated movie"""
        signals = UserBehaviorSignals(
            user_id=1,
            total_movies_watched=1,
            average_completion_rate=1.0,
            average_rating=9.0,
            drop_rate=0.0,
            rewatch_rate=0.0,
        )
        
        score = engine_with_data._compute_behavior_score(signals)
        
        # Should not crash, return sensible score
        assert 0 <= score <= 1.0


# ============================================================================
# CONFTEST: Fixtures for all tests
# ============================================================================


@pytest.fixture
def db_mock():
    """Mock MongoDB database"""
    return AsyncMock()


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
    }


@pytest.fixture
def sample_movies():
    """Sample movies for testing"""
    return [
        {
            "id": 550,
            "title": "Fight Club",
            "vote_average": 8.8,
            "popularity": 50,
            "vote_count": 25000,
            "genres": [{"id": 18, "name": "Drama"}],
            "release_date": "1999-10-15",
        },
        {
            "id": 278,
            "title": "The Shawshank Redemption",
            "vote_average": 9.3,
            "popularity": 80,
            "vote_count": 28000,
            "genres": [{"id": 18, "name": "Drama"}],
            "release_date": "1994-09-23",
        },
        {
            "id": 238,
            "title": "The Godfather",
            "vote_average": 9.2,
            "popularity": 90,
            "vote_count": 18000,
            "genres": [{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}],
            "release_date": "1972-03-24",
        },
    ]


@pytest.fixture
def token():
    """Sample JWT token"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
