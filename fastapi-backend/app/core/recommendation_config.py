"""
Recommendation Engine Configuration
Centralized configuration for all recommendation algorithm parameters
"""

from typing import Dict

# ============================================================================
# ALGORITHM WEIGHTS
# ============================================================================
# These weights determine how each component contributes to the final score
# Total should sum to 1.0 (or close to it for flexibility)

RECOMMENDATION_WEIGHTS = {
    "genre_similarity": 0.25,           # How much the genres match user preferences
    "collaborative_filtering": 0.25,    # Similarity to other users' preferences
    "popularity": 0.15,                 # Trending, community ratings, view count
    "content_similarity": 0.20,         # Cast, director, keywords, production company
    "user_behavior": 0.15,              # Watch time, completion rate, drop rate
}

# ============================================================================
# FEATURE IMPORTANCE
# ============================================================================
# Sub-weights for content features

CONTENT_FEATURE_WEIGHTS = {
    "genre": 0.40,
    "cast": 0.25,
    "director": 0.15,
    "keywords": 0.15,
    "production_company": 0.05,
}

# ============================================================================
# BEHAVIOR SCORING
# ============================================================================
# How to score user behavior signals

BEHAVIOR_WEIGHTS = {
    "completion_rate": 0.40,      # 0-100% watched
    "rating_given": 0.25,         # User explicit rating (1-10)
    "rewatch_count": 0.20,        # Number of times rewatched
    "session_duration": 0.15,     # Average session length
}

# Drop rate penalty: if user drops <20% watched, penalize similar content
DROP_RATE_THRESHOLD = 0.20  # If completion < 20%, count as "dropped"
DROP_RATE_PENALTY = 0.5     # Multiply score by 0.5 if similar to dropped content

# ============================================================================
# RECENCY & TEMPORAL FACTORS
# ============================================================================

# Time decay for ratings: older ratings matter less
# Decay function: score *= (1 / (1 + days_ago / RATING_HALF_LIFE))
RATING_HALF_LIFE_DAYS = 90  # After 90 days, rating weight is halved

# Boost for new/trending content
RECENCY_BOOST_DAYS = 30     # Movies released in last 30 days get boost
RECENCY_BOOST_FACTOR = 1.3  # Multiply score by 1.3 for new content

# Popularity trend boost
# Boost movies gaining popularity (e.g., trending up in last 7 days)
TRENDING_BOOST_DAYS = 7
TRENDING_BOOST_FACTOR = 1.2

# ============================================================================
# DIVERSITY PENALTY
# ============================================================================
# Avoid recommending too many similar movies (e.g., all action films)

# Maximum number of movies from same primary genre in top-N recommendations
MAX_SAME_GENRE_IN_TOP_N = {
    "top_10": 3,    # Max 3 action movies in top 10 recommendations
    "top_20": 5,    # Max 5 action movies in top 20 recommendations
}

# Diversity penalty: multiply score if already showing too many of this genre
DIVERSITY_PENALTY = 0.7

# ============================================================================
# CANDIDATE GENERATION
# ============================================================================

# How many candidate movies to consider before ranking
CANDIDATE_POOL_SIZE = 1000

# Minimum score threshold to be included in recommendations
MIN_RECOMMENDATION_SCORE = 0.3  # 30% of max possible score

# Number of final recommendations to return
RECOMMENDATION_LIMIT = 20

# ============================================================================
# COLD START HANDLING
# ============================================================================

# For new users with no watch history
NEW_USER_STRATEGY = "popularity"  # Options: "popularity", "trending", "random_genre"

# For new movies with no ratings
NEW_MOVIE_BOOST = 1.1  # Slight boost to encourage discovery

# Number of recommendations to show to completely new users
NEW_USER_RECOMMENDATION_COUNT = 10

# ============================================================================
# GEOLOCATION & LOCALIZATION
# ============================================================================

# Boost for movies in user's preferred language
LANGUAGE_MATCH_BOOST = 1.1

# Boost for movies from user's region (if tracked)
REGION_MATCH_BOOST = 1.05

