import type { MovieDocument } from "./types.js";
/**
 * Fetch a movie by TMDB ID. Checks MongoDB first, then falls back to TMDB API.
 * Upserts the full ERD-driven document including all fields.
 */
declare function get_movie_by_id(tmdb_id: number): Promise<MovieDocument>;
/**
 * Get multiple movies by tmdb_ids (for rails / collections).
 */
declare function get_movies_by_ids(tmdb_ids: number[]): Promise<MovieDocument[]>;
/**
 * Search movies stored in MongoDB by title substring.
 */
declare function search_movies(query: string, limit?: number): Promise<MovieDocument[]>;
export { get_movie_by_id, get_movies_by_ids, search_movies };
//# sourceMappingURL=movieService.d.ts.map