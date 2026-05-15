"""
User Behavior Service
Extracts and calculates user behavior signals for recommendations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncDatabase
from app.models.recommendation_schemas import UserBehaviorSignals
from app.core.recommendation_config import DROP_RATE_THRESHOLD

logger = logging.getLogger(__name__)


class UserBehaviorService:
    """Calculate user behavior signals for recommendations"""

    def __init__(self, db):
        self.db = db
        self.watch_history_collection = db["watch_history"]
        self.user_ratings_collection = db["user_ratings"]
        self.movies_collection = db["movies"]
        self.user_behavior_collection = db.get_collection("user_behavior_signals")

    async def calculate_user_behavior_signals(
        self, user_id: int
    ) -> Optional[UserBehaviorSignals]:
        """
        Calculate aggregated behavior signals for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            UserBehaviorSignals or None if user has no history
        """
        # Get watch history
        watch_history = await self.watch_history_collection.find(
            {"user_id": user_id}
        ).to_list(None)
        
        if not watch_history:
            logger.warning(f"No watch history found for user {user_id}")
            return None
        
        # Get ratings
        ratings = await self.user_ratings_collection.find(
            {"user_id": user_id}
        ).to_list(None)
        
        # Calculate signals
        total_movies = sum(1 for h in watch_history if h.get("content_type") == "movie")
        total_series = sum(1 for h in watch_history if h.get("content_type") == "series")
        
        completion_rates = [
            h.get("completion_percentage", 0) / 100.0
            for h in watch_history
            if h.get("completion_percentage") is not None
        ]
        avg_completion = (
            sum(completion_rates) / len(completion_rates)
            if completion_rates
            else 0.0
        )
        
        # Calculate drop rate (% of movies watched < 20%)
        dropped_count = sum(
            1 for rate in completion_rates if rate < DROP_RATE_THRESHOLD
        )
        drop_rate = (
            dropped_count / len(completion_rates) if completion_rates else 0.0
        )
        
        # Rating stats
        rating_values = [r.get("rating", 0) for r in ratings]
        avg_rating = (
            sum(rating_values) / len(rating_values) if rating_values else 0.0
        )
        
        # Session duration (average time watching)
        session_durations = [
            h.get("session_duration_minutes", 0)
            for h in watch_history
            if h.get("session_duration_minutes") is not None
        ]
        avg_session_duration = (
            sum(session_durations) / len(session_durations)
            if session_durations
            else 0.0
        )
        
        # Rewatch rate
        movie_ids = [h.get("movie_id") for h in watch_history]
        rewatch_count = len(movie_ids) - len(set(movie_ids))
        rewatch_rate = (
            rewatch_count / len(movie_ids) if movie_ids else 0.0
        )
        
        # Preferred watch time
        preferred_time = self._calculate_preferred_watch_time(watch_history)
        
        # Last activity
        last_activity = max(
            (h.get("watch_date") for h in watch_history if h.get("watch_date")),
            default=datetime.utcnow(),
        )
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)
        
        signals = UserBehaviorSignals(
            user_id=user_id,
            total_movies_watched=total_movies,
            total_series_watched=total_series,
            average_completion_rate=min(avg_completion, 1.0),
            average_rating=min(avg_rating, 10.0),
            drop_rate=min(drop_rate, 1.0),
            average_session_duration_minutes=avg_session_duration,
            rewatch_rate=min(rewatch_rate, 1.0),
            last_activity=last_activity,
            preferred_watch_time_of_day=preferred_time,
        )
        
        # Store signals
        await self.user_behavior_collection.update_one(
            {"user_id": user_id},
            {"$set": signals.model_dump()},
            upsert=True,
        )
        
        logger.info(
            f"Calculated behavior signals for user {user_id}: "
            f"watched {total_movies} movies, avg completion {avg_completion:.1%}"
        )
        
        return signals

    def _calculate_preferred_watch_time(self, watch_history: List[Dict]) -> Optional[str]:
        """
        Infer user's preferred watch time of day from history.
        
        Args:
            watch_history: List of watch history entries
            
        Returns:
            "Morning", "Afternoon", "Evening", "Night" or None
        """
        time_buckets = {"Morning": 0, "Afternoon": 0, "Evening": 0, "Night": 0}
        
        for entry in watch_history:
            watch_date = entry.get("watch_date")
            if not watch_date:
                continue
            
            if isinstance(watch_date, str):
                try:
                    watch_date = datetime.fromisoformat(watch_date)
                except (ValueError, TypeError):
                    continue
            
            hour = watch_date.hour
            if 6 <= hour < 12:
                time_buckets["Morning"] += 1
            elif 12 <= hour < 17:
                time_buckets["Afternoon"] += 1
            elif 17 <= hour < 21:
                time_buckets["Evening"] += 1
            else:
                time_buckets["Night"] += 1
        
        if not sum(time_buckets.values()):
            return None
        
        return max(time_buckets, key=time_buckets.get)

    async def get_user_behavior_signals(self, user_id: int) -> Optional[UserBehaviorSignals]:
        """
        Retrieve cached behavior signals or calculate if not found.
        
        Args:
            user_id: User ID
            
        Returns:
            UserBehaviorSignals or None
        """
        cached = await self.user_behavior_collection.find_one({"user_id": user_id})
        
        if cached:
            return UserBehaviorSignals(**cached)
        
        # Calculate if not cached
        return await self.calculate_user_behavior_signals(user_id)

    async def get_user_genre_preferences(
        self, user_id: int, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Calculate user's preferred genres based on watch history and ratings.
        
        Args:
            user_id: User ID
            top_n: Return top N genres
            
        Returns:
            List of {genre_id, genre_name, score} ordered by preference
        """
        watch_history = await self.watch_history_collection.find(
            {"user_id": user_id}
        ).to_list(None)
        
        if not watch_history:
            return []
        
        genre_scores: Dict[int, Dict[str, Any]] = {}
        
        for entry in watch_history:
            movie_id = entry.get("movie_id")
            completion = entry.get("completion_percentage", 0) / 100.0
            
            # Get movie genres
            movie = await self.movies_collection.find_one(
                {"id": movie_id},
                {"genres": 1}
            )
            
            if not movie:
                continue
            
            # Weight by completion: watched more = higher preference
            weight = completion
            
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
                
                genre_scores[genre_id]["score"] += weight
                genre_scores[genre_id]["count"] += 1
        
        # Normalize scores and sort
        if not genre_scores:
            return []
        
        max_score = max(g["score"] for g in genre_scores.values())
        
        result = [
            {
                "genre_id": g["id"],
                "genre_name": g["name"],
                "score": g["score"] / max_score if max_score > 0 else 0.0,
                "watch_count": g["count"],
            }
            for g in genre_scores.values()
        ]
        
        # Sort by score descending
        result.sort(key=lambda x: x["score"], reverse=True)
        
        return result[:top_n]

    async def get_user_favorite_actors(
        self, user_id: int, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Calculate user's favorite actors based on ratings and completion.
        
        Args:
            user_id: User ID
            top_n: Return top N actors
            
        Returns:
            List of {name, score, movie_count}
        """
        watch_history = await self.watch_history_collection.find(
            {"user_id": user_id}
        ).to_list(None)
        
        if not watch_history:
            return []
        
        actor_scores: Dict[str, Dict[str, Any]] = {}
        
        for entry in watch_history:
            movie_id = entry.get("movie_id")
            completion = entry.get("completion_percentage", 0) / 100.0
            
            # Get movie cast
            movie = await self.movies_collection.find_one(
                {"id": movie_id},
                {"credits.cast": 1}
            )
            
            if not movie or "credits" not in movie:
                continue
            
            cast = movie["credits"].get("cast", [])
            
            # Weight by completion
            weight = completion
            
            for actor in cast[:10]:  # Top 10 cast members
                actor_name = actor.get("name")
                
                if actor_name not in actor_scores:
                    actor_scores[actor_name] = {
                        "name": actor_name,
                        "score": 0.0,
                        "count": 0,
                    }
                
                actor_scores[actor_name]["score"] += weight
                actor_scores[actor_name]["count"] += 1
        
        if not actor_scores:
            return []
        
        max_score = max(a["score"] for a in actor_scores.values())
        
        result = [
            {
                "name": a["name"],
                "score": a["score"] / max_score if max_score > 0 else 0.0,
                "movie_count": a["count"],
            }
            for a in actor_scores.values()
        ]
        
        result.sort(key=lambda x: x["score"], reverse=True)
        
        return result[:top_n]

    async def get_user_watch_streak(self, user_id: int) -> Dict[str, Any]:
        """
        Calculate user's watch streak and engagement.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with {current_streak_days, last_watch_date, streak_type}
        """
        watch_history = await self.watch_history_collection.find(
            {"user_id": user_id}
        ).sort("watch_date", -1).limit(100).to_list(None)
        
        if not watch_history:
            return {
                "current_streak_days": 0,
                "last_watch_date": None,
                "streak_type": "none",
            }
        
        # Group by date
        watch_dates = []
        for entry in watch_history:
            watch_date = entry.get("watch_date")
            if isinstance(watch_date, str):
                try:
                    watch_date = datetime.fromisoformat(watch_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(watch_date, datetime):
                pass
            else:
                continue
            
            watch_dates.append(watch_date.date())
        
        watch_dates = sorted(set(watch_dates), reverse=True)
        
        if not watch_dates:
            return {
                "current_streak_days": 0,
                "last_watch_date": None,
                "streak_type": "none",
            }
        
        # Calculate current streak
        current_streak = 1
        today = datetime.utcnow().date()
        
        # Check if watched today or yesterday
        if watch_dates[0] != today and watch_dates[0] != today - timedelta(days=1):
            current_streak = 0
        else:
            # Count consecutive days
            for i in range(1, len(watch_dates)):
                expected_date = watch_dates[i - 1] - timedelta(days=1)
                if watch_dates[i] == expected_date:
                    current_streak += 1
                else:
                    break
        
        # Determine streak type
        if current_streak == 0:
            streak_type = "broken"
        elif current_streak >= 7:
            streak_type = "hot"
        elif current_streak >= 3:
            streak_type = "active"
        else:
            streak_type = "mild"
        
        return {
            "current_streak_days": current_streak,
            "last_watch_date": watch_dates[0].isoformat(),
            "streak_type": streak_type,
        }

    async def calculate_all_user_signals(self) -> Dict[str, Any]:
        """
        Batch calculate behavior signals for all users.
        Use for initial setup or periodic refresh.
        
        Returns:
            Dict with {processed, errors}
        """
        logger.info("Starting batch behavior signal calculation for all users...")
        
        processed = 0
        errors = 0
        
        # Get unique users from watch_history
        users = await self.watch_history_collection.distinct("user_id")
        
        for user_id in users:
            try:
                await self.calculate_user_behavior_signals(user_id)
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"Processed {processed} users...")
                    
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                errors += 1
        
        logger.info(
            f"Batch behavior signal calculation complete. "
            f"Processed: {processed}, Errors: {errors}"
        )
        
        return {
            "processed": processed,
            "errors": errors,
        }
