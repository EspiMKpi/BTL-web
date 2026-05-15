"""
Background Jobs for Recommendation System
Scheduled tasks for periodic data refresh and computation
Run with APScheduler or system cron
"""

import logging
from datetime import datetime, timedelta
from app.services.content_features_service import ContentFeaturesService
from app.services.user_behavior_service import UserBehaviorService
from app.services.user_vectorization_service import UserVectorizationService
from app.core.recommendation_config import BATCH_JOB_SCHEDULES

logger = logging.getLogger(__name__)


class RecommendationJobs:
    """Background jobs for recommendation system maintenance"""

    def __init__(self, db):
        self.db = db
        self.features_service = ContentFeaturesService(db)
        self.behavior_service = UserBehaviorService(db)
        self.vector_service = UserVectorizationService(db)

    async def recompute_user_vectors(self) -> Dict[str, Any]:
        """
        Nightly job: Recompute user vectors for collaborative filtering.
        Schedule: Daily @ 2 AM (0 2 * * *)
        Duration: ~1-2 minutes (1K users)
        
        Steps:
        1. Get all users with 3+ ratings
        2. Recompute vector for each
        3. Update user_vectors collection
        
        Returns:
            Job status and statistics
        """
        logger.info("Starting nightly user vector recomputation...")
        
        job_start = datetime.utcnow()
        
        result = await self.vector_service.compute_all_user_vectors()
        
        job_duration = (datetime.utcnow() - job_start).total_seconds()
        
        logger.info(
            f"User vector recomputation complete. "
            f"Processed: {result['processed']}, Skipped: {result['skipped']}, "
            f"Errors: {result['errors']}, Duration: {job_duration:.1f}s"
        )
        
        return {
            "job_name": "recompute_user_vectors",
            "status": "completed",
            "processed": result["processed"],
            "skipped": result["skipped"],
            "errors": result["errors"],
            "duration_seconds": job_duration,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def refresh_behavior_signals(self) -> Dict[str, Any]:
        """
        Hourly job: Refresh user behavior signals for recently active users.
        Schedule: Hourly (0 * * * *)
        Duration: ~30-60 seconds (active users only)
        
        Steps:
        1. Find users active in last 24 hours
        2. Recalculate behavior signals
        3. Update user_behavior_signals collection
        
        Returns:
            Job status and statistics
        """
        logger.info("Starting hourly behavior signal refresh...")
        
        job_start = datetime.utcnow()
        
        # Find users active in last 24 hours
        since = datetime.utcnow() - timedelta(days=1)
        active_users = await self.db["watch_history"].distinct(
            "user_id",
            {"watch_date": {"$gte": since}}
        )
        
        logger.info(f"Found {len(active_users)} active users to refresh")
        
        processed = 0
        errors = 0
        
        for user_id in active_users:
            try:
                await self.behavior_service.calculate_user_behavior_signals(user_id)
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"Refreshed {processed} user signals...")
                    
            except Exception as e:
                logger.error(f"Error refreshing user {user_id}: {e}")
                errors += 1
        
        job_duration = (datetime.utcnow() - job_start).total_seconds()
        
        logger.info(
            f"Behavior signal refresh complete. "
            f"Processed: {processed}, Errors: {errors}, Duration: {job_duration:.1f}s"
        )
        
        return {
            "job_name": "refresh_behavior_signals",
            "status": "completed",
            "processed": processed,
            "errors": errors,
            "duration_seconds": job_duration,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def enrich_new_movies(self) -> Dict[str, Any]:
        """
        Every 30 minutes: Extract features for newly added movies.
        Schedule: Every 30 minutes (*/30 * * * *)
        Duration: ~10-30 seconds (depends on new movies)
        
        Steps:
        1. Find movies updated in last 30 minutes
        2. Extract features and store in movie_features
        3. Compute similarity to existing movies
        
        Returns:
            Job status and statistics
        """
        logger.info("Starting new movie feature extraction...")
        
        job_start = datetime.utcnow()
        
        # Find movies added/updated in last 30 minutes
        since = datetime.utcnow() - timedelta(minutes=30)
        new_movies = await self.db["movies"].find(
            {"updated_at": {"$gte": since}}
        ).to_list(None)
        
        logger.info(f"Found {len(new_movies)} new/updated movies")
        
        processed = 0
        errors = 0
        
        for movie in new_movies:
            try:
                await self.features_service.extract_movie_features(movie["id"])
                processed += 1
                    
            except Exception as e:
                logger.error(f"Error extracting features for movie {movie['id']}: {e}")
                errors += 1
        
        job_duration = (datetime.utcnow() - job_start).total_seconds()
        
        logger.info(
            f"New movie feature extraction complete. "
            f"Processed: {processed}, Errors: {errors}, Duration: {job_duration:.1f}s"
        )
        
        return {
            "job_name": "enrich_new_movies",
            "status": "completed",
            "processed": processed,
            "errors": errors,
            "duration_seconds": job_duration,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def cleanup_old_logs(self) -> Dict[str, Any]:
        """
        Weekly job: Clean up old recommendation logs (>90 days).
        Schedule: Weekly Sunday 3 AM (0 3 * * 0)
        Duration: ~10-20 seconds
        
        Note: MongoDB TTL index handles this automatically,
        but this job provides explicit control and logging.
        
        Returns:
            Job status and statistics
        """
        logger.info("Starting recommendation log cleanup...")
        
        job_start = datetime.utcnow()
        
        # Delete logs older than 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        
        result = await self.db["recommendation_logs"].delete_many(
            {"shown_at": {"$lt": cutoff}}
        )
        
        job_duration = (datetime.utcnow() - job_start).total_seconds()
        
        logger.info(
            f"Recommendation log cleanup complete. "
            f"Deleted: {result.deleted_count}, Duration: {job_duration:.1f}s"
        )
        
        return {
            "job_name": "cleanup_old_logs",
            "status": "completed",
            "deleted_count": result.deleted_count,
            "duration_seconds": job_duration,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def compute_trending_scores(self) -> Dict[str, Any]:
        """
        Hourly job: Compute/update trending movie scores.
        Schedule: Hourly (0 * * * *)
        Duration: ~20-30 seconds
        
        Steps:
        1. Calculate recent popularity trends (last 7 days)
        2. Update popularity_trend field in movies
        3. Cache trending recommendations
        
        Returns:
            Job status and statistics
        """
        logger.info("Starting trending score computation...")
        
        job_start = datetime.utcnow()
        
        # Get movies with ratings in last 7 days
        since = datetime.utcnow() - timedelta(days=7)
        
        trending_cursor = self.db["user_ratings"].aggregate([
            {"$match": {"rating_date": {"$gte": since}}},
            {"$group": {
                "_id": "$movie_id",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$rating"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 500}
        ])
        
        trending_movies = await trending_cursor.to_list(None)
        
        # Update movies with trend scores
        processed = 0
        for trend_data in trending_movies:
            movie_id = trend_data["_id"]
            
            # Calculate trend score (0-100)
            trend_score = min(trend_data["count"] * (trend_data["avg_rating"] / 10), 100)
            
            await self.db["movies"].update_one(
                {"id": movie_id},
                {"$set": {
                    "popularity_trend": trend_score,
                    "trending_updated_at": datetime.utcnow()
                }}
            )
            
            processed += 1
        
        job_duration = (datetime.utcnow() - job_start).total_seconds()
        
        logger.info(
            f"Trending score computation complete. "
            f"Processed: {processed}, Duration: {job_duration:.1f}s"
        )
        
        return {
            "job_name": "compute_trending_scores",
            "status": "completed",
            "processed": processed,
            "duration_seconds": job_duration,
            "completed_at": datetime.utcnow().isoformat(),
        }


# ============================================================================
# APScheduler Integration
# ============================================================================
# Add to main.py startup:

async def setup_recommendation_jobs(app, db):
    """
    Initialize background jobs on app startup.
    Call this in FastAPI lifespan startup event.
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = AsyncIOScheduler()
        jobs = RecommendationJobs(db)
        
        # Schedule jobs
        scheduler.add_job(
            jobs.recompute_user_vectors,
            CronTrigger(hour=2),  # 2 AM daily
            id="recompute_user_vectors",
            name="Recompute user vectors for collaborative filtering"
        )
        
        scheduler.add_job(
            jobs.refresh_behavior_signals,
            CronTrigger(minute=0),  # Every hour
            id="refresh_behavior_signals",
            name="Refresh behavior signals for active users"
        )
        
        scheduler.add_job(
            jobs.enrich_new_movies,
            CronTrigger(minute="*/30"),  # Every 30 minutes
            id="enrich_new_movies",
            name="Extract features for new movies"
        )
        
        scheduler.add_job(
            jobs.compute_trending_scores,
            CronTrigger(minute=0),  # Every hour
            id="compute_trending_scores",
            name="Compute trending movie scores"
        )
        
        scheduler.add_job(
            jobs.cleanup_old_logs,
            CronTrigger(hour=3, day_of_week=6),  # Sunday 3 AM
            id="cleanup_old_logs",
            name="Clean up old recommendation logs"
        )
        
        scheduler.start()
        app.state.scheduler = scheduler
        
        logger.info("✓ Recommendation background jobs scheduled")
        
        return scheduler
        
    except ImportError:
        logger.warning(
            "APScheduler not installed. "
            "Install with: pip install apscheduler"
        )
        return None
```

Now I'll create a comprehensive test file:

