import mongoose, { type Document } from "mongoose";
import type { GenreDocument, CastDocument, CrewDocument } from "../types.js";
export interface MovieDoc extends Document {
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
    created_at: Date;
    updated_at: Date;
}
export declare const Movie: mongoose.Model<MovieDoc, {}, {}, {}, mongoose.Document<unknown, {}, MovieDoc, {}, mongoose.DefaultSchemaOptions> & MovieDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, MovieDoc>;
//# sourceMappingURL=Movie.d.ts.map