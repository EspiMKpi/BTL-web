"""
Recommendation System Pydantic Models
Data structures for recommendation requests/responses and internal data representation
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RecommendationResponse(BaseModel):
    """Single recommendation in the response"""
    movie_id: int
    title: str
    poster_path: Optional[str] = None
    overview: Optional[str] = None
    vote_average: float
    release_date: Optional[str] = None
    genres: List[str] = []
    score: float = Field(description="Recommendation score (0-1)")
    reason: str = Field(description="Why this was recommended (e.g., 'Based on your watch history')")
    rank: int = Field(description="Rank in recommendation list (1-20)")


class PersonalizedRecommendationsResponse(BaseModel):
    """Response for personalized recommendations endpoint"""
    user_id: int
    recommendations: List[RecommendationResponse]
    generated_at: datetime
    algorithm_version: str = "1.0"
    total_count: int


class SimilarMoviesResponse(BaseModel):
    """Response for 'similar to this movie' endpoint"""
    movie_id: int
    movie_title: str
    similar_movies: List[RecommendationResponse]
    criteria: List[str] = Field(
        description="What makes them similar (e.g., ['cast', 'genre', 'director'])"
    )
    generated_at: datetime


class GenreRecommendationsResponse(BaseModel):
    """Response for genre-specific recommendations"""
    genre_id: int
    genre_name: str
    recommendations: List[RecommendationResponse]
    trending: bool = Field(default=False, description="Are these trending in this genre?")
    generated_at: datetime


class TrendingMoviesResponse(BaseModel):
    """Response for trending movies"""
    recommendations: List[RecommendationResponse]
    time_window: str = Field(default="7days", description="Time period for trending (7days, 30days, etc)")
    generated_at: datetime


# ============================================================================
# DATA MODELS (Internal representation)
# ============================================================================

class GenreScore(BaseModel):
    """Genre with its score/weight"""
    genre_id: int
    genre_name: str
    score: float = Field(ge=0.0, le=1.0, description="Genre preference score")


class UserPreference(BaseModel):
    """User preference profile"""
    user_id: int
    genre_weights: List[GenreScore] = Field(description="Weighted genres user prefers")
    preferred_language: Optional[str] = None
    preferred_certification: Optional[str] = None
    favorite_directors: List[str] = []
    favorite_actors: List[str] = []
    updated_at: datetime


class UserBehaviorSignals(BaseModel):
    """Aggregated behavior signals for a user"""
    user_id: int
    total_movies_watched: int
    total_series_watched: int
    average_completion_rate: float = Field(ge=0.0, le=1.0)
    average_rating: float = Field(ge=0.0, le=10.0)
    drop_rate: float = Field(
        ge=0.0, le=1.0, description="% of movies dropped before 20% watched"
    )
    average_session_duration_minutes: float
    rewatch_rate: float = Field(ge=0.0, le=1.0, description="% of movies rewatched")
    last_activity: datetime
    preferred_watch_time_of_day: Optional[str] = Field(
        description="Morning, Afternoon, Evening, Night"
    )


class MovieFeatures(BaseModel):
    """Precomputed features for a movie"""
    movie_id: int
    title: str
    genres: List[Dict[str, Any]] = Field(description="[{id, name, score}, ...]")
    cast: List[Dict[str, str]] = Field(description="[{name, character}, ...]")
    director: Optional[str] = None
    keywords: List[str] = Field(description="Plot keywords/themes")
    production_company: Optional[str] = None
    language: str
    certification: Optional[str] = None
    popularity_score: float = Field(description="TMDB popularity metric")
    vote_average: float = Field(ge=0.0, le=10.0)
    vote_count: int
    release_date: Optional[str] = None
    embeddings: Optional[List[float]] = Field(
        description="Vector representation for similarity search (optional, future use)"
    )
    updated_at: datetime


class UserVector(BaseModel):
    """User embedding for collaborative filtering"""
    user_id: int
    vector: List[float] = Field(
        description="N-dimensional vector representing user preferences"
    )
    dimension: int = Field(description="Length of vector")
    based_on_movies: int = Field(description="Number of rated movies used to compute")
    computed_at: datetime


class RecommendationScore(BaseModel):
    """Detailed scoring breakdown for a recommendation"""
    movie_id: int
    user_id: int
    final_score: float
    
    # Component scores (for debugging/transparency)
    genre_similarity_score: float
    collaborative_filtering_score: float
    popularity_score: float
    content_similarity_score: float
    user_behavior_score: float
    
    # Modifiers
    recency_boost: float = Field(default=1.0)
    diversity_penalty: float = Field(default=1.0)
    language_boost: float = Field(default=1.0)
    
    # Metadata
    algorithm_version: str
    computed_at: datetime


class RecommendationLog(BaseModel):
    """Log entry for recommendation impression/interaction"""
    user_id: int
    movie_id: int
    recommendation_rank: int
    score: float
    algorithm_version: str
    shown_at: datetime
    
    # Interaction tracking
    clicked: Optional[bool] = Field(default=None, description="Did user click?")
    started_watching: Optional[bool] = Field(default=None)
    completion_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    session_duration_minutes: Optional[float] = None
    device_type: Optional[str] = Field(None, description="mobile, desktop, tablet, tv")
    user_rating: Optional[float] = Field(None, ge=0.0, le=10.0)
    
    clicked_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ContentSimilarityPair(BaseModel):
    """For computing similarity between movies/series"""
    movie_id_1: int
    movie_id_2: int
    similarity_score: float = Field(ge=0.0, le=1.0)
    shared_features: List[str] = Field(
        description="What they have in common (genre, cast, director, keywords)"
    )
    computed_at: datetime


# ============================================================================
# QUERY/FILTER MODELS
# ============================================================================

class RecommendationFilter(BaseModel):
    """Filters for recommendation queries"""
    exclude_genres: List[int] = Field(default=[], description="Genre IDs to exclude")
    include_genres: List[int] = Field(
        default=[], description="Only include these genres (optional)"
    )
    min_release_year: Optional[int] = None
    max_release_year: Optional[int] = None
    min_rating: Optional[float] = Field(None, ge=0.0, le=10.0)
    languages: List[str] = Field(default=[], description="Preferred languages")
    exclude_watched: bool = Field(default=True)
    exclude_watchlist: bool = Field(default=True)
    content_type: Optional[str] = Field(None, description="movie or series")


class RecommendationRequest(BaseModel):
    """Request for personalized recommendations"""
    limit: int = Field(default=20, ge=1, le=50)
    filters: Optional[RecommendationFilter] = None
    use_cache: bool = Field(default=True, description="Use cached recs if available?")


# ============================================================================
# METRICS & ANALYTICS MODELS
# ============================================================================

class RecommendationMetrics(BaseModel):
    """Aggregated metrics for recommendation performance"""
    period: str = Field(description="e.g., 'last_7_days', 'last_30_days'")
    
    # Main metrics
    click_through_rate: float = Field(ge=0.0, le=1.0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    average_score: float
    
    # Diversity metrics
    genre_diversity: float = Field(
        ge=0.0, le=1.0, description="% of different genres in recommendations"
    )
    cast_diversity: float = Field(ge=0.0, le=1.0)
    
    # Coverage metrics
    cold_start_coverage: float = Field(
        ge=0.0, le=1.0, description="% of users getting non-fallback recommendations"
    )
    content_freshness: float = Field(
        ge=0.0, le=1.0, description="% of recent/trending content in recommendations"
    )
    
    # Performance
    average_computation_time_ms: float
    cache_hit_rate: float = Field(ge=0.0, le=1.0)
    
    computed_at: datetime


class ABTestResult(BaseModel):
    """A/B test comparison results"""
    test_variant_a: str
    test_variant_b: str
    duration_days: int
    
    variant_a_ctr: float
    variant_b_ctr: float
    ctr_winner: str = Field(description="Which variant had higher CTR")
    
    variant_a_completion: float
    variant_b_completion: float
    completion_winner: str
    
    variant_a_diversity: float
    variant_b_diversity: float
    diversity_winner: str
    
    statistical_significance: float = Field(
        description="P-value, 0.05 = 95% confidence"
    )
    recommendation: str = Field(description="Which variant to deploy")


# ============================================================================
# BACKGROUND JOB MODELS
# ============================================================================

class JobStatus(BaseModel):
    """Status of a background job"""
    job_id: str
    job_type: str  # 'recompute_user_vectors', 'compute_trending', etc
    status: str  # 'pending', 'running', 'completed', 'failed'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    next_run: Optional[datetime] = None
