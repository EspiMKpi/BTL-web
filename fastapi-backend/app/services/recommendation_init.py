"""
MongoDB Initialization for Recommendation System
Creates collections and indexes for recommendation features
Run this once when deploying the recommendation system
"""

import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RecommendationCollectionInitializer:
    """Initialize MongoDB collections for the recommendation system"""

    def __init__(self, db):
        self.db = db

    async def initialize_all(self) -> None:
        """Initialize all recommendation collections"""
        logger.info("Initializing recommendation collections...")
        
        await self.create_user_preferences_collection()
        await self.create_user_vectors_collection()
        await self.create_movie_features_collection()
        await self.create_recommendation_logs_collection()
        await self.create_content_similarity_collection()
        await self.create_recommendation_cache_collection()
        
        logger.info("✓ All recommendation collections initialized")

    async def create_user_preferences_collection(self) -> None:
        """
        user_preferences - User's genre weights, language preferences, etc.
        """
        collection_name = "user_preferences"
        
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        
        # Create indexes
        await self.db[collection_name].create_index("user_id", unique=True)
        await self.db[collection_name].create_index("updated_at")
        logger.info(f"✓ Indexes created for {collection_name}")

    async def create_user_vectors_collection(self) -> None:
        """
        user_vectors - User embeddings for collaborative filtering
        """
        collection_name = "user_vectors"
        
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        
        await self.db[collection_name].create_index("user_id", unique=True)
        await self.db[collection_name].create_index("computed_at")
        logger.info(f"✓ Indexes created for {collection_name}")

    async def create_movie_features_collection(self) -> None:
        """
        movie_features - Precomputed features for movies (genres, cast, keywords, etc.)
        """
        collection_name = "movie_features"
        
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        
        # Index for quick feature lookup
        await self.db[collection_name].create_index("movie_id", unique=True)
        await self.db[collection_name].create_index("genres")
        await self.db[collection_name].create_index("language")
        await self.db[collection_name].create_index("popularity_score", direction=-1)
        await self.db[collection_name].create_index("updated_at")
        
        # Compound index for filtering
        await self.db[collection_name].create_index([
            ("language", 1),
            ("popularity_score", -1)
        ])
        logger.info(f"✓ Indexes created for {collection_name}")

    async def create_recommendation_logs_collection(self) -> None:
        """
        recommendation_logs - Track what was recommended and how users interacted
        Used for metrics, A/B testing, and model improvement
        """
        collection_name = "recommendation_logs"
        
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        
        # Index for analytics queries
        await self.db[collection_name].create_index([("user_id", 1), ("shown_at", -1)])
        await self.db[collection_name].create_index([("movie_id", 1), ("shown_at", -1)])
        await self.db[collection_name].create_index("algorithm_version")
        await self.db[collection_name].create_index("shown_at", expireAfterSeconds=7776000)  # 90 days TTL
        
        # Index for CTR/completion metrics
        await self.db[collection_name].create_index([("clicked", 1), ("shown_at", -1)])
        await self.db[collection_name].create_index([("completion_percentage", 1), ("shown_at", -1)])
        
        logger.info(f"✓ Indexes created for {collection_name}")

    async def create_content_similarity_collection(self) -> None:
        """
        content_similarity - Precomputed similarity scores between movies
        Used for "similar to this movie" recommendations
        """
        collection_name = "content_similarity"
        
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        
        # Index for quick lookup of similar movies
        await self.db[collection_name].create_index([("movie_id_1", 1), ("similarity_score", -1)])
        await self.db[collection_name].create_index("movie_id_2")
        await self.db[collection_name].create_index("computed_at")
        
        logger.info(f"✓ Indexes created for {collection_name}")

    async def create_recommendation_cache_collection(self) -> None:
        """
        recommendation_cache - Cache for pre-computed recommendations
        """
        collection_name = "recommendation_cache"
        
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        
        # Index for cache lookup and TTL cleanup
        await self.db[collection_name].create_index("cache_key", unique=True)
        await self.db[collection_name].create_index([("user_id", 1), ("cache_type", 1)])
        await self.db[collection_name].create_index("expires_at", expireAfterSeconds=0)  # TTL index
        
        logger.info(f"✓ Indexes created for {collection_name}")


async def initialize_recommendation_system(db) -> None:
    """
    Main initialization function
    
    Usage:
        from app.database import db
        from app.services.recommendation_init import initialize_recommendation_system
        
        await initialize_recommendation_system(db)
    """
    initializer = RecommendationCollectionInitializer(db)
    await initializer.initialize_all()


# ============================================================================
# OPTIONAL: Enhance Existing Collections
# ============================================================================

async def enhance_watch_history_collection(db) -> None:
    """
    Add indexes to watch_history for recommendation queries
    Note: This assumes watch_history already exists
    """
    collection_name = "watch_history"
    
    try:
        # Add missing indexes if watch_history exists
        await db[collection_name].create_index([("user_id", 1), ("watch_date", -1)])
        await db[collection_name].create_index([("user_id", 1), ("completion_percentage", -1)])
        logger.info(f"✓ Enhanced indexes for {collection_name}")
    except Exception as e:
        logger.warning(f"Could not enhance {collection_name}: {e}")


async def enhance_movies_collection(db) -> None:
    """
    Add indexes to movies collection for recommendation queries
    """
    collection_name = "movies"
    
    try:
        await db[collection_name].create_index("genres")
        await db[collection_name].create_index("vote_average")
        await db[collection_name].create_index([("vote_average", -1), ("vote_count", -1)])
        logger.info(f"✓ Enhanced indexes for {collection_name}")
    except Exception as e:
        logger.warning(f"Could not enhance {collection_name}: {e}")


async def enhance_user_ratings_collection(db) -> None:
    """
    Add indexes to user_ratings for recommendation queries
    """
    collection_name = "user_ratings"
    
    try:
        await db[collection_name].create_index([("user_id", 1), ("rating_date", -1)])
        await db[collection_name].create_index([("movie_id", 1), ("rating", -1)])
        logger.info(f"✓ Enhanced indexes for {collection_name}")
    except Exception as e:
        logger.warning(f"Could not enhance {collection_name}: {e}")


if __name__ == "__main__":
    # For manual initialization
    async def main():
        from app.database import db
        await initialize_recommendation_system(db)

    asyncio.run(main())
