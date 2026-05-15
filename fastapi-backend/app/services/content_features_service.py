"""
Content Features Service
Extracts and enriches movie features from TMDB data for recommendations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.recommendation_schemas import MovieFeatures
from app.core.recommendation_config import CONTENT_FEATURE_WEIGHTS

logger = logging.getLogger(__name__)


class ContentFeaturesService:
    """Extract and manage movie features for content-based recommendations"""

    def __init__(self, db):
        self.db = db
        self.movies_collection = db["movies"]
        self.movie_features_collection = db["movie_features"]
        self.genres_collection = db["genres"]

    async def extract_movie_features(self, movie_id: int) -> Optional[MovieFeatures]:
        """
        Extract features from a movie document and store in movie_features collection.
        
        Args:
            movie_id: TMDB movie ID
            
        Returns:
            MovieFeatures object or None if movie not found
        """
        movie = await self.movies_collection.find_one({"id": movie_id})
        
        if not movie:
            logger.warning(f"Movie {movie_id} not found in database")
            return None
        
        # Extract and normalize features
        features = MovieFeatures(
            movie_id=movie.get("id"),
            title=movie.get("title", "Unknown"),
            genres=await self._extract_genres(movie.get("genres", [])),
            cast=self._extract_cast(movie.get("credits", {}).get("cast", [])),
            director=self._extract_director(movie.get("credits", {}).get("crew", [])),
            keywords=self._extract_keywords(movie.get("keywords", [])),
            production_company=self._extract_production_company(
                movie.get("production_companies", [])
            ),
            language=movie.get("original_language", "unknown"),
            certification=movie.get("certification"),
            popularity_score=movie.get("popularity", 0.0),
            vote_average=movie.get("vote_average", 0.0),
            vote_count=movie.get("vote_count", 0),
            release_date=movie.get("release_date"),
            embeddings=None,  # Can be computed later with ML models
            updated_at=datetime.utcnow(),
        )
        
        # Store in movie_features collection
        await self.movie_features_collection.update_one(
            {"movie_id": movie_id},
            {"$set": features.model_dump()},
            upsert=True,
        )
        
        logger.info(f"Extracted features for movie {movie_id}: {movie.get('title')}")
        return features

    async def _extract_genres(self, genre_list: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract genres and compute scores based on CONTENT_FEATURE_WEIGHTS.
        
        Args:
            genre_list: List of genre dicts from TMDB
            
        Returns:
            List of {id, name, score} with normalized scores
        """
        if not genre_list:
            return []
        
        result = []
        total_genres = len(genre_list)
        
        for i, genre in enumerate(genre_list):
            # First genre (primary) gets higher weight
            score = 1.0 - (i * 0.15)  # 1.0, 0.85, 0.70, 0.55, ...
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
            
            result.append({
                "id": genre.get("id"),
                "name": genre.get("name"),
                "score": score,
            })
        
        return result

    def _extract_cast(self, cast_list: List[Dict]) -> List[Dict[str, str]]:
        """
        Extract top 10 cast members for similarity matching.
        
        Args:
            cast_list: Full cast from TMDB
            
        Returns:
            Top 10 cast with name + character
        """
        result = []
        for i, actor in enumerate(cast_list[:10]):  # Top 10 only
            result.append({
                "name": actor.get("name", "Unknown"),
                "character": actor.get("character", "Unknown"),
                "order": i + 1,
            })
        
        return result

    def _extract_director(self, crew_list: List[Dict]) -> Optional[str]:
        """
        Extract director from crew list.
        
        Args:
            crew_list: Crew from TMDB
            
        Returns:
            Director name or None
        """
        for person in crew_list:
            if person.get("job") == "Director":
                return person.get("name")
        
        return None

    def _extract_keywords(self, keywords_list: List[Dict]) -> List[str]:
        """
        Extract keywords/themes from TMDB keywords.
        
        Args:
            keywords_list: Keywords from TMDB
            
        Returns:
            List of keyword strings (max 15)
        """
        result = []
        for keyword in keywords_list[:15]:  # Top 15 keywords
            result.append(keyword.get("name", "").lower())
        
        return [kw for kw in result if kw]  # Filter empty

    def _extract_production_company(self, companies_list: List[Dict]) -> Optional[str]:
        """
        Extract primary production company.
        
        Args:
            companies_list: Production companies from TMDB
            
        Returns:
            First production company name or None
        """
        if companies_list:
            return companies_list[0].get("name")
        return None

    async def enrich_movie_features(self, movie_id: int) -> Optional[MovieFeatures]:
        """
        Enrich existing movie features with additional data.
        Computes derived features like:
        - Popularity trend (vs. previous measurement)
        - Cast similarity to popular movies
        - Keyword importance
        
        Args:
            movie_id: TMDB movie ID
            
        Returns:
            Updated MovieFeatures or None
        """
        features = await self.movie_features_collection.find_one({"movie_id": movie_id})
        
        if not features:
            logger.warning(f"Features not found for movie {movie_id}")
            return None
        
        # Add enrichment logic here (future: popularity trend, embeddings, etc)
        features["enriched_at"] = datetime.utcnow()
        
        await self.movie_features_collection.update_one(
            {"movie_id": movie_id},
            {"$set": features},
        )
        
        logger.info(f"Enriched features for movie {movie_id}")
        return MovieFeatures(**features)

    async def get_movie_features(self, movie_id: int) -> Optional[MovieFeatures]:
        """
        Retrieve movie features from cache (movie_features collection).
        If not found, extract from movies collection.
        
        Args:
            movie_id: TMDB movie ID
            
        Returns:
            MovieFeatures or None
        """
        # Try to get from cache first
        cached = await self.movie_features_collection.find_one({"movie_id": movie_id})
        
        if cached:
            return MovieFeatures(**cached)
        
        # Extract if not cached
        return await self.extract_movie_features(movie_id)

    async def extract_all_movie_features(self) -> Dict[str, Any]:
        """
        Batch extract features for all movies in database.
        Use for initial setup or periodic refresh.
        
        Returns:
            Dict with counts: {processed, skipped, errors}
        """
        logger.info("Starting batch feature extraction for all movies...")
        
        processed = 0
        skipped = 0
        errors = 0
        
        cursor = self.movies_collection.find({}, {"id": 1, "title": 1})
        
        async for movie in cursor:
            try:
                await self.extract_movie_features(movie["id"])
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"Processed {processed} movies...")
                    
            except Exception as e:
                logger.error(f"Error processing movie {movie.get('id')}: {e}")
                errors += 1
        
        logger.info(
            f"Batch feature extraction complete. "
            f"Processed: {processed}, Errors: {errors}"
        )
        
        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }

    async def compute_genre_similarity(
        self, 
        movie_id_1: int, 
        movie_id_2: int
    ) -> float:
        """
        Compute genre similarity between two movies (0-1).
        Uses Jaccard similarity on genre sets.
        
        Args:
            movie_id_1: First movie ID
            movie_id_2: Second movie ID
            
        Returns:
            Similarity score (0-1)
        """
        features_1 = await self.get_movie_features(movie_id_1)
        features_2 = await self.get_movie_features(movie_id_2)
        
        if not features_1 or not features_2:
            return 0.0
        
        genres_1 = {g["id"] for g in features_1.genres}
        genres_2 = {g["id"] for g in features_2.genres}
        
        if not genres_1 and not genres_2:
            return 1.0
        if not genres_1 or not genres_2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(genres_1 & genres_2)
        union = len(genres_1 | genres_2)
        
        return intersection / union if union > 0 else 0.0

    async def compute_cast_similarity(
        self,
        movie_id_1: int,
        movie_id_2: int
    ) -> float:
        """
        Compute cast similarity between two movies (0-1).
        Considers shared actors.
        
        Args:
            movie_id_1: First movie ID
            movie_id_2: Second movie ID
            
        Returns:
            Similarity score (0-1)
        """
        features_1 = await self.get_movie_features(movie_id_1)
        features_2 = await self.get_movie_features(movie_id_2)
        
        if not features_1 or not features_2:
            return 0.0
        
        cast_1 = {actor["name"] for actor in features_1.cast}
        cast_2 = {actor["name"] for actor in features_2.cast}
        
        if not cast_1 and not cast_2:
            return 1.0
        if not cast_1 or not cast_2:
            return 0.0
        
        intersection = len(cast_1 & cast_2)
        union = len(cast_1 | cast_2)
        
        return intersection / union if union > 0 else 0.0

    async def get_similar_movies_by_features(
        self,
        movie_id: int,
        limit: int = 10,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find movies with similar features (genres, cast, director).
        
        Args:
            movie_id: Reference movie ID
            limit: Max results to return
            min_similarity: Minimum similarity score to include
            
        Returns:
            List of similar movies with similarity scores
        """
        reference = await self.get_movie_features(movie_id)
        if not reference:
            return []
        
        similar_movies = []
        
        # Get all movies and compute similarity
        cursor = self.movie_features_collection.find(
            {"movie_id": {"$ne": movie_id}},
            {"_id": 0}
        )
        
        async for other_features in cursor:
            # Compute weighted similarity
            genre_sim = await self.compute_genre_similarity(
                movie_id, 
                other_features["movie_id"]
            )
            cast_sim = await self.compute_cast_similarity(
                movie_id,
                other_features["movie_id"]
            )
            director_match = 1.0 if (
                reference.director and 
                reference.director == other_features.get("director")
            ) else 0.0
            
            # Weighted average (40% genre, 40% cast, 20% director)
            combined_score = (
                genre_sim * 0.40 +
                cast_sim * 0.40 +
                director_match * 0.20
            )
            
            if combined_score >= min_similarity:
                similar_movies.append({
                    "movie_id": other_features["movie_id"],
                    "title": other_features.get("title"),
                    "similarity_score": combined_score,
                    "shared_features": self._identify_shared_features(
                        reference, other_features
                    ),
                })
        
        # Sort by similarity and return top N
        similar_movies.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_movies[:limit]

    def _identify_shared_features(
        self,
        ref_features: MovieFeatures,
        other_features: Dict
    ) -> List[str]:
        """Identify what features two movies share"""
        shared = []
        
        ref_genres = {g["id"] for g in ref_features.genres}
        other_genres = {g["id"] for g in other_features.get("genres", [])}
        if ref_genres & other_genres:
            shared.append("genre")
        
        ref_cast = {a["name"] for a in ref_features.cast}
        other_cast = {a["name"] for a in other_features.get("cast", [])}
        if ref_cast & other_cast:
            shared.append("cast")
        
        if ref_features.director and ref_features.director == other_features.get("director"):
            shared.append("director")
        
        ref_keywords = set(ref_features.keywords or [])
        other_keywords = set(other_features.get("keywords", []))
        if ref_keywords & other_keywords:
            shared.append("keywords")
        
        return shared
