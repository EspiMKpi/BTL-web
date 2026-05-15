"""
Phase 2: Feature Engineering Pipeline - COMPLETED
Summary of services created for data pipeline
"""

## 📋 Phase 2 Completion Summary

### ✅ Files Created (4 Core Services)

#### 1. **`content_features_service.py`** (420 lines)
**Purpose:** Extract movie features from TMDB data and cache for efficient retrieval

**Key Methods:**
- `extract_movie_features(movie_id)` — Extract genres, cast, director, keywords from TMDB → store in `movie_features` collection
- `enrich_movie_features(movie_id)` — Add derived features (popularity trends, embeddings)
- `get_movie_features(movie_id)` — Retrieve from cache or extract if missing
- `extract_all_movie_features()` — Batch extract for all movies (initial setup)
- `compute_genre_similarity(id1, id2)` — Jaccard similarity on genres
- `compute_cast_similarity(id1, id2)` — Jaccard similarity on actors
- `get_similar_movies_by_features(id)` — Find movies with similar genres/cast/director/keywords

**Features Extracted:**
```
Movie Features:
├── genres              # [{id, name, score}] sorted by importance
├── cast                # Top 10 actors: [{name, character, order}]
├── director            # Primary director name
├── keywords            # Top 15 plot keywords/themes
├── production_company  # Primary production company
├── language            # Original language (en, es, fr, etc)
├── certification       # Content rating (PG, R, etc)
├── popularity_score    # TMDB popularity metric
├── vote_average        # TMDB rating (0-10)
├── vote_count          # Number of votes
├── release_date        # YYYY-MM-DD format
├── embeddings          # Optional: future ML embeddings
└── updated_at          # Last update timestamp
```

**Output Collections:** `movie_features`, enhanced `movies`

---

#### 2. **`user_behavior_service.py`** (380 lines)
**Purpose:** Calculate user behavior signals from watch history and ratings

**Key Methods:**
- `calculate_user_behavior_signals(user_id)` — Aggregate stats: completion rate, drop rate, avg rating, session duration, rewatch rate
- `get_user_behavior_signals(user_id)` — Retrieve cached signals or calculate
- `get_user_genre_preferences(user_id, top_n)` — Rank genres by user preference
- `get_user_favorite_actors(user_id, top_n)` — Top actors user watches
- `get_user_watch_streak(user_id)` — Current streak (hot/active/mild/broken)
- `calculate_all_user_signals()` — Batch calculate for all users

**Signals Computed:**
```
User Behavior Signals:
├── total_movies_watched        # Count
├── total_series_watched        # Count
├── average_completion_rate     # 0-1 (% watched)
├── average_rating              # 0-10 (user ratings)
├── drop_rate                   # % of movies abandoned <20%
├── average_session_duration    # Minutes
├── rewatch_rate                # % of rewatches
├── last_activity               # Last watch date/time
└── preferred_watch_time_of_day # Morning/Afternoon/Evening/Night

Genre Preferences:
├── genre_id
├── genre_name
├── score                       # 0-1 normalized preference
└── watch_count                 # How many movies of this genre

Favorite Actors:
├── name
├── score                       # 0-1 normalized preference
└── movie_count                 # Movies watched with this actor

Watch Streak:
├── current_streak_days
├── last_watch_date
└── streak_type                 # hot (7+), active (3+), mild (1-2), broken (0)
```

**Output Collections:** `user_behavior_signals`, enhanced `watch_history`, `user_ratings`

---

#### 3. **`user_vectorization_service.py`** (400 lines)
**Purpose:** Create user embedding vectors for collaborative filtering

**Key Methods:**
- `compute_user_vector(user_id, vector_dimension)` — Create N-dimensional vector from genre preferences
  - Strategy: Genre-based, time-decay ratings, normalized vectors
  - Default dimension: 100
  - Requires: 3+ rated movies
- `get_user_vector(user_id)` — Retrieve cached vector or compute
- `find_similar_users(user_id, top_n)` — Find users with similar taste
- `compute_user_similarity(id1, id2)` — Cosine similarity between user vectors
- `compute_rating_correlation(id1, id2)` — Pearson correlation (alternative similarity metric)
- `compute_all_user_vectors()` — Batch compute for all users
- `get_vector_statistics(user_id)` — Vector stats (magnitude, mean, std_dev, etc)

