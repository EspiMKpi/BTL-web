import type { SeriesDocument } from "./types.js";
/**
 * Fetch a TV series by TMDB ID. Checks MongoDB first, then falls back to TMDB API.
 * Upserts the full ERD-driven document with embedded seasons and episodes.
 */
declare function get_series_by_id(tmdb_id: number): Promise<SeriesDocument>;
/**
 * Get multiple series by tmdb_ids (for rails / collections).
 */
declare function get_series_by_ids(tmdb_ids: number[]): Promise<SeriesDocument[]>;
/**
 * Search series stored in MongoDB by name substring.
 */
declare function search_series(query: string, limit?: number): Promise<SeriesDocument[]>;
export { get_series_by_id, get_series_by_ids, search_series };
//# sourceMappingURL=seriesService.d.ts.map