# VozFlix Recommendation System - Quick Reference

## Phase 1: ✅ COMPLETE

### Files Created (4 files)

| File | Purpose | Key Contents |
|------|---------|--------------|
| `recommendation_config.py` | Central configuration | Algorithm weights (5 components), feature importance, caching TTL, batch job schedules, A/B testing config |
| `recommendation_schemas.py` | Pydantic models | Request/response DTOs (5 response types), data models (7 entities), query filters, metrics, A/B test results |
| `recommendation_init.py` | MongoDB setup | Create 6 collections + indexes, enhance existing collections, TTL configuration |
| `recommendation_utils.py` | Helper functions | ScoringUtils (5 scoring functions), SimilarityUtils (3 similarity algorithms), FilteringUtils (3 filters), VectorUtils, DateUtils |

### MongoDB Collections (6 New + 3 Enhanced)

**New Collections:**
```
user_preferences      → Genre weights, language, actor preferences
user_vectors          → N-dimensional embeddings (collaborative filtering)
movie_features        → Precomputed movie metadata & similarity scores
recommendation_logs   → Impression tracking (CTR, completion, device, rating)
content_similarity    → Movie-to-movie similarity matrix
recommendation_cache  → Pre-computed recommendations with TTL
```

**Enhanced Collections:**
```
watch_history         → Added: pause_count, completion_%, device, time_of_day
movies                → Added: genre, vote_average indexes
user_ratings          → Added: user+date, movie+rating indexes
```

### Configuration Summary

```python
# Core Weights (sum = 1.0)
RECOMMENDATION_WEIGHTS = {
    "genre_similarity": 0.25,
    "collaborative_filtering": 0.25,
    "popularity": 0.15,
    "content_similarity": 0.20,
    "user_behavior": 0.15,
}

# Key Thresholds
DROP_RATE_THRESHOLD = 0.20      # < 20% watched = dropped
RECENCY_BOOST_DAYS = 30         # Boost movies released in last 30 days
RATING_HALF_LIFE_DAYS = 90      # Old ratings decay to 50% weight
RECOMMENDATION_LIMIT = 20       # Return top 20 recommendations
CANDIDATE_POOL_SIZE = 1000      # Consider 1000 candidates before ranking

# Caching
RECOMMENDATION_CACHE_TTL = {
    "personalized": 2 * 3600,    # 2 hours per-user
    "trending": 1 * 3600,        # 1 hour
    "genre": 2 * 3600,           # 2 hours
    "similar": 6 * 3600,         # 6 hours
}

# Batch Jobs
recompute_user_vectors: 0 2 * * *      # 2 AM daily
recompute_trending: 0 * * * *          # Every hour
enrich_new_movies: */30 * * * *        # Every 30 minutes
```

### Utility Functions Quick Access

**Scoring:**
```python
from app.services.recommendation_utils import ScoringUtils

score = ScoringUtils.apply_time_decay(0.8, rating_date)
score = ScoringUtils.apply_recency_boost(score, release_date)
score = ScoringUtils.apply_language_boost(score, "en", "en")
```

**Similarity:**
```python
from app.services.recommendation_utils import SimilarityUtils

cosine = SimilarityUtils.cosine_similarity([0.1, 0.2], [0.15, 0.25])
jaccard = SimilarityUtils.jaccard_similarity({"action", "drama"}, {"action"})
pearson = SimilarityUtils.pearson_correlation([8, 7, 9], [7, 8, 9])
```

**Filtering:**
```python
from app.services.recommendation_utils import FilteringUtils

filtered = FilteringUtils.filter_by_user_history(
    candidates=[1, 2, 3, 4, 5],
    watched_movies={1, 3},
    watchlist_movies={2},
    exclude_watched=True,
    exclude_watchlist=True
)  # Returns [4, 5]
```

### Data Model Examples