# Weight for language preference in scoring
LANGUAGE_IMPORTANCE = 0.1

# List of priority languages per region (for multi-language recommendations)
REGION_LANGUAGE_PREFERENCES = {
    "US": ["en", "es"],
    "ES": ["es", "en", "ca"],
    "FR": ["fr", "en"],
    "DE": ["de", "en"],
    "BR": ["pt", "en"],
    "MX": ["es", "en"],
    "JP": ["ja", "en"],
    "KR": ["ko", "en"],
}

# ============================================================================
# CACHING CONFIGURATION
# ============================================================================

# How long to cache recommendations (in seconds)
RECOMMENDATION_CACHE_TTL = {
    "personalized": 2 * 3600,      # 2 hours for per-user recs
    "trending": 1 * 3600,          # 1 hour for trending
    "genre": 2 * 3600,             # 2 hours for genre-specific
    "similar": 6 * 3600,           # 6 hours for "similar to movie"
}

# ============================================================================
# COMPUTATION FREQUENCY
# ============================================================================

# Batch job schedules (cron format or description)
BATCH_JOB_SCHEDULES = {
    "recompute_user_vectors": "0 2 * * *",        # 2 AM daily
    "recompute_trending": "0 * * * *",            # Every hour
    "enrich_new_movies": "*/30 * * * *",          # Every 30 minutes
    "cleanup_old_logs": "0 3 * * 0",              # 3 AM Sunday (weekly)
}

# ============================================================================
# FILTERING & EXCLUSION
# ============================================================================

# Movie content filters
CONTENT_FILTERS = {
    "min_rating": 3.5,              # Minimum TMDB rating to recommend
    "min_vote_count": 100,          # Minimum votes to be considered
    "exclude_certifications": [],   # e.g., ["NC-17"] to exclude
    "exclude_adult": True,          # Exclude adult content
}

# Exclude movies user has already:
EXCLUDE_WATCHED = True              # Don't recommend movies in watch_history
EXCLUDE_WATCHLIST = True            # Don't recommend movies in watchlist
EXCLUDE_RATED = True                # Don't recommend movies user already rated

# ============================================================================
# LOGGING & ANALYTICS
# ============================================================================

# Track recommendation impressions and interactions
TRACK_RECOMMENDATION_LOGS = True

# Metrics to compute
METRICS_TO_TRACK = [
    "click_through_rate",       # % of recommendations clicked
    "completion_rate",          # % of clicked movies watched >50%
    "genre_diversity",          # % of different genres in recommendations
    "cold_start_coverage",      # % of users getting non-fallback recs
    "recommendation_freshness", # % of new/trending content in recs
]

# ============================================================================
# A/B TESTING
# ============================================================================

# Enable A/B testing to compare algorithm variants
ENABLE_AB_TESTING = False

# A/B test configuration
AB_TEST_CONFIG = {
    "enabled": False,
    "variants": {
        "control": {
            "weights": RECOMMENDATION_WEIGHTS,
            "traffic_split": 0.5,  # 50% of users
        },
        "variant_v2": {
            "weights": {
                "genre_similarity": 0.20,
                "collaborative_filtering": 0.30,
                "popularity": 0.15,
                "content_similarity": 0.20,
                "user_behavior": 0.15,
            },
            "traffic_split": 0.5,  # 50% of users
        },
    },
    "test_duration_days": 14,
    "metrics_to_track": ["ctr", "completion_rate", "diversity"],
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURES = {
    "use_collaborative_filtering": True,
    "use_geolocation_boost": True,
    "use_recency_boost": True,
    "use_diversity_penalty": True,
    "use_behavior_signals": True,
}

# ============================================================================
# DEBUG & LOGGING
# ============================================================================

# Enable detailed logging for recommendation scoring
DEBUG_SCORING = False

# Log recommendation generation time
PROFILE_PERFORMANCE = False

# Store full scoring breakdown for each recommendation (for debugging)
STORE_SCORE_BREAKDOWN = False
