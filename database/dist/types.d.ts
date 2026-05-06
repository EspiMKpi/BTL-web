/**
 * MongoDB Document Model — movies collection
 *
 * Single embedded document replaces the 6 MySQL tables:
 *   movies, genres, people, movie_genres, movie_cast, movie_crew
 */
export interface GenreDocument {
    genre_id: number;
    name: string;
}
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
export interface MovieDocument {
    _id?: number;
    tmdb_id: number;
    title: string;
    runtime: number | null;
    vote_average: number;
    overview: string;
    release_date: string | null;
    poster_path: string | null;
    genres: GenreDocument[];
    cast: CastDocument[];
    crew: CrewDocument[];
    raw_data: Record<string, unknown>;
    created_at?: Date;
    updated_at?: Date;
}
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
export interface TmdbResponse {
    id: number;
    title: string;
    runtime: number | null;
    vote_average: number;
    overview: string;
    release_date: string | null;
    poster_path: string | null;
    genres: TmdbGenre[];
    credits: TmdbCredits;
    [key: string]: unknown;
}
//# sourceMappingURL=types.d.ts.map