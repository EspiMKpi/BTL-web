/**
 * MongoDB Document Model — ERD-driven design
 *
 * Collections: users, genres, movies, series,
 *   watch_history, watchlist_items, user_ratings
 *
 * Embed: casts, seasons, episodes inside content documents
 * Reference: users, genres, watch history, watchlist items, ratings
 */

// ─── Genre ───────────────────────────────────────────────
export interface GenreDocument {
    genre_id: number;
    name: string;
    created_at?: Date;
    updated_at?: Date;
}

// ─── Cast / Crew (embedded in movies & series) ───────────
export interface CastDocument {
    person_id: number;
    name: string;
    profile_path: string | null;
    character_name: string;
    cast_order: number;
}

export interface CrewDocument {
    person_id: number;
    name: string;
    profile_path: string | null;
    job: string;
}

// ─── Episode (embedded in season, season embedded in series)
export interface EpisodeDocument {
    episode_number: number;
    name: string;
    overview: string;
    still_path: string | null;
    air_date: string | null;
    runtime: number | null;
    vote_average: number;
    vote_count: number;
    season_number: number;
}

export interface SeasonDocument {
    season_number: number;
    name: string;
    overview: string;
    poster_path: string | null;
    air_date: string | null;
    episode_count: number;
    episodes: EpisodeDocument[];
}

// ─── Movie Document ──────────────────────────────────────
export interface MovieDocument {
    tmdb_id: number;
    title: string;
    original_title: string | null;
    tagline: string | null;
    overview: string;
    poster_path: string | null;
    backdrop_path: string | null;
    release_date: string | null;
    original_language: string | null;
    popularity: number;
    vote_average: number;
    vote_count: number;
    adult: boolean;
    video: boolean;
    runtime: number | null;
    budget: number;
    revenue: number;
    status: string | null;
    imdb_id: string | null;
    homepage: string | null;
    genres: GenreDocument[];
    cast: CastDocument[];
    crew: CrewDocument[];
    production_countries_json: Record<string, unknown>[];
    spoken_languages_json: Record<string, unknown>[];
    raw_data: Record<string, unknown>;
    created_at?: Date;
    updated_at?: Date;
}

// ─── Series Document ─────────────────────────────────────
export interface SeriesDocument {
    tmdb_id: number;
    name: string;
    original_name: string | null;
    tagline: string | null;
    overview: string;
    poster_path: string | null;
    backdrop_path: string | null;
    first_air_date: string | null;
    last_air_date: string | null;
    original_language: string | null;
    popularity: number;
    vote_average: number;
    vote_count: number;
    adult: boolean;
    episode_run_time: number[];
    type: string | null;
    status: string | null;
    imdb_id: string | null;
    homepage: string | null;
    number_of_seasons: number;
    number_of_episodes: number;
    genres: GenreDocument[];
    cast: CastDocument[];
    crew: CrewDocument[];
    seasons: SeasonDocument[];
    networks_json: Record<string, unknown>[];
    production_countries_json: Record<string, unknown>[];
    spoken_languages_json: Record<string, unknown>[];
    raw_data: Record<string, unknown>;
    created_at?: Date;
    updated_at?: Date;
}

// ─── Watch History ───────────────────────────────────────
export interface WatchHistoryDocument {
    user_id: string;
    content_type: "movie" | "series";
    tmdb_id: number;
    season_number: number | null;
    episode_number: number | null;
    progress_seconds: number;
    completed: boolean;
    last_watched_at: Date;
    created_at?: Date;
}

// ─── Watchlist Item ──────────────────────────────────────
export interface WatchlistItemDocument {
    user_id: string;
    content_type: "movie" | "series";
    tmdb_id: number;
    status: "plan_to_watch" | "watching" | "completed" | "dropped";
    progress_seconds: number;
    current_season: number | null;
    current_episode: number | null;
    rating: number | null;
    review: string | null;
    is_bookmarked: boolean;
    created_at?: Date;
    updated_at?: Date;
}

// ─── User Rating ─────────────────────────────────────────
export interface UserRatingDocument {
    user_id: string;
    content_type: "movie" | "series";
    tmdb_id: number;
    rating: number;
    review: string | null;
    created_at?: Date;
    updated_at?: Date;
}

// ─── TMDB API Response Shapes ────────────────────────────
export interface TmdbGenre {
    id: number;
    name: string;
}

export interface TmdbCastMember {
    id: number;
    name: string;
    profile_path: string | null;
    character: string;
    order: number;
}

export interface TmdbCrewMember {
    id: number;
    name: string;
    profile_path: string | null;
    job: string;
}

export interface TmdbCredits {
    cast: TmdbCastMember[];
    crew: TmdbCrewMember[];
}

export interface TmdbEpisode {
    episode_number: number;
    name: string;
    overview: string;
    still_path: string | null;
    air_date: string | null;
    runtime: number | null;
    vote_average: number;
    vote_count: number;
    season_number: number;
}

export interface TmdbSeason {
    season_number: number;
    name: string;
    overview: string;
    poster_path: string | null;
    air_date: string | null;
    episode_count: number;
    episodes?: TmdbEpisode[];
}

export interface TmdbMovieResponse {
    id: number;
    title: string;
    original_title: string | null;
    tagline: string | null;
    overview: string;
    poster_path: string | null;
    backdrop_path: string | null;
    release_date: string | null;
    original_language: string | null;
    popularity: number;
    vote_average: number;
    vote_count: number;
    adult: boolean;
    video: boolean;
    runtime: number | null;
    budget: number;
    revenue: number;
    status: string | null;
    imdb_id: string | null;
    homepage: string | null;
    genres: TmdbGenre[];
    credits: TmdbCredits;
    production_countries: { iso_3166_1: string; name: string }[];
    spoken_languages: { iso_639_1: string; english_name: string }[];
    [key: string]: unknown;
}

export interface TmdbSeriesResponse {
    id: number;
    name: string;
    original_name: string | null;
    tagline: string | null;
    overview: string;
    poster_path: string | null;
    backdrop_path: string | null;
    first_air_date: string | null;
    last_air_date: string | null;
    original_language: string | null;
    popularity: number;
    vote_average: number;
    vote_count: number;
    adult: boolean;
    episode_run_time: number[];
    type: string | null;
    status: string | null;
    imdb_id: string | null;
    homepage: string | null;
    number_of_seasons: number;
    number_of_episodes: number;
    genres: TmdbGenre[];
    credits: TmdbCredits;
    seasons: TmdbSeason[];
    networks: { id: number; name: string; logo_path: string | null }[];
    production_countries: { iso_3166_1: string; name: string }[];
    spoken_languages: { iso_639_1: string; english_name: string }[];
    [key: string]: unknown;
}
