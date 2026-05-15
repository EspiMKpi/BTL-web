"""
Content Similarity Service
Computes and caches movie-to-movie similarity scores for efficient recommendations
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncDatabase
from app.models.recommendation_schemas import ContentSimilarityPair
from app.services.recommendation_utils import SimilarityUtils
from app.services.content_features_service import ContentFeaturesService

logger = logging.getLogger(__name__)


class ContentSimilarityService:
    """Compute and manage content similarity between movies"""

    def __init__(self, db):
        self.db = db
        self.similarity_collection = db["content_similarity"]
        self.movie_features_collection = db["movie_features"]
        self.movies_collection = db["movies"]
        self.features_service = ContentFeaturesService(db)

    async def compute_pairwise_similarity(
        self,
        movie_id_1: int,
        movie_id_2: int
    ) -> Optional[ContentSimilarityPair]:
        """
        Compute similarity between two specific movies.
        Considers: genres, cast, director, keywords, language.
        
        Args:
            movie_id_1: First movie ID
            movie_id_2: Second movie ID
            
        Returns:
            ContentSimilarityPair with similarity score and shared features
        """
        features_1 = await self.features_service.get_movie_features(movie_id_1)
        features_2 = await self.features_service.get_movie_features(movie_id_2)
        
        if not features_1 or not features_2:
            logger.warning(
                f"Could not compute similarity: features missing for "
                f"{movie_id_1} or {movie_id_2}"
            )
            return None
        
        # Compute individual similarities
        genre_sim = self._compute_genre_similarity(features_1, features_2)
        cast_sim = self._compute_cast_similarity(features_1, features_2)
        director_sim = self._compute_director_similarity(features_1, features_2)
        keywords_sim = self._compute_keywords_similarity(features_1, features_2)
        language_sim = self._compute_language_similarity(features_1, features_2)
        
        # Weighted combination (40% genre, 30% cast, 15% director, 10% keywords, 5% language)
        combined_score = (
            genre_sim * 0.40 +
            cast_sim * 0.30 +
            director_sim * 0.15 +
            keywords_sim * 0.10 +
            language_sim * 0.05
        )
        
        # Identify shared features
        shared_features = self._identify_shared_features(
            features_1, features_2,
            genre_sim, cast_sim, director_sim, keywords_sim
        )
        
        similarity_pair = ContentSimilarityPair(
            movie_id_1=movie_id_1,
            movie_id_2=movie_id_2,
            similarity_score=min(combined_score, 1.0),
            shared_features=shared_features,
            computed_at=datetime.utcnow(),
        )
        
        # Store in database
        await self.similarity_collection.update_one(
            {"movie_id_1": movie_id_1, "movie_id_2": movie_id_2},
            {"$set": similarity_pair.model_dump()},
            upsert=True,
        )
        
        # Also store reverse pair (for symmetric lookup)
        await self.similarity_collection.update_one(
            {"movie_id_1": movie_id_2, "movie_id_2": movie_id_1},
            {"$set": {
                **similarity_pair.model_dump(),
                "movie_id_1": movie_id_2,
                "movie_id_2": movie_id_1,
            }},
            upsert=True,
        )
        
        return similarity_pair

    def _compute_genre_similarity(
        self,
        features_1,
        features_2
    ) -> float:
        """Compute Jaccard similarity on genres"""
        genres_1 = {g["id"] for g in features_1.genres}
        genres_2 = {g["id"] for g in features_2.genres}
        
        if not genres_1 and not genres_2:
            return 1.0
        if not genres_1 or not genres_2:
            return 0.0
        
        return SimilarityUtils.jaccard_similarity(genres_1, genres_2)

    def _compute_cast_similarity(
        self,
        features_1,
        features_2
    ) -> float:
        """Compute Jaccard similarity on cast (actors)"""
        cast_1 = {a["name"] for a in features_1.cast}
        cast_2 = {a["name"] for a in features_2.cast}
        
        if not cast_1 and not cast_2:
            return 1.0
        if not cast_1 or not cast_2:
            return 0.0
        
        return SimilarityUtils.jaccard_similarity(cast_1, cast_2)

    def _compute_director_similarity(
        self,
        features_1,
        features_2
    ) -> float:
        """Compute director match (binary)"""
        if (features_1.director and 
            features_2.director and 
            features_1.director.lower() == features_2.director.lower()):
            return 1.0
        return 0.0

    def _compute_keywords_similarity(
        self,
        features_1,
        features_2
    ) -> float:
        """Compute Jaccard similarity on keywords"""
        keywords_1 = set(features_1.keywords or [])
        keywords_2 = set(features_2.keywords or [])
        
        if not keywords_1 and not keywords_2:
            return 1.0
        if not keywords_1 or not keywords_2:
            return 0.0
        
        return SimilarityUtils.jaccard_similarity(keywords_1, keywords_2)

    def _compute_language_similarity(
        self,
        features_1,
        features_2
    ) -> float:
        """Compute language match"""
        if (features_1.language and 
            features_2.language and 
            features_1.language.lower() == features_2.language.lower()):
            return 1.0
        return 0.0

    def _identify_shared_features(
        self,
        features_1,
        features_2,
        genre_sim: float,
        cast_sim: float,
        director_sim: float,
        keywords_sim: float
    ) -> List[str]:
        """Identify which features are shared (with significant similarity)"""
        shared = []
        
        if genre_sim > 0.2:
            shared.append("genre")
        if cast_sim > 0.1:
            shared.append("cast")
        if director_sim > 0.5:
            shared.append("director")
        if keywords_sim > 0.2:
            shared.append("keywords")
        
        return shared

    async def get_similar_movies(
        self,
        movie_id: int,
        limit: int = 20,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Get movies similar to a given movie.
        Uses cached similarity pairs.
        
        Args:
            movie_id: Reference movie ID
            limit: Max results
            min_similarity: Minimum similarity threshold
            
        Returns:
            Sorted list of similar movies
        """
        # Try to get from cache first
        cached = await self.similarity_collection.find(
            {
                "movie_id_1": movie_id,
                "similarity_score": {"$gte": min_similarity}
            }
        ).sort("similarity_score", -1).limit(limit).to_list(None)
        
        if cached:
            return [
                {
                    "movie_id": pair["movie_id_2"],
                    "similarity_score": pair["similarity_score"],
                    "shared_features": pair.get("shared_features", []),
                }
                for pair in cached
            ]
        
        # If not in cache, compute on-the-fly (slower)
        logger.info(f"Cache miss for movie {movie_id}, computing similarities...")
        
        # Get all movies
        all_movies = await self.movies_collection.find({}, {"id": 1}).to_list(None)
        
        similar_movies = []
        
        for other_movie in all_movies:
            other_id = other_movie["id"]
            if other_id == movie_id:
                continue
            
            pair = await self.compute_pairwise_similarity(movie_id, other_id)
            
            if pair and pair.similarity_score >= min_similarity:
                similar_movies.append({
                    "movie_id": other_id,
                    "similarity_score": pair.similarity_score,
                    "shared_features": pair.shared_features,
                })
        
        # Sort and return
        similar_movies.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return similar_movies[:limit]

    async def compute_all_similarities(
        self,
        batch_size: int = 100,
        min_similarity: float = 0.25
    ) -> Dict[str, Any]:
        """
        Batch compute similarity matrix for all movie pairs.
        WARNING: O(n²) complexity, use with caution for large catalogs.
        
        For 10,000 movies: ~100M pairs to compute (takes hours).
        Recommend: subset by popularity or compute on-demand with caching.
        
        Args:
            batch_size: Process movies in batches
            min_similarity: Only store pairs above threshold
            
        Returns:
            Dict with {processed, stored, errors}
        """
        logger.info("Starting batch similarity computation...")
        logger.warning(
            "This is an expensive operation. For large catalogs, "
            "consider computing on-demand instead."
        )
        
        movies = await self.movies_collection.find({}, {"id": 1}).to_list(None)
        movie_ids = [m["id"] for m in movies]
        
        logger.info(f"Computing similarity for {len(movie_ids)} movies...")
        
        processed = 0
        stored = 0
        errors = 0
        
        for i, movie_id_1 in enumerate(movie_ids):
            for movie_id_2 in movie_ids[i+1:]:  # Avoid duplicates
                try:
                    pair = await self.compute_pairwise_similarity(
                        movie_id_1,
                        movie_id_2
                    )
                    
                    if pair and pair.similarity_score >= min_similarity:
                        stored += 1
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(
                        f"Error computing similarity "
                        f"({movie_id_1}, {movie_id_2}): {e}"
                    )
                    errors += 1
            
            if (i + 1) % batch_size == 0:
                logger.info(
                    f"Processed {processed} pairs, "
                    f"Stored {stored}, Errors {errors}"
                )
        
        logger.info(
            f"Batch similarity computation complete. "
            f"Total pairs: {processed}, Stored: {stored}, Errors: {errors}"
        )
        
        return {
            "total_pairs_processed": processed,
            "pairs_stored": stored,
            "errors": errors,
        }

    async def find_cluster_members(
        self,
        movie_id: int,
        depth: int = 1,
        min_similarity: float = 0.4
    ) -> List[int]:
        """
        Find a cluster of similar movies (transitive).
        
        Example: Find all movies related to 'The Matrix'
        - Level 1: Movies similar to The Matrix
        - Level 2: Movies similar to similar movies
        
        Args:
            movie_id: Seed movie ID
            depth: How many levels to traverse
            min_similarity: Threshold for similarity
            
        Returns:
            List of movie IDs in cluster
        """
        cluster = {movie_id}
        frontier = {movie_id}
        
        for level in range(depth):
            next_frontier = set()
            
            for current_id in frontier:
                similar = await self.get_similar_movies(
                    current_id,
                    limit=20,
                    min_similarity=min_similarity
                )
                
                for movie_dict in similar:
                    similar_id = movie_dict["movie_id"]
                    if similar_id not in cluster:
                        cluster.add(similar_id)
                        next_frontier.add(similar_id)
            
            frontier = next_frontier
            
            if not frontier:
                break
        
        return list(cluster)

    async def get_similarity_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached similarities.
        
        Returns:
            Dict with counts and score distribution
        """
        total = await self.similarity_collection.count_documents({})
        
        # Score distribution
        avg_score = await self.similarity_collection.aggregate([
            {"$group": {"_id": None, "avg": {"$avg": "$similarity_score"}}}
        ]).to_list(1)
        
        avg_score = avg_score[0]["avg"] if avg_score else 0.0
        
        # Count by shared features
        shared_features_counts = {}
        cursor = self.similarity_collection.find({}, {"shared_features": 1})
        
        async for doc in cursor:
            for feature in doc.get("shared_features", []):
                shared_features_counts[feature] = shared_features_counts.get(feature, 0) + 1
        
        return {
            "total_similarity_pairs": total,
            "average_similarity_score": round(avg_score, 3),
            "shared_features_distribution": shared_features_counts,
        }
