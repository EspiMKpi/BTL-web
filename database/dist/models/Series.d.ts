import mongoose, { type Document } from "mongoose";
import type { GenreDocument, CastDocument, CrewDocument, SeasonDocument } from "../types.js";
export interface SeriesDoc extends Document {
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
    created_at: Date;
    updated_at: Date;
}
export declare const Series: mongoose.Model<SeriesDoc, {}, {}, {}, mongoose.Document<unknown, {}, SeriesDoc, {}, mongoose.DefaultSchemaOptions> & SeriesDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, SeriesDoc>;
//# sourceMappingURL=Series.d.ts.map