**User Preference:**
```python
{
    "user_id": 123,
    "genre_weights": [
        {"genre_id": 28, "genre_name": "Action", "score": 0.85},
        {"genre_id": 35, "genre_name": "Comedy", "score": 0.45}
    ],
    "preferred_language": "en",
    "favorite_actors": ["Tom Hanks", "Meryl Streep"],
    "updated_at": "2026-05-14T..."
}
```

**Movie Features:**
```python
{
    "movie_id": 550,
    "title": "Fight Club",
    "genres": [{"id": 18, "name": "Drama", "score": 0.9}],
    "cast": [{"name": "Brad Pitt", "character": "Tyler Durden"}],
    "director": "David Fincher",
    "keywords": ["psychological", "revenge", "mind-bending"],
    "language": "en",
    "popularity_score": 89.5,
    "vote_average": 8.8,
    "vote_count": 15000,
    "release_date": "1999-10-15",
    "updated_at": "2026-05-14T..."
}
```

**Recommendation Log (Interaction Tracking):**
```python
{
    "user_id": 123,
    "movie_id": 550,
    "recommendation_rank": 1,
    "score": 0.87,
    "algorithm_version": "1.0",
    "shown_at": "2026-05-14T10:00:00Z",
    "clicked": True,
    "started_watching": True,
    "completion_percentage": 85.5,
    "session_duration_minutes": 145,
    "device_type": "desktop",
    "user_rating": 9.0,
    "clicked_at": "2026-05-14T10:01:00Z",
    "completed_at": "2026-05-14T12:26:00Z"
}
```

---

## Phase 2: Feature Engineering Pipeline (Next)

### What's Being Built
1. Extract movie features from TMDB → `movie_features` collection
2. Calculate user behavior signals → Enhanced `watch_history`
3. Build user preference profiles → `user_preferences` collection
4. Compute user vectors → `user_vectors` collection
5. Calculate movie similarities → `content_similarity` collection

### Services to Create
- `content_features_service.py` - Movie feature extraction & enrichment
- `user_behavior_service.py` - Behavior signal aggregation
- `user_vectorization_service.py` - Collaborative filtering vectors
- `content_similarity_service.py` - Movie-to-movie similarity

### Expected Outputs
- Populated `movie_features` (from existing `movies`)
- Populated `user_preferences` (from `watch_history` + `user_ratings`)
- Populated `user_vectors` (collaborative filtering embeddings)
- Populated `content_similarity` (all movie pairs)

---

## Getting Started with the Foundation

### 1. Initialize MongoDB Collections
```python
from app.database import db
from app.services.recommendation_init import initialize_recommendation_system

# Run once on deployment
await initialize_recommendation_system(db)
```

### 2. Import Config in Your Services
```python
from app.core.recommendation_config import RECOMMENDATION_WEIGHTS, RECOMMENDATION_CACHE_TTL

print(RECOMMENDATION_WEIGHTS)  # See current algorithm weights
```

### 3. Use Pydantic Models in Endpoints
```python
from app.models.recommendation_schemas import (
    PersonalizedRecommendationsResponse,
    RecommendationFilter,
    RecommendationLog
)

@app.post("/api/recommendations/personalized")
async def get_recommendations(req: RecommendationRequest) -> PersonalizedRecommendationsResponse:
    ...
```

### 4. Leverage Utility Functions
```python
from app.services.recommendation_utils import ScoringUtils, SimilarityUtils

# Apply time decay to ratings
decayed = ScoringUtils.apply_time_decay(score, rating_date)

# Compute user similarity for collaborative filtering
similarity = SimilarityUtils.cosine_similarity(user1_vector, user2_vector)
```

---

## Summary

✅ **Phase 1 Complete** — All foundational infrastructure in place
- Configuration system with all algorithm parameters
- Complete Pydantic models for type safety
- MongoDB schema with optimal indexes
- 20+ utility functions for common operations

🚀 **Ready for Phase 2** — Feature extraction & preprocessing
🎯 **Goal** — Build the data pipelines to populate collections
⚡ **Output** — Ready for Phase 3 (recommendation engine)