**Vector Computation:**
```
Process:
1. Get user's rated movies
2. Aggregate genre scores (weighted by rating + time decay)
3. Create fixed-dimension vector (default: 100)
4. Normalize to unit vector (L2)
5. Store in user_vectors collection

Example (simplified):
User_1_vector = [
  0.95,  # Action (strongly preferred)
  0.72,  # Drama
  0.35,  # Comedy
  0.0,   # Horror
  ...    # 96 more dimensions
]

Similarity = cosine_similarity(User_1_vector, User_2_vector)
           = dot_product / (||v1|| * ||v2||)
           = score 0-1 (0=opposite, 1=identical)
```

**Output Collections:** `user_vectors`, enhanced `user_ratings`

---

#### 4. **`content_similarity_service.py`** (450 lines)
**Purpose:** Compute and cache movie-to-movie similarity for efficient "similar movies" recommendations

**Key Methods:**
- `compute_pairwise_similarity(id1, id2)` — Compute similarity between two movies
  - Weighing: 40% genre + 30% cast + 15% director + 10% keywords + 5% language
  - Stores both directions (symmetric lookup)
- `get_similar_movies(movie_id, limit, min_similarity)` — Get top N similar movies
- `compute_all_similarities(batch_size, min_similarity)` — Batch compute all pairs ⚠️ Expensive
- `find_cluster_members(movie_id, depth)` — Find transitive clusters (movies related through intermediaries)
- `get_similarity_stats()` — Statistics on cached similarities

**Similarity Scoring:**
```
For movies A and B:

genre_sim      = Jaccard({genres_A} ∩ {genres_B})
cast_sim       = Jaccard({cast_A} ∩ {cast_B})
director_sim   = 1.0 if same director else 0.0
keywords_sim   = Jaccard({keywords_A} ∩ {keywords_B})
language_sim   = 1.0 if same language else 0.0

final_score = (
  genre_sim * 0.40 +
  cast_sim * 0.30 +
  director_sim * 0.15 +
  keywords_sim * 0.10 +
  language_sim * 0.05
)  # Result: 0-1

shared_features = ["genre", "cast", "director", "keywords"]
```

**Output Collections:** `content_similarity`

---

### 📊 Data Pipeline Architecture

```
TMDB Movie Data
    ↓
content_features_service
    ↓
[movie_features] ← Genres, cast, director, keywords, language
    
User Watch History + Ratings
    ↓
user_behavior_service
    ↓
[user_behavior_signals] ← Completion, drop rate, engagement, preferences
    
User Ratings
    ↓
user_vectorization_service
    ↓
[user_vectors] ← N-dimensional embeddings for collaborative filtering
    
movie_features
    ↓
content_similarity_service
    ↓
[content_similarity] ← Movie-to-movie similarity matrix (pairwise)
```

---

### 🗂️ Collections Populated in Phase 2

| Collection | Populated By | Source | Records |
|------------|-------------|--------|---------|
| `movie_features` | content_features_service | movies collection | ~10K (all movies) |
| `user_behavior_signals` | user_behavior_service | watch_history + ratings | ~1K (active users) |
| `user_vectors` | user_vectorization_service | user_ratings | ~1K (users with 3+ ratings) |
| `content_similarity` | content_similarity_service | movie_features | ~50M (all pairs if computed) |

---

### 🚀 Usage Examples

#### Extract Movie Features
```python
from app.services.content_features_service import ContentFeaturesService

features_service = ContentFeaturesService(db)

# Extract for single movie
features = await features_service.extract_movie_features(550)  # Fight Club
print(features.genres)  # [{id: 18, name: "Drama", score: 0.9}, ...]

# Batch extract all (initial setup)
result = await features_service.extract_all_movie_features()
# Output: {processed: 10000, errors: 2}
```

#### Calculate User Behavior
```python
from app.services.user_behavior_service import UserBehaviorService

behavior_service = UserBehaviorService(db)

# Get user signals
signals = await behavior_service.calculate_user_behavior_signals(user_id=123)
print(signals.average_completion_rate)  # 0.75
print(signals.drop_rate)  # 0.15

# Get genre preferences
prefs = await behavior_service.get_user_genre_preferences(user_id=123, top_n=5)
# [{genre_id: 28, genre_name: "Action", score: 0.85, watch_count: 12}, ...]
```

