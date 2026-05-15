"""
Recommendation System Utilities
Helper functions for recommendation computations, scoring, and data manipulation
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from .recommendation_config import (
    RATING_HALF_LIFE_DAYS,
    RECENCY_BOOST_DAYS,
    RECENCY_BOOST_FACTOR,
    TRENDING_BOOST_DAYS,
    TRENDING_BOOST_FACTOR,
    DROP_RATE_THRESHOLD,
    DROP_RATE_PENALTY,
    LANGUAGE_MATCH_BOOST,
    REGION_MATCH_BOOST,
)


class ScoringUtils:
    """Utility functions for scoring calculations"""

    @staticmethod
    def apply_time_decay(score: float, rating_date: datetime, reference_date: Optional[datetime] = None) -> float:
        """
        Apply exponential time decay to a score.
        Older ratings matter less; after RATING_HALF_LIFE_DAYS, weight is 50%.
        
        Formula: score *= (1 / (1 + days_ago / HALF_LIFE))
        
        Args:
            score: Original score (0-1)
            rating_date: When the rating was given
            reference_date: Today (default: now)
            
        Returns:
            Decayed score
        """
        if reference_date is None:
            reference_date = datetime.utcnow()
        
        days_ago = (reference_date - rating_date).days
        if days_ago < 0:
            days_ago = 0
        
        decay_factor = 1.0 / (1.0 + days_ago / RATING_HALF_LIFE_DAYS)
        return score * decay_factor

    @staticmethod
    def apply_recency_boost(score: float, release_date: Optional[str], reference_date: Optional[datetime] = None) -> float:
        """
        Boost score for newly released movies.
        Movies released in last RECENCY_BOOST_DAYS get a boost.
        
        Args:
            score: Original score
            release_date: Movie release date (YYYY-MM-DD format)
            reference_date: Today (default: now)
            
        Returns:
            Boosted score
        """
        if reference_date is None:
            reference_date = datetime.utcnow()
        
        if not release_date:
            return score
        
        try:
            release_datetime = datetime.strptime(release_date, "%Y-%m-%d")
            days_since_release = (reference_date - release_datetime).days
            
            if 0 <= days_since_release <= RECENCY_BOOST_DAYS:
                return score * RECENCY_BOOST_FACTOR
        except (ValueError, TypeError):
            pass
        
        return score

    @staticmethod
    def apply_popularity_trend_boost(
        score: float, 
        popularity_trend: Optional[float], 
        is_trending: Optional[bool] = None
    ) -> float:
        """
        Boost score if movie is gaining popularity (trending up).
        
        Args:
            score: Original score
            popularity_trend: Trend value (e.g., +5, -2)
            is_trending: Boolean flag if trending
            
        Returns:
            Boosted score if trending
        """
        if is_trending:
            return score * TRENDING_BOOST_FACTOR
        
        if popularity_trend and popularity_trend > 0:
            # Slight boost proportional to trend
            boost = 1.0 + (min(popularity_trend, 10) / 100)
            return score * boost
        
        return score

    @staticmethod
    def apply_drop_rate_penalty(score: float, user_drop_rate: float) -> float:
        """
        Apply penalty to similar content if user has high drop rate.
        If user drops many movies early (< 20% watched), penalize similar content.
        
        Args:
            score: Original score
            user_drop_rate: User's overall drop rate (0-1)
            
        Returns:
            Penalized score if high drop rate
        """
        if user_drop_rate > DROP_RATE_THRESHOLD:
            return score * DROP_RATE_PENALTY
        
        return score

    @staticmethod
    def apply_language_boost(score: float, user_language: Optional[str], movie_language: Optional[str]) -> float:
        """
        Boost score if movie matches user's preferred language.
        
        Args:
            score: Original score
            user_language: User's preferred language code (e.g., 'en', 'es')
            movie_language: Movie's original language code
            
        Returns:
            Boosted score if languages match
        """
        if user_language and movie_language and user_language == movie_language:
            return score * LANGUAGE_MATCH_BOOST
        
        return score

    @staticmethod
    def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        Normalize score to range [min_val, max_val]
        
        Args:
            score: Raw score
            min_val: Minimum value
            max_val: Maximum value
            
        Returns:
            Normalized score
        """
        clamped = max(min_val, min(max_val, score))
        return clamped


