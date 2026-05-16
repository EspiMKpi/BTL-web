"""
User Vectorization Service
Creates user embedding vectors for collaborative filtering recommendations
"""

import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from app.models.recommendation_schemas import UserVector
from app.services.recommendation_utils import VectorUtils, SimilarityUtils, ScoringUtils

logger = logging.getLogger(__name__)


class UserVectorizationService:
    """Generate user vectors for collaborative filtering"""

    def __init__(self, db):
        self.db = db
        self.user_ratings_collection = db["user_ratings"]
        self.movies_collection = db["movies"]
        self.user_vectors_collection = db["user_vectors"]
        self.user_preferences_collection = db["user_preferences"]
        self.watch_history_collection = db["watch_history"]

    async def compute_user_vector(
        self,
        user_id: int,
        vector_dimension: int = 100,
    ) -> Optional[UserVector]:
        """
        Compute a user embedding vector based on genre preferences and ratings.
        
        Strategy: Create vector based on:
        - Genre preference (from watch history + ratings)
        - Movie popularity (weighted by user rating)
        - Content diversity
        
        Args:
            user_id: User ID
            vector_dimension: Dimension of output vector (default: 100)
            
        Returns:
            UserVector or None if user has insufficient data
        """
        # Get user ratings
        ratings = await self.user_ratings_collection.find(
            {"user_id": user_id}
        ).to_list(None)
        
        if not ratings or len(ratings) < 3:
            logger.warning(
                f"User {user_id} has insufficient ratings ({len(ratings) or 0}) "
                f"for vector computation. Need at least 3."
            )
            return None
        
        # Build genre score map
        genre_scores = await self._aggregate_genre_scores(user_id, ratings)
        
        if not genre_scores:
            logger.warning(f"User {user_id} has no genre information")
            return None
        
        # Create vector from genre scores
        vector = self._create_vector_from_genres(genre_scores, vector_dimension)
        
        # Normalize to unit vector
        vector = VectorUtils.normalize_vector(vector)
        
        user_vector = UserVector(
            user_id=user_id,
            vector=vector,
            dimension=vector_dimension,
            based_on_movies=len(ratings),
            computed_at=datetime.utcnow(),
        )
        
        # Store vector
        await self.user_vectors_collection.update_one(
            {"user_id": user_id},
            {"$set": user_vector.model_dump()},
            upsert=True,
        )
        
        logger.info(
            f"Computed vector for user {user_id} "
            f"({len(ratings)} rated movies, {len(genre_scores)} genres)"
        )
        
        return user_vector

    async def _aggregate_genre_scores(
        self,
        user_id: int,
        ratings: List[Dict[str, Any]]
    ) -> Dict[int, float]:
        """
        Aggregate genre scores from user's ratings.
        Higher user rating = higher preference for that genre.
        
        Args:
            user_id: User ID
            ratings: List of rating documents
            
        Returns:
            Dict of {genre_id: aggregated_score}
        """
        genre_scores: Dict[int, Dict[str, Any]] = {}
        
        for rating in ratings:
            movie_id = rating.get("movie_id")
            user_rating = rating.get("rating", 5.0)  # 0-10 scale
            rating_date = rating.get("rating_date", datetime.utcnow())
            
            # Apply time decay to older ratings
            if isinstance(rating_date, str):
                try:
                    rating_date = datetime.fromisoformat(rating_date)
                except (ValueError, TypeError):
                    rating_date = datetime.utcnow()
            
            decayed_rating = ScoringUtils.apply_time_decay(
                user_rating / 10.0,  # Normalize to 0-1
                rating_date
            )
            
            # Get movie genres
            movie = await self.movies_collection.find_one(
                {"id": movie_id},
                {"genres": 1}
            )
            
            if not movie:
                continue
            
            # Add score to each genre
            for genre in movie.get("genres", []):
                genre_id = genre.get("id")
                genre_name = genre.get("name")
                
                if genre_id not in genre_scores:
                    genre_scores[genre_id] = {
                        "id": genre_id,
                        "name": genre_name,
                        "score": 0.0,
                        "count": 0,
                    }
                
                genre_scores[genre_id]["score"] += decayed_rating
                genre_scores[genre_id]["count"] += 1
        
        # Normalize by count (average)
        result = {}
        for genre_id, data in genre_scores.items():
            avg_score = data["score"] / data["count"] if data["count"] > 0 else 0.0
            result[genre_id] = min(avg_score, 1.0)  # Clamp to 0-1
        
        return result

    def _create_vector_from_genres(
        self,
        genre_scores: Dict[int, float],
        dimension: int
    ) -> List[float]:
        """
        Create a fixed-dimension vector from genre scores.
        
        Strategy:
        - Sort genres by score
        - Place top genres in first positions
        - Distribute remaining scores across vector
        
        Args:
            genre_scores: Dict of {genre_id: score}
            dimension: Output vector dimension
            
        Returns:
            Vector of length `dimension`
        """
        # Initialize with zeros
        vector = [0.0] * dimension
        
        # Sort genres by score
        sorted_genres = sorted(
            genre_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Place genres in vector
        for i, (genre_id, score) in enumerate(sorted_genres):
            if i < dimension:
                # Direct placement for first N genres
                vector[i] = score
            else:
                # Average remaining scores into last position
                vector[-1] += score / len(sorted_genres[dimension:])
        
        # Normalize last position
        if dimension > len(sorted_genres):
            vector[-1] = vector[-1] / max(1, len(sorted_genres) - dimension)
        
        return vector

    async def get_user_vector(self, user_id: int) -> Optional[UserVector]:
        """
        Retrieve cached user vector or compute if not found.
        
        Args:
            user_id: User ID
            
        Returns:
            UserVector or None
        """
        cached = await self.user_vectors_collection.find_one({"user_id": user_id})
        
        if cached:
            return UserVector(**cached)
        
        # Compute if not cached
        return await self.compute_user_vector(user_id)

    async def find_similar_users(
        self,
        user_id: int,
        top_n: int = 10,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find users with similar taste profiles using vector similarity.
        
        Args:
            user_id: Reference user ID
            top_n: Return top N similar users
            min_similarity: Minimum similarity score (0-1)
            
        Returns:
            List of {user_id, similarity_score, shared_preferences}
        """
        user_vector = await self.get_user_vector(user_id)
        
        if not user_vector:
            logger.warning(f"No vector found for user {user_id}")
            return []
        
        similar_users = []
        
        # Compare against all other user vectors
        cursor = self.user_vectors_collection.find(
            {"user_id": {"$ne": user_id}}
        )
        
        async for other in cursor:
            other_vector = UserVector(**other)
            
            # Compute cosine similarity
            similarity = SimilarityUtils.cosine_similarity(
                user_vector.vector,
                other_vector.vector
            )
            
            if similarity >= min_similarity:
                similar_users.append({
                    "user_id": other_vector.user_id,
                    "similarity_score": similarity,
                    "based_on_movies": other_vector.based_on_movies,
                })
        
        # Sort by similarity
        similar_users.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return similar_users[:top_n]

    async def compute_user_similarity(
        self,
        user_id_1: int,
        user_id_2: int
    ) -> float:
        """
        Compute similarity between two users (0-1).
        
        Args:
            user_id_1: First user ID
            user_id_2: Second user ID
            
        Returns:
            Similarity score (0-1)
        """
        vector_1 = await self.get_user_vector(user_id_1)
        vector_2 = await self.get_user_vector(user_id_2)
        
        if not vector_1 or not vector_2:
            return 0.0
        
        return SimilarityUtils.cosine_similarity(
            vector_1.vector,
            vector_2.vector
        )

    async def compute_rating_correlation(
        self,
        user_id_1: int,
        user_id_2: int
    ) -> float:
        """
        Compute Pearson correlation between two users' ratings.
        Better for smaller datasets, more interpretable.
        
        Args:
            user_id_1: First user ID
            user_id_2: Second user ID
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        # Get movies both users have rated
        ratings_1 = await self.user_ratings_collection.find(
            {"user_id": user_id_1}
        ).to_list(None)
        
        ratings_2 = await self.user_ratings_collection.find(
            {"user_id": user_id_2}
        ).to_list(None)
        
        movies_1 = {r["movie_id"]: r["rating"] for r in ratings_1}
        movies_2 = {r["movie_id"]: r["rating"] for r in ratings_2}
        
        # Find common movies
        common_movies = set(movies_1.keys()) & set(movies_2.keys())
        
        if len(common_movies) < 2:
            return 0.0
        
        # Extract ratings for common movies
        ratings_1_common = [movies_1[m] for m in common_movies]
        ratings_2_common = [movies_2[m] for m in common_movies]
        
        return SimilarityUtils.pearson_correlation(
            ratings_1_common,
            ratings_2_common
        )

    async def compute_all_user_vectors(self) -> Dict[str, Any]:
        """
        Batch compute vectors for all users.
        Use for initial setup or periodic refresh.
        
        Returns:
            Dict with {processed, skipped, errors}
        """
        logger.info("Starting batch user vector computation...")
        
        processed = 0
        skipped = 0
        errors = 0
        
        # Get unique users from ratings
        users = await self.user_ratings_collection.distinct("user_id")
        
        logger.info(f"Found {len(users)} users to process")
        
        for user_id in users:
            try:
                result = await self.compute_user_vector(user_id)
                
                if result:
                    processed += 1
                else:
                    skipped += 1
                
                if processed % 50 == 0:
                    logger.info(
                        f"Processed {processed} users, "
                        f"Skipped {skipped}, Errors {errors}"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                errors += 1
        
        logger.info(
            f"Batch user vector computation complete. "
            f"Processed: {processed}, Skipped: {skipped}, Errors: {errors}"
        )
        
        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }

    async def get_vector_statistics(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics about a user's vector.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with vector statistics or None
        """
        user_vector = await self.get_user_vector(user_id)
        
        if not user_vector:
            return None
        
        vector = user_vector.vector
        
        return {
            "user_id": user_id,
            "dimension": user_vector.dimension,
            "magnitude": math.sqrt(sum(v ** 2 for v in vector)),
            "mean": sum(vector) / len(vector),
            "min": min(vector),
            "max": max(vector),
            "std_dev": self._calculate_std_dev(vector),
            "non_zero_components": sum(1 for v in vector if v != 0.0),
            "computed_at": user_vector.computed_at.isoformat(),
        }

    def _calculate_std_dev(self, vector: List[float]) -> float:
        """Calculate standard deviation of vector"""
        if not vector:
            return 0.0
        
        mean = sum(vector) / len(vector)
        variance = sum((v - mean) ** 2 for v in vector) / len(vector)
        
        return math.sqrt(variance)