#### Create User Vectors
```python
from app.services.user_vectorization_service import UserVectorizationService

vector_service = UserVectorizationService(db)

# Compute user vector
user_vector = await vector_service.compute_user_vector(user_id=123)
print(user_vector.vector)  # [0.95, 0.72, 0.35, 0.0, ...]
print(user_vector.dimension)  # 100

# Find similar users
similar = await vector_service.find_similar_users(user_id=123, top_n=10)
# [{user_id: 456, similarity_score: 0.82}, ...]

# Batch compute (all users)
result = await vector_service.compute_all_user_vectors()
# {processed: 1000, skipped: 50, errors: 2}
```

#### Compute Content Similarity
```python
from app.services.content_similarity_service import ContentSimilarityService

similarity_service = ContentSimilarityService(db)

# Get similar movies
similar = await similarity_service.get_similar_movies(
    movie_id=550,  # Fight Club
    limit=20,
    min_similarity=0.3
)
# [{movie_id: 278, similarity_score: 0.72, shared_features: ["genre", "director"]}, ...]

# Find movie cluster (transitive)
cluster = await similarity_service.find_cluster_members(
    movie_id=550,
    depth=2,
    min_similarity=0.4
)
# [550, 278, 19404, 12345, ...]
```

---

### 📈 Performance Considerations

**Extraction Time Estimates (10K movies, 1K active users):**
- `extract_all_movie_features()` — ~2-3 minutes (100 movies/min)
- `calculate_all_user_signals()` — ~30-60 seconds (20 users/sec)
- `compute_all_user_vectors()` — ~1-2 minutes (per vector: 100-200ms)
- `compute_all_similarities()` — ⚠️ **4-6 hours** (50M pairs for 10K movies)
  - Recommendation: Use on-demand computation with caching instead

**Storage (MongoDB):**
- `movie_features` — ~50KB per movie = ~500MB (10K movies)
- `user_behavior_signals` — ~5KB per user = ~5MB (1K users)
- `user_vectors` — ~2KB per vector (100 dims) = ~2MB (1K users)
- `content_similarity` — ⚠️ **~5GB** if all pairs stored (avoid precomputing)

**Recommendation:**
- Precompute: features, behavior signals, user vectors
- On-demand: content similarity (store top 20 per movie only)

---

### 🔄 Batch Job Integration

These services are designed to run as scheduled background jobs:

```python
# In FastAPI app startup or APScheduler jobs:

@scheduler.scheduled_job('cron', hour=2)  # 2 AM daily
async def recompute_user_vectors():
    service = UserVectorizationService(db)
    await service.compute_all_user_vectors()

@scheduler.scheduled_job('cron', hour='*')  # Every hour
async def refresh_behavior_signals():
    service = UserBehaviorService(db)
    # Compute for users active in last 24 hours
    active_users = await db.watch_history.distinct(
        "user_id",
        {"watch_date": {"$gte": datetime.utcnow() - timedelta(days=1)}}
    )
    for user_id in active_users:
        await service.calculate_user_behavior_signals(user_id)

@scheduler.scheduled_job('cron', minute='*/30')  # Every 30 minutes
async def extract_new_movies():
    service = ContentFeaturesService(db)
    # Find movies added in last 30 minutes
    new_movies = await db.movies.find(
        {"updated_at": {"$gte": datetime.utcnow() - timedelta(minutes=30)}}
    ).to_list(None)
    for movie in new_movies:
        await service.extract_movie_features(movie["id"])
```

---

### ✅ Phase 2 Checklist

- [x] `content_features_service.py` — Movie feature extraction
- [x] `user_behavior_service.py` — User behavior aggregation
- [x] `user_vectorization_service.py` — Collaborative filtering vectors
- [x] `content_similarity_service.py` — Movie similarity computation
- [x] Documentation with usage examples
- [x] Performance considerations & recommendations

---

## Phase 3: Recommendation Engine (Next)

**What's Being Built:**
- `recommendation_engine.py` — Hybrid scoring & ranking engine
- Combines all features into final recommendations
- Implements diversity penalty, cold start handling
- Caching & performance optimization

**Expected Output:**
- Personalized recommendations (top 20 per user)
- Trending recommendations
- Genre-specific recommendations
- "Similar to this movie" recommendations

---

**Phase 2 Status: ✅ COMPLETE**

All feature extraction services are ready. Data pipeline infrastructure established.
Ready to proceed to Phase 3 (Recommendation Engine).