class SimilarityUtils:
    """Utility functions for computing similarity metrics"""

    @staticmethod
    def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.
        Result: 0 = completely different, 1 = identical
        
        Args:
            vector_a: First vector
            vector_b: Second vector
            
        Returns:
            Similarity score (0-1)
        """
        if len(vector_a) != len(vector_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        magnitude_a = math.sqrt(sum(a ** 2 for a in vector_a))
        magnitude_b = math.sqrt(sum(b ** 2 for b in vector_b))
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)

    @staticmethod
    def jaccard_similarity(set_a: set, set_b: set) -> float:
        """
        Compute Jaccard similarity between two sets.
        Useful for comparing genres, keywords, cast.
        
        Result: 0 = no overlap, 1 = identical sets
        
        Args:
            set_a: First set
            set_b: Second set
            
        Returns:
            Similarity score (0-1)
        """
        if not set_a and not set_b:
            return 1.0
        
        if not set_a or not set_b:
            return 0.0
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def pearson_correlation(ratings_a: List[float], ratings_b: List[float]) -> float:
        """
        Compute Pearson correlation between two rating vectors.
        Used for collaborative filtering similarity.
        
        Result: -1 = opposite preferences, 0 = no correlation, 1 = identical
        
        Args:
            ratings_a: User A's ratings
            ratings_b: User B's ratings
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(ratings_a) != len(ratings_b) or len(ratings_a) < 2:
            return 0.0
        
        mean_a = sum(ratings_a) / len(ratings_a)
        mean_b = sum(ratings_b) / len(ratings_b)
        
        numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(ratings_a, ratings_b))
        denominator = math.sqrt(
            sum((a - mean_a) ** 2 for a in ratings_a) *
            sum((b - mean_b) ** 2 for b in ratings_b)
        )
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator


class FilteringUtils:
    """Utility functions for filtering and ranking"""

    @staticmethod
    def apply_diversity_penalty(
        rankings: List[Tuple[int, float, str]],  # (movie_id, score, primary_genre)
        max_same_genre: int = 3
    ) -> List[Tuple[int, float, str]]:
        """
        Apply diversity penalty: don't recommend too many movies from same genre.
        
        Args:
            rankings: List of (movie_id, score, primary_genre) tuples
            max_same_genre: Max movies from same genre in results
            
        Returns:
            List with adjusted scores for diversity
        """
        genre_counts: Dict[str, int] = {}
        result = []
        
        for movie_id, score, genre in rankings:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            if genre_counts[genre] > max_same_genre:
                # Apply penalty
                adjusted_score = score * 0.7
            else:
                adjusted_score = score
            
            result.append((movie_id, adjusted_score, genre))
        
        # Re-sort by adjusted score
        return sorted(result, key=lambda x: x[1], reverse=True)

    @staticmethod
    def remove_duplicates(movies: List[int]) -> List[int]:
        """
        Remove duplicate movie IDs while preserving order.
        
        Args:
            movies: List of movie IDs
            
        Returns:
            List with duplicates removed
        """
        seen = set()
        result = []
        for movie_id in movies:
            if movie_id not in seen:
                seen.add(movie_id)
                result.append(movie_id)
        return result

    @staticmethod
    def filter_by_user_history(
        candidates: List[int],
        watched_movies: set,
        watchlist_movies: set,
        exclude_watched: bool = True,
        exclude_watchlist: bool = True
    ) -> List[int]:
        """
        Filter out movies user has already watched or added to watchlist.
        
        Args:
            candidates: List of movie IDs to filter
            watched_movies: Set of movies user has watched
            watchlist_movies: Set of movies in user's watchlist
            exclude_watched: Remove watched movies?
            exclude_watchlist: Remove watchlist movies?
            
        Returns:
            Filtered list
        """
        result = []
        for movie_id in candidates:
            if exclude_watched and movie_id in watched_movies:
                continue
            if exclude_watchlist and movie_id in watchlist_movies:
                continue
            result.append(movie_id)
        
        return result


class VectorUtils:
    """Utility functions for vector operations"""

    @staticmethod
    def create_preference_vector(
        genre_weights: Dict[int, float],
        all_genres: List[int]
    ) -> List[float]:
        """
        Create user preference vector from genre weights.
        
        Args:
            genre_weights: Dict of {genre_id: weight}
            all_genres: List of all possible genre IDs
            
        Returns:
            Vector of weights aligned to all_genres
        """
        vector = []
        for genre_id in all_genres:
            vector.append(genre_weights.get(genre_id, 0.0))
        return vector

    @staticmethod
    def normalize_vector(vector: List[float]) -> List[float]:
        """
        Normalize vector to unit length (L2 normalization).
        
        Args:
            vector: Vector to normalize
            
        Returns:
            Normalized vector
        """
        magnitude = math.sqrt(sum(v ** 2 for v in vector))
        
        if magnitude == 0:
            return vector
        
        return [v / magnitude for v in vector]


class DateUtils:
    """Utility functions for date/time operations"""

    @staticmethod
    def days_ago(date: datetime) -> int:
        """Get number of days since a given date"""
        return (datetime.utcnow() - date).days

    @staticmethod
    def is_recent(date: datetime, days: int) -> bool:
        """Check if date is within last N days"""
        return DateUtils.days_ago(date) <= days

    @staticmethod
    def get_next_midnight() -> datetime:
        """Get next midnight UTC"""
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time())